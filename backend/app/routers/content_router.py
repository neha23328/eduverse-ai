import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.auth import get_current_student
from app.database import get_db
from app.models.models import Student
from app.services import ai_service, rag

router = APIRouter(prefix="/api/content", tags=["content"])


class ContentGenerateRequest(BaseModel):
    subject: str
    topic: str
    material_type: str = "notes"  # notes | summary | flashcards | revision
    level: str = "intermediate"
    use_notes: bool = False
    doc_ids: Optional[List[int]] = None


class ContentGenerateResponse(BaseModel):
    content: str
    material_type: str
    source: str = "live"
    from_notes: bool = False
    note_sources: List[dict] = []


@router.post("/generate", response_model=ContentGenerateResponse)
def generate_content(
    payload: ContentGenerateRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    context, note_sources = "", []
    if payload.use_notes:
        hits = rag.retrieve(db, current_student.id, f"{payload.subject} {payload.topic}", payload.doc_ids, k=6)
        if not hits:
            raise HTTPException(status_code=422, detail=(
                "Your notes don't seem to cover this topic. Try a different topic, "
                "upload more notes, or turn off 'Use my notes'."))
        context, note_sources = rag.build_context(hits), rag.sources_payload(hits)
    try:
        content, source = ai_service.generate_study_material(
            subject=payload.subject,
            topic=payload.topic,
            material_type=payload.material_type,
            level=payload.level,
            learning_style=current_student.learning_style or "",
            context=context,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {str(e)}")

    return ContentGenerateResponse(content=content, material_type=payload.material_type, source=source,
                                   from_notes=bool(context), note_sources=note_sources)


@router.post("/stream")
def stream_content(
    payload: ContentGenerateRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Server-sent events: study material appears as it is written instead of after a long wait."""
    context, note_sources = "", []
    if payload.use_notes:
        hits = rag.retrieve(db, current_student.id, f"{payload.subject} {payload.topic}", payload.doc_ids, k=6)
        if not hits:
            raise HTTPException(status_code=422, detail=(
                "Your notes don't seem to cover this topic. Try a different topic, "
                "upload more notes, or turn off 'Use my notes'."))
        context, note_sources = rag.build_context(hits), rag.sources_payload(hits)
    learning_style = current_student.learning_style or ""

    def sse(obj):
        return f"data: {json.dumps(obj)}\n\n"

    def gen():
        yield sse({"meta": {"from_notes": bool(context), "note_sources": note_sources}})
        source = "live"
        try:
            for kind, val in ai_service.stream_study_material(
                payload.subject, payload.topic, payload.material_type, payload.level, learning_style, context
            ):
                if kind == "chunk":
                    yield sse({"t": val})
                else:
                    source = val
        except Exception as e:
            yield sse({"error": str(e)})
            return
        yield sse({"done": True, "source": source})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
