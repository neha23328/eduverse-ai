from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_student
from app.database import get_db
from app.models.models import Student, LearningTask, Activity
from app.schemas.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(
    status: str = "",
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    query = db.query(LearningTask).filter(LearningTask.student_id == current_student.id)
    if status:
        query = query.filter(LearningTask.status == status)
    return query.order_by(LearningTask.due_date.asc().nulls_last(), LearningTask.created_at.desc()).all()


@router.post("", response_model=TaskOut)
def create_task(
    payload: TaskCreate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    task = LearningTask(
        student_id=current_student.id,
        title=payload.title,
        subject=payload.subject or "",
        due_date=payload.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    task = db.query(LearningTask).filter(
        LearningTask.id == task_id, LearningTask.student_id == current_student.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = payload.status
    if payload.status == "completed":
        task.completed_at = datetime.utcnow()
        db.add(Activity(
            student_id=current_student.id,
            activity_type="task_completed",
            subject=task.subject,
            minutes=0,
        ))
    else:
        task.completed_at = None

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    task = db.query(LearningTask).filter(
        LearningTask.id == task_id, LearningTask.student_id == current_student.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"status": "deleted"}
