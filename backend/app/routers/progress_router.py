from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_student
from app.database import get_db
from app.models.models import Student, SubjectProgress, LearningTask, Activity, QuizAttempt
from app.schemas.schemas import (
    SubjectProgressOut, SubjectCreate, DashboardSummary, ActivityCreate
)

router = APIRouter(prefix="/api/progress", tags=["progress"])


def _subject_to_out(s: SubjectProgress) -> SubjectProgressOut:
    pct = (s.completed_topics / s.total_topics * 100) if s.total_topics else 0
    return SubjectProgressOut(
        subject=s.subject,
        completedTopics=s.completed_topics,
        totalTopics=s.total_topics,
        percentage=round(pct, 1),
        averageScore=round(s.average_score, 1),
        studyMinutes=s.study_minutes,
    )


def _calc_study_streak(db: Session, student_id: int) -> int:
    """Count consecutive days (including today) with at least one activity."""
    since = datetime.utcnow() - timedelta(days=120)
    rows = (
        db.query(Activity.created_at)
        .filter(Activity.student_id == student_id, Activity.created_at >= since)
        .all()
    )
    if not rows:
        return 0

    days_with_activity = sorted({r[0].date() for r in rows}, reverse=True)
    today = datetime.utcnow().date()

    streak = 0
    expected_day = today
    for day in days_with_activity:
        if day == expected_day:
            streak += 1
            expected_day = expected_day - timedelta(days=1)
        elif day == expected_day + timedelta(days=1):
            continue
        else:
            break
    return streak


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    subjects = db.query(SubjectProgress).filter(SubjectProgress.student_id == current_student.id).all()

    if subjects:
        total_completed = sum(s.completed_topics for s in subjects)
        total_topics = sum(s.total_topics for s in subjects) or 1
        overall_progress = round(total_completed / total_topics * 100, 1)
        scored_subjects = [s for s in subjects if s.average_score > 0]
        avg_score = round(sum(s.average_score for s in scored_subjects) / len(scored_subjects), 1) if scored_subjects else 0.0
        total_minutes = sum(s.study_minutes for s in subjects)
    else:
        overall_progress = 0.0
        avg_score = 0.0
        total_minutes = 0

    completed_tasks = db.query(LearningTask).filter(
        LearningTask.student_id == current_student.id, LearningTask.status == "completed"
    ).count()
    pending_tasks = db.query(LearningTask).filter(
        LearningTask.student_id == current_student.id, LearningTask.status == "pending"
    ).count()

    streak = _calc_study_streak(db, current_student.id)

    return DashboardSummary(
        overallProgress=overall_progress,
        completedTasks=completed_tasks,
        pendingTasks=pending_tasks,
        averageScore=avg_score,
        studyStreak=streak,
        totalStudyMinutes=total_minutes,
    )


@router.get("/subjects", response_model=list[SubjectProgressOut])
def get_subjects(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    subjects = db.query(SubjectProgress).filter(SubjectProgress.student_id == current_student.id).all()
    return [_subject_to_out(s) for s in subjects]


@router.post("/subjects", response_model=SubjectProgressOut)
def create_subject(
    payload: SubjectCreate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    existing = db.query(SubjectProgress).filter(
        SubjectProgress.student_id == current_student.id,
        SubjectProgress.subject == payload.subject,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subject already being tracked")

    subject = SubjectProgress(
        student_id=current_student.id,
        subject=payload.subject,
        total_topics=payload.total_topics,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _subject_to_out(subject)


@router.get("/weekly")
def get_weekly_activity(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Study minutes per day for the last 7 days."""
    today = datetime.utcnow().date()
    start = datetime.combine(today - timedelta(days=6), datetime.min.time())
    rows = (
        db.query(Activity.created_at, Activity.minutes)
        .filter(Activity.student_id == current_student.id, Activity.created_at >= start)
        .all()
    )
    per_day = {}
    for created, minutes in rows:
        per_day[created.date()] = per_day.get(created.date(), 0) + (minutes or 0)
    result = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        result.append({"date": day.isoformat(), "day": day.strftime("%a"), "minutes": per_day.get(day, 0)})
    return result


@router.post("/activity")
def log_activity(
    payload: ActivityCreate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    activity = Activity(
        student_id=current_student.id,
        activity_type=payload.activityType,
        subject=payload.subject or "",
        minutes=payload.minutes or 0,
    )
    db.add(activity)

    # If it's a topic completion, bump the subject's completed_topics
    if payload.activityType == "topic_completed" and payload.subject:
        subject = db.query(SubjectProgress).filter(
            SubjectProgress.student_id == current_student.id,
            SubjectProgress.subject == payload.subject,
        ).first()
        if subject and subject.completed_topics < subject.total_topics:
            subject.completed_topics += 1
        if subject:
            subject.study_minutes += payload.minutes or 0

    if payload.activityType == "study_session" and payload.subject:
        subject = db.query(SubjectProgress).filter(
            SubjectProgress.student_id == current_student.id,
            SubjectProgress.subject == payload.subject,
        ).first()
        if subject:
            subject.study_minutes += payload.minutes or 0

    db.commit()
    return {"status": "saved"}


@router.get("/weak-topics")
def get_weak_topics(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == current_student.id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(10)
        .all()
    )
    import json
    weak = []
    for a in attempts:
        try:
            topics = json.loads(a.weak_topics_json)
            weak.extend(topics)
        except Exception:
            pass
    # dedupe, preserve order
    seen = set()
    unique_weak = []
    for t in weak:
        if t not in seen:
            seen.add(t)
            unique_weak.append(t)
    return unique_weak[:10]
