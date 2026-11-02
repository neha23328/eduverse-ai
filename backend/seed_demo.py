"""Create a ready-to-demo account plus a few classmates for the leaderboard.

    python seed_demo.py            # adds demo data
    python seed_demo.py --reset    # wipes eduverse.db first

Login:  demo@eduverse.ai / demo1234
"""
import json
import os
import random
import sys
from datetime import datetime, timedelta

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import models as m

if "--reset" in sys.argv:
    path = "eduverse.db"
    engine.dispose()
    if os.path.exists(path):
        os.remove(path)

Base.metadata.create_all(bind=engine)
db = SessionLocal()
random.seed(7)

if db.query(m.Student).filter(m.Student.email == "demo@eduverse.ai").first():
    print("Demo data already present (use --reset to rebuild).")
    raise SystemExit

PEOPLE = [
    # name, email, xp-ish "intensity"
    ("Ananya Sharma", "demo@eduverse.ai", 0.75),
    ("Rohan Mehta", "rohan@eduverse.ai", 1.0),
    ("Simran Kaur", "simran@eduverse.ai", 0.9),
    ("Arjun Verma", "arjun@eduverse.ai", 0.55),
    ("Kavya Nair", "kavya@eduverse.ai", 0.4),
]
SUBJECTS = [("Data Structures", 10), ("Machine Learning", 12), ("Operating Systems", 10), ("Mathematics", 8)]
TASKS = ["Revise linked lists", "Solve 5 DP problems", "Read ML regularization notes",
         "Finish OS scheduling worksheet", "Practice matrix problems", "Mock quiz: Trees",
         "Summarize deadlocks", "Implement k-means", "Review probability", "Complete lab record"]

for name, email, k in PEOPLE:
    st = m.Student(
        name=name, email=email, hashed_password=hash_password("demo1234"),
        branch="MCA (AI/ML)", semester="2", career_goal="GenAI engineer",
        learning_style="",
    )
    db.add(st)
    db.flush()

    for subj, total in SUBJECTS:
        done = int(total * random.uniform(0.2, 0.9) * k)
        db.add(m.SubjectProgress(
            student_id=st.id, subject=subj, total_topics=total, completed_topics=done,
            study_minutes=int(random.randint(40, 240) * k),
            average_score=round(random.uniform(52, 93) * (0.8 + 0.2 * k), 1),
        ))

    for i, title in enumerate(TASKS):
        if random.random() < k:
            done = random.random() < 0.6 * k + 0.2
            db.add(m.LearningTask(
                student_id=st.id, title=title, subject=random.choice(SUBJECTS)[0],
                status="completed" if done else "pending",
                completed_at=datetime.utcnow() - timedelta(days=random.randint(0, 5)) if done else None,
            ))

    # activity over the last 7 days (today included => live streak)
    for d in range(7):
        for _ in range(random.randint(1, 3)):
            db.add(m.Activity(
                student_id=st.id, activity_type=random.choice(["study_session", "quiz_taken", "chat_session"]),
                subject=random.choice(SUBJECTS)[0], minutes=random.randint(10, 45),
                created_at=datetime.utcnow() - timedelta(days=d, hours=random.randint(0, 5)),
            ))

    # a few quiz attempts (one weak topic so the dashboard has content)
    for j in range(int(2 + 4 * k)):
        subj = random.choice(SUBJECTS)[0]
        q = m.Quiz(student_id=st.id, subject=subj, topic="Core concepts", difficulty="intermediate",
                   questions_json=json.dumps([]))
        db.add(q)
        db.flush()
        score = random.choice([55, 60, 80, 90, 100])
        db.add(m.QuizAttempt(
            student_id=st.id, quiz_id=q.id, subject=subj, score=score, total_questions=5,
            correct_answers=score // 20,
            weak_topics_json=json.dumps(["Dynamic Programming"] if score < 70 else []),
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 6)),
        ))

db.commit()
print("Seeded. Login with  demo@eduverse.ai / demo1234")
