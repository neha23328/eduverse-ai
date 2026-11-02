import math
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_student
from app.database import get_db
from app.models.models import (
    Student, Activity, QuizAttempt, LearningTask, SubjectProgress, ChatMessage,
)
from app.routers.progress_router import _calc_study_streak

router = APIRouter(prefix="/api/gamification", tags=["gamification"])

XP_RULES = {
    "chat": 2,          # per mentor question
    "quiz": 20,         # per quiz taken
    "quiz_pass": 15,    # bonus when score >= 70
    "task": 10,         # per completed task
    "topic": 30,        # per completed topic
    "minutes_per_xp": 5,
}


def level_for(xp: int) -> int:
    return int(math.sqrt(xp / 50)) + 1


def xp_for_level(level: int) -> int:
    return 50 * (level - 1) ** 2


def _xp_table(db: Session) -> dict:
    """XP for every student using a handful of GROUP BY queries."""
    xp = defaultdict(int)
    for sid, n in db.query(ChatMessage.student_id, func.count()).filter(ChatMessage.role == "user").group_by(ChatMessage.student_id):
        xp[sid] += n * XP_RULES["chat"]
    for sid, n in db.query(QuizAttempt.student_id, func.count()).group_by(QuizAttempt.student_id):
        xp[sid] += n * XP_RULES["quiz"]
    for sid, n in db.query(QuizAttempt.student_id, func.count()).filter(QuizAttempt.score >= 70).group_by(QuizAttempt.student_id):
        xp[sid] += n * XP_RULES["quiz_pass"]
    for sid, n in db.query(LearningTask.student_id, func.count()).filter(LearningTask.status == "completed").group_by(LearningTask.student_id):
        xp[sid] += n * XP_RULES["task"]
    for sid, topics, minutes in db.query(
        SubjectProgress.student_id, func.sum(SubjectProgress.completed_topics), func.sum(SubjectProgress.study_minutes)
    ).group_by(SubjectProgress.student_id):
        xp[sid] += int(topics or 0) * XP_RULES["topic"] + int(minutes or 0) // XP_RULES["minutes_per_xp"]
    return xp


@router.get("/me")
def my_gamification(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    sid = current_student.id
    table = _xp_table(db)
    my_xp = table.get(sid, 0)
    level = level_for(my_xp)
    cur_floor, nxt = xp_for_level(level), xp_for_level(level + 1)

    quizzes = db.query(QuizAttempt).filter(QuizAttempt.student_id == sid).all()
    best = max((q.score for q in quizzes), default=0)
    chats = db.query(ChatMessage).filter(ChatMessage.student_id == sid, ChatMessage.role == "user").count()
    done_tasks = db.query(LearningTask).filter(LearningTask.student_id == sid, LearningTask.status == "completed").count()
    subjects = db.query(SubjectProgress).filter(SubjectProgress.student_id == sid).all()
    topics = sum(s.completed_topics for s in subjects)
    minutes = sum(s.study_minutes for s in subjects)
    streak = _calc_study_streak(db, sid)

    badges = [
        ("first_quiz", "First Quiz", "🎯", "Complete your first quiz", len(quizzes) >= 1),
        ("quiz_ace", "Quiz Ace", "🏆", "Score 90%+ on a quiz", best >= 90),
        ("curious", "Curious Mind", "💡", "Ask the AI Mentor 10 questions", chats >= 10),
        ("streak3", "On a Roll", "🔥", "3-day study streak", streak >= 3),
        ("streak7", "Unstoppable", "⚡", "7-day study streak", streak >= 7),
        ("tasker", "Task Master", "✅", "Complete 10 tasks", done_tasks >= 10),
        ("explorer", "Topic Explorer", "🧭", "Complete 5 topics", topics >= 5),
        ("hundred", "Century", "⏱️", "Study for 100 minutes", minutes >= 100),
    ]

    top = sorted(table.items(), key=lambda kv: kv[1], reverse=True)[:5]
    names = {s.id: s.name for s in db.query(Student).filter(Student.id.in_([i for i, _ in top] + [sid])).all()}
    board = [
        {"rank": i + 1, "name": names.get(i_id, "Student"), "xp": x, "level": level_for(x), "isMe": i_id == sid}
        for i, (i_id, x) in enumerate(top)
    ]
    if not any(b["isMe"] for b in board):
        rank = 1 + sum(1 for v in table.values() if v > my_xp)
        board.append({"rank": rank, "name": current_student.name, "xp": my_xp, "level": level, "isMe": True})

    return {
        "xp": my_xp,
        "level": level,
        "levelStartXp": cur_floor,
        "nextLevelXp": nxt,
        "streak": streak,
        "badges": [{"id": b[0], "name": b[1], "icon": b[2], "desc": b[3], "earned": b[4]} for b in badges],
        "leaderboard": board,
    }
