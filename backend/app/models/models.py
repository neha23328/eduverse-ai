from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Date
)
from sqlalchemy.orm import relationship

from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    branch = Column(String(120), default="")
    semester = Column(String(20), default="")
    career_goal = Column(String(200), default="")
    learning_style = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    subjects = relationship("SubjectProgress", back_populates="student", cascade="all, delete-orphan")
    tasks = relationship("LearningTask", back_populates="student", cascade="all, delete-orphan")
    chats = relationship("ChatMessage", back_populates="student", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="student", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="student", cascade="all, delete-orphan")


class SubjectProgress(Base):
    __tablename__ = "subject_progress"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    subject = Column(String(120), nullable=False)
    completed_topics = Column(Integer, default=0)
    total_topics = Column(Integer, default=10)
    study_minutes = Column(Integer, default=0)
    average_score = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="subjects")


class LearningTask(Base):
    __tablename__ = "learning_tasks"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(120), default="")
    status = Column(String(20), default="pending")  # pending | completed
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    student = relationship("Student", back_populates="tasks")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    subject = Column(String(120), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="chats")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    subject = Column(String(120), nullable=False)
    topic = Column(String(200), default="")
    difficulty = Column(String(20), default="intermediate")
    questions_json = Column(Text, nullable=False)  # JSON string of questions
    created_at = Column(DateTime, default=datetime.utcnow)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    subject = Column(String(120), nullable=False)
    score = Column(Float, default=0.0)
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    weak_topics_json = Column(Text, default="[]")
    answers_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="quiz_attempts")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False)  # topic_completed, quiz_taken, study_session, task_completed
    subject = Column(String(120), default="")
    minutes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="activities")


class Document(Base):
    """A note/PDF a student uploaded for the RAG knowledge base."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), default="")
    subject = Column(String(120), default="")
    n_chunks = Column(Integer, default=0)
    n_chars = Column(Integer, default=0)
    embedded = Column(Boolean, default=False)  # True when semantic vectors were stored
    created_at = Column(DateTime, default=datetime.utcnow)


class DocChunk(Base):
    __tablename__ = "doc_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    idx = Column(Integer, default=0)
    page = Column(Integer, default=0)
    text = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)  # JSON list of floats, or NULL
