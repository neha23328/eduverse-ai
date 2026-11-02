import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_student
from app.database import get_db
from app.models.models import Student, Quiz, QuizAttempt, SubjectProgress, Activity
from app.schemas.schemas import (
    QuizGenerateRequest, QuizOut, QuizQuestion, QuizSubmitRequest, QuizResultOut
)
from app.services import ai_service, rag

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("/generate", response_model=QuizOut)
def generate_quiz(
    payload: QuizGenerateRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    context, note_sources = "", []
    if payload.use_notes:
        hits = rag.retrieve(db, current_student.id, f"{payload.subject} {payload.topic}",
                            payload.doc_ids, k=max(6, payload.num_questions))
        if not hits:
            raise HTTPException(status_code=422, detail=(
                "Your notes don't seem to cover this topic. Try a different topic, "
                "upload more notes, or turn off 'Use my notes'."))
        context, note_sources = rag.build_context(hits), rag.sources_payload(hits)
    try:
        questions_raw, source = ai_service.generate_quiz(
            subject=payload.subject,
            topic=payload.topic,
            difficulty=payload.difficulty,
            num_questions=payload.num_questions,
            context=context,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

    quiz = Quiz(
        student_id=current_student.id,
        subject=payload.subject,
        topic=payload.topic,
        difficulty=payload.difficulty,
        questions_json=json.dumps(questions_raw),
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    questions = [QuizQuestion(**q) for q in questions_raw]
    return QuizOut(id=quiz.id, subject=quiz.subject, topic=quiz.topic, difficulty=quiz.difficulty, questions=questions, source=source,
                   from_notes=bool(context), note_sources=note_sources)


@router.get("/{quiz_id}", response_model=QuizOut)
def get_quiz(
    quiz_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.student_id == current_student.id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    questions = [QuizQuestion(**q) for q in json.loads(quiz.questions_json)]
    return QuizOut(id=quiz.id, subject=quiz.subject, topic=quiz.topic, difficulty=quiz.difficulty, questions=questions)


@router.post("/submit", response_model=QuizResultOut)
def submit_quiz(
    payload: QuizSubmitRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    quiz = db.query(Quiz).filter(
        Quiz.id == payload.quiz_id, Quiz.student_id == current_student.id
    ).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = json.loads(quiz.questions_json)
    answers_by_index = {a.question_index: a.selected_index for a in payload.answers}

    correct_count = 0
    review = []
    for i, q in enumerate(questions):
        selected = answers_by_index.get(i, -1)
        is_correct = selected == q["correct_index"]
        if is_correct:
            correct_count += 1
        review.append({
            "question": q["question"],
            "options": q["options"],
            "correct_index": q["correct_index"],
            "selected_index": selected,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    total = len(questions)
    score = round((correct_count / total * 100), 1) if total else 0.0
    weak_topics = [quiz.topic] if score < 70 else []

    attempt = QuizAttempt(
        student_id=current_student.id,
        quiz_id=quiz.id,
        subject=quiz.subject,
        score=score,
        total_questions=total,
        correct_answers=correct_count,
        weak_topics_json=json.dumps(weak_topics),
        answers_json=json.dumps(review),
    )
    db.add(attempt)

    # Update subject progress average score (running average)
    subject = db.query(SubjectProgress).filter(
        SubjectProgress.student_id == current_student.id,
        SubjectProgress.subject == quiz.subject,
    ).first()
    if not subject:
        subject = SubjectProgress(student_id=current_student.id, subject=quiz.subject, total_topics=10)
        db.add(subject)
        db.flush()

    prior_attempts = db.query(QuizAttempt).filter(
        QuizAttempt.student_id == current_student.id, QuizAttempt.subject == quiz.subject
    ).count()
    if prior_attempts == 0:
        subject.average_score = score
    else:
        subject.average_score = round(((subject.average_score * prior_attempts) + score) / (prior_attempts + 1), 1)

    db.add(Activity(
        student_id=current_student.id,
        activity_type="quiz_taken",
        subject=quiz.subject,
        minutes=5,
    ))

    db.commit()

    return QuizResultOut(
        score=score,
        total_questions=total,
        correct_answers=correct_count,
        weak_topics=weak_topics,
        review=review,
    )


@router.get("/history/all")
def quiz_history(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == current_student.id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": a.id,
            "subject": a.subject,
            "score": a.score,
            "totalQuestions": a.total_questions,
            "correctAnswers": a.correct_answers,
            "createdAt": a.created_at.isoformat(),
        }
        for a in attempts
    ]
