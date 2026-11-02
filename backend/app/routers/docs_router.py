from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_student
from app.database import get_db
from app.models.models import Student, Document, DocChunk
from app.services import rag

router = APIRouter(prefix="/api/docs", tags=["knowledge-base"])


def _out(d: Document) -> dict:
    return {
        "id": d.id, "title": d.title, "filename": d.filename, "subject": d.subject,
        "chunks": d.n_chunks, "chars": d.n_chars, "semantic": bool(d.embedded),
        "createdAt": d.created_at.isoformat(),
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    subject: str = Form(""),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    data = await file.read()
    try:
        doc = rag.index_document(db, current_student.id, file.filename or "notes.txt", data, title, subject)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read this file: {e}")
    return _out(doc)


@router.get("")
def list_documents(current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.student_id == current_student.id).order_by(Document.created_at.desc()).all()
    return [_out(d) for d in docs]


@router.delete("/{doc_id}")
def delete_document(doc_id: int, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.student_id == current_student.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.query(DocChunk).filter(DocChunk.document_id == doc_id).delete()
    db.delete(doc)
    db.commit()
    return {"status": "deleted"}


@router.get("/status")
def rag_status(probe: bool = False, current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    """Is semantic search actually working? probe=true makes a real embedding call to find out."""
    return rag.status(db, current_student.id, probe=probe)


@router.post("/reindex")
def reindex(current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    """Adds semantic search to notes that were uploaded while embeddings were unavailable."""
    result = rag.reindex_missing(db, current_student.id)
    return {**result, **rag.status(db, current_student.id)}


@router.get("/search")
def search_notes(q: str, k: int = 5, doc_id: Optional[int] = None,
                 current_student: Student = Depends(get_current_student), db: Session = Depends(get_db)):
    """Shows exactly what the retriever finds (and why) - handy to demo RAG on stage."""
    hits, info = rag.retrieve_ex(db, current_student.id, q, [doc_id] if doc_id else None, k=max(1, min(k, 8)))
    return {
        "info": info,
        "hits": [{"title": h["title"], "page": h["page"], "score": h["score"], "coverage": h["coverage"],
                  "cosine": h["cosine"], "mode": h["mode"], "text": h["text"]} for h in hits],
    }
