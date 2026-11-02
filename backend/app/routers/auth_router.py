from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import verify_password, hash_password, create_access_token, get_current_student
from app.database import get_db
from app.models.models import Student
from app.schemas.schemas import StudentCreate, StudentLogin, Token, StudentOut, StudentProfileUpdate

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=Token)
def register(payload: StudentCreate, db: Session = Depends(get_db)):
    existing = db.query(Student).filter(Student.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    student = Student(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        branch=payload.branch or "",
        semester=payload.semester or "",
        career_goal=payload.career_goal or "",
        learning_style=payload.learning_style or "",
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    token = create_access_token({"sub": str(student.id)})
    return Token(access_token=token, student=StudentOut.model_validate(student))


@router.post("/login", response_model=Token)
def login(payload: StudentLogin, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.email == payload.email).first()
    if not student or not verify_password(payload.password, student.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": str(student.id)})
    return Token(access_token=token, student=StudentOut.model_validate(student))


@router.get("/me", response_model=StudentOut)
def get_me(current_student: Student = Depends(get_current_student)):
    return current_student


@router.patch("/me", response_model=StudentOut)
def update_profile(
    payload: StudentProfileUpdate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_student, field, value)
    db.commit()
    db.refresh(current_student)
    return current_student
