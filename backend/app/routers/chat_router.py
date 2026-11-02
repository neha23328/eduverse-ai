import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_student
from app.database import get_db, SessionLocal
from app.models.models import Student, ChatMessage, Activity
from app.schemas.schemas import ChatRequest, ChatResponse, ChatMessageOut
from app.services import ai_service, rag

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _context(student: Student) -> dict:
    return {
        "branch": student.branch,
        "semester": student.semester,
        "career_goal": student.career_goal,
        "learning_style": student.learning_style,
    }


def _recent_history(db: Session, student_id: int):
    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.student_id == student_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(7)
        .all()
    )
    # newest-first -> oldest-first; drop the message we just saved (last one)
    return [{"role": m.role, "content": m.content} for m in reversed(recent)][:-1]


@router.post("", response_model=ChatResponse)
def send_message(
    payload: ChatRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Non-streaming endpoint (kept for compatibility)."""
    db.add(ChatMessage(student_id=current_student.id, role="user",
                       content=payload.message, subject=payload.subject or ""))
    db.commit()
    history = _recent_history(db, current_student.id)

    parts, source = [], "live"
    try:
        for kind, val in ai_service.stream_mentor(
            payload.message, payload.subject or "", payload.level or "intermediate",
            history, _context(current_student),
        ):
            if kind == "chunk":
                parts.append(val)
            else:
                source = val
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {e}")

    reply = "".join(parts).strip()
    msg = ChatMessage(student_id=current_student.id, role="assistant", content=reply,
                      subject=payload.subject or "")
    db.add(msg)
    db.add(Activity(student_id=current_student.id, activity_type="chat_session",
                    subject=payload.subject or "", minutes=1))
    db.commit()
    db.refresh(msg)
    return ChatResponse(reply=reply, history_id=msg.id, source=source)


def _notes_mode(payload: ChatRequest) -> str:
    mode = (payload.notes_mode or ("only" if payload.use_docs else "auto")).lower()
    return mode if mode in ("auto", "only", "off") else "auto"


@router.post("/stream")
def stream_message(
    payload: ChatRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Server-sent events: tokens appear in the UI as soon as Gemini produces them.

    Notes modes
      auto - if the student has notes, search them first; ground + cite the answer when
             something relevant is found, otherwise answer normally and say the notes had no match.
      only - answer strictly from the notes (says so when they don't cover the question).
      off  - ignore the notes.
    """
    student_id = current_student.id
    ctx = _context(current_student)
    subject = payload.subject or ""
    level = payload.level or "intermediate"
    mode = _notes_mode(payload)

    db.add(ChatMessage(student_id=student_id, role="user", content=payload.message, subject=subject))
    db.commit()
    history = _recent_history(db, student_id)
    message = payload.message

    # --- RAG: retrieve from the student's own notes ---
    hits, context, fallback, rag_meta = [], "", "", {"mode": mode, "searched": False}
    if mode != "off" and rag.has_documents(db, student_id, payload.doc_ids):
        t_r = time.time()
        query = ai_service.condense_query(message, history)
        hits, info = rag.retrieve_ex(db, student_id, query, payload.doc_ids)
        rag_meta = {
            "mode": mode, "searched": True, "query": query if query != message else "",
            "retrieval": info["mode"], "considered": info["considered"], "found": len(hits),
            "embeddingError": info.get("embeddingError"), "ms": int((time.time() - t_r) * 1000),
        }
        if hits:
            context = rag.build_context(hits)
            fallback = ("**Offline mode** - the AI can't write an answer right now, but these are the most relevant "
                        "parts of your notes:\n\n" + "\n\n".join(
                            f"**[{i}] {h['title']} (p.{h['page']})**\n{h['text'][:500]}" for i, h in enumerate(hits, 1)))
        elif mode == "only":
            context = "(No relevant excerpts were found in the student's notes.)"
    sources = rag.sources_payload(hits)

    def sse(obj):
        return f"data: {json.dumps(obj)}\n\n"

    def gen():
        t0 = time.time()
        first = None
        parts, source = [], "live"
        if rag_meta.get("searched") or mode == "only":
            yield sse({"sources": sources, "rag": rag_meta, "grounded": bool(hits)})
        try:
            for kind, val in ai_service.stream_mentor(message, subject, level, history, ctx, context, fallback,
                                                      strict=(mode == "only")):
                if kind == "chunk":
                    if first is None:
                        first = round(time.time() - t0, 2)
                        yield sse({"first_token_s": first})
                    parts.append(val)
                    yield sse({"t": val})
                else:
                    source = val
        except Exception as e:
            yield sse({"error": str(e)})
            return

        reply = "".join(parts).strip()
        # Own session: the request-scoped one may already be closed while streaming.
        s = SessionLocal()
        try:
            msg = ChatMessage(student_id=student_id, role="assistant", content=reply, subject=subject)
            s.add(msg)
            s.add(Activity(student_id=student_id, activity_type="chat_session", subject=subject, minutes=1))
            s.commit()
            s.refresh(msg)
            mid = msg.id
        finally:
            s.close()
        yield sse({"done": True, "id": mid, "source": source, "total_s": round(time.time() - t0, 2),
                   "cited": rag.cited_numbers(reply, len(hits)) if hits else []})

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history", response_model=list[ChatMessageOut])
def get_history(
    subject: str = "",
    limit: int = 50,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    query = db.query(ChatMessage).filter(ChatMessage.student_id == current_student.id)
    if subject:
        query = query.filter(ChatMessage.subject == subject)
    # newest N, returned oldest-first
    rows = query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
    return list(reversed(rows))


@router.delete("/history")
def clear_history(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    db.query(ChatMessage).filter(ChatMessage.student_id == current_student.id).delete()
    db.commit()
    return {"status": "cleared"}
