from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class StudentCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=6)
    branch: Optional[str] = ""
    semester: Optional[str] = ""
    career_goal: Optional[str] = ""
    learning_style: Optional[str] = ""


class StudentLogin(BaseModel):
    email: EmailStr
    password: str


class StudentOut(BaseModel):
    id: int
    name: str
    email: str
    branch: str
    semester: str
    career_goal: str
    learning_style: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student: StudentOut


class StudentProfileUpdate(BaseModel):
    branch: Optional[str] = None
    semester: Optional[str] = None
    career_goal: Optional[str] = None
    learning_style: Optional[str] = None


# ---------- Chat / AI Mentor ----------

class ChatRequest(BaseModel):
    message: str
    subject: Optional[str] = ""
    level: Optional[str] = "intermediate"  # beginner | intermediate | advanced
    use_docs: Optional[bool] = False       # legacy flag: True == notes_mode "only"
    notes_mode: Optional[str] = None       # auto (default) | only | off
    doc_ids: Optional[List[int]] = None    # restrict to these documents (default: all)


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    subject: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    reply: str
    history_id: int
    source: str = "live"


# ---------- Subjects / Progress ----------

class SubjectProgressOut(BaseModel):
    subject: str
    completedTopics: int
    totalTopics: int
    percentage: float
    averageScore: float
    studyMinutes: int

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    subject: str
    total_topics: int = 10


class DashboardSummary(BaseModel):
    overallProgress: float
    completedTasks: int
    pendingTasks: int
    averageScore: float
    studyStreak: int
    totalStudyMinutes: int


# ---------- Tasks ----------

class TaskCreate(BaseModel):
    title: str
    subject: Optional[str] = ""
    due_date: Optional[date] = None


class TaskOut(BaseModel):
    id: int
    title: str
    subject: str
    status: str
    due_date: Optional[date]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskUpdate(BaseModel):
    status: str


# ---------- Quiz ----------

class QuizGenerateRequest(BaseModel):
    subject: str
    topic: str
    difficulty: str = "intermediate"  # beginner | intermediate | advanced
    num_questions: int = 5
    use_notes: bool = False                # build the quiz from the student's own notes (RAG)
    doc_ids: Optional[List[int]] = None


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    explanation: str


class QuizOut(BaseModel):
    id: int
    subject: str
    topic: str
    difficulty: str
    questions: List[QuizQuestion]
    source: str = "live"
    from_notes: bool = False
    note_sources: List[dict] = []


class QuizSubmitAnswer(BaseModel):
    question_index: int
    selected_index: int


class QuizSubmitRequest(BaseModel):
    quiz_id: int
    answers: List[QuizSubmitAnswer]


class QuizResultOut(BaseModel):
    score: float
    total_questions: int
    correct_answers: int
    weak_topics: List[str]
    review: List[dict]


# ---------- Activity ----------

class ActivityCreate(BaseModel):
    activityType: str
    subject: Optional[str] = ""
    minutes: Optional[int] = 0
    topicId: Optional[str] = None


# ---------- Study Planner ----------

class StudyPlanRequest(BaseModel):
    goal: Optional[str] = ""
    hours_per_day: float = 2.0
    days: int = 7
