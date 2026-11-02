from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_student
from app.database import get_db
from app.models.models import Student, SubjectProgress
from app.schemas.schemas import StudyPlanRequest
from app.services import ai_service
from app.routers.progress_router import _subject_to_out

router = APIRouter(prefix="/api/planner", tags=["planner"])


@router.post("/generate")
def generate_plan(
    payload: StudyPlanRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    subjects = db.query(SubjectProgress).filter(SubjectProgress.student_id == current_student.id).all()
    subject_data = [_subject_to_out(s).model_dump() for s in subjects]

    goal = payload.goal or current_student.career_goal

    try:
        plan, source = ai_service.generate_study_plan(
            subject_progress=subject_data,
            goal=goal,
            hours_per_day=payload.hours_per_day,
            days=payload.days,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

    plan["source"] = source
    return plan
