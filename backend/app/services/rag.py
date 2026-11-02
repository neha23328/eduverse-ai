"""Retrieval-Augmented Generation over a student's own notes.

Pipeline
    upload  -> extract text -> chunk (~900 chars, overlap, page numbers) -> embed -> SQLite
    question-> (rewrite follow-ups into a standalone query)
            -> keyword rank (BM25)  +  semantic rank (Gemini embeddings)
            -> reciprocal-rank fusion  -> ABSOLUTE relevance gate -> drop near-duplicates
            -> top-k passages go into the prompt, answer cites them as [1], [2] ...

Why these choices
    * Reciprocal-rank fusion instead of adding min-max scores: min-max makes the best
      chunk look "perfect" even when nothing is relevant, so irrelevant questions still
      got sources. Ranking decides ORDER; an absolute gate decides WHETHER anything is
      relevant at all.
    * Keyword search is always available (offline, instant). Embeddings are added when
      the API works. Every response says which mode was used.
"""
import io
import json
import math
import re
import urllib.request
from collections import Counter
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.models.models import Document, DocChunk

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_CHUNKS_PER_DOC = 400
CHUNK_CHARS = 900
CHUNK_OVERLAP = 150
RRF_K = 60
DUPLICATE_JACCARD = 0.7

# Last embedding problem, so the UI can show WHY semantic search is off.
LAST_EMBED_ERROR: Optional[str] = None

# ------------------------------------------------------------------ extraction

def extract_pages(filename: str, data: bytes) -> List[Tuple[int, str]]:
    """Returns [(page_number, text)]. Plain text files are a single 'page'."""
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append((i, text))
        return pages
    if name.endswith((".txt", ".md", ".markdown", ".csv")):
        return [(1, data.decode("utf-8", errors="ignore"))]
    raise ValueError("Unsupported file type. Upload a PDF, .txt or .md file.")


def _overlap_tail(text: str) -> str:
    """Last ~CHUNK_OVERLAP characters, starting at a word boundary (never mid-word)."""
    if len(text) <= CHUNK_OVERLAP:
        return text
    tail = text[-CHUNK_OVERLAP:]
    cut = tail.find(" ")
    return tail[cut + 1:] if 0 <= cut < len(tail) - 1 else tail


def chunk_pages(pages: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
    """Topic-aware chunks of ~CHUNK_CHARS. A heading starts a new chunk (so one passage = one topic);
    otherwise paragraphs are packed with a small word-aligned overlap. Keeps page numbers."""
    chunks: List[Tuple[int, str]] = []
    for page_no, text in pages:
        text = re.sub(r"[ \t]+", " ", text.replace("\r", ""))
        paras = [p.strip() for p in re.split(r"\n\s*\n|\n(?=[A-Z0-9#•\-])", text) if p.strip()]
        buf = ""
        for para in paras:
            if para.startswith("#") and len(buf) >= 200:      # new section: flush, no overlap across topics
                chunks.append((page_no, buf))
                buf = para
                continue
            if len(buf) + len(para) + 1 <= CHUNK_CHARS:
                buf = f"{buf}\n{para}".strip()
                continue
            if buf:
                chunks.append((page_no, buf))
                buf = _overlap_tail(buf) + "\n" + para
            else:
                buf = para
            while len(buf) > CHUNK_CHARS * 1.5:       # very long paragraph
                cut = buf.rfind(" ", 0, CHUNK_CHARS)
                cut = cut if cut > CHUNK_CHARS // 2 else CHUNK_CHARS
                chunks.append((page_no, buf[:cut]))
                buf = _overlap_tail(buf[:cut]) + " " + buf[cut:].lstrip()
        if buf.strip():
            chunks.append((page_no, buf.strip()))
    return chunks[:MAX_CHUNKS_PER_DOC]

# ------------------------------------------------------------------ BM25

_STOP = set("""a an the and or but if then of to in on for with by at from as is are was were be been being it its this that
these those i you he she we they them his her our your do does did done can could should would may might will shall not no
yes what which who whom when where why how about into over under than so such also very just more most some any each
explain tell give show please define describe""".split())


def _stem(w: str) -> str:
    for suf in ("ing", "edly", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def tokenize(text: str) -> List[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 1]


def _bm25(query_tokens: List[str], docs_tokens: List[List[str]], k1=1.5, b=0.75) -> List[float]:
    n = len(docs_tokens)
    if n == 0 or not query_tokens:
        return [0.0] * n
    avgdl = sum(len(d) for d in docs_tokens) / n or 1.0
    df = Counter()
    for d in docs_tokens:
        for t in set(d):
            df[t] += 1
    scores = []
    for d in docs_tokens:
        tf = Counter(d)
        s = 0.0
        for q in set(query_tokens):
            if q not in tf:
                continue
            idf = math.log(1 + (n - df[q] + 0.5) / (df[q] + 0.5))
            s += idf * tf[q] * (k1 + 1) / (tf[q] + k1 * (1 - b + b * len(d) / avgdl))
        scores.append(s)
    return scores

# ------------------------------------------------------------------ embeddings (REST, no extra SDK)

_EMB_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _key_ok() -> bool:
    k = settings.GEMINI_API_KEY
    return bool(k) and k != "your_gemini_api_key_here"


def embeddings_enabled() -> bool:
    return bool(settings.USE_EMBEDDINGS and not settings.DEMO_MODE and _key_ok())


def embed_texts(texts: List[str], task: str) -> Optional[List[List[float]]]:
    """task: RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY. Returns None on ANY failure (keyword search takes over)."""
    global LAST_EMBED_ERROR
    if not texts:
        return None
    if not embeddings_enabled():
        LAST_EMBED_ERROR = ("embeddings are switched off (USE_EMBEDDINGS / DEMO_MODE)" if _key_ok()
                            else "no Gemini API key set")
        return None
    out: List[List[float]] = []
    try:
        for i in range(0, len(texts), 50):
            batch = texts[i:i + 50]
            body = {"requests": [{
                "model": f"models/{settings.EMBED_MODEL}",
                "content": {"parts": [{"text": t[:2000]}]},
                "taskType": task,
                "outputDimensionality": 768,
            } for t in batch]}
            req = urllib.request.Request(
                f"{_EMB_BASE}/{settings.EMBED_MODEL}:batchEmbedContents",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "x-goog-api-key": settings.GEMINI_API_KEY},
            )
            with urllib.request.urlopen(req, timeout=settings.AI_TIMEOUT_SECONDS) as r:
                data = json.loads(r.read().decode("utf-8"))
            out.extend(e["values"] for e in data["embeddings"])
        if len(out) != len(texts):
            raise ValueError("embedding count mismatch")
        LAST_EMBED_ERROR = None
        return out
    except Exception as e:  # network, quota, wrong model name ... -> keyword search only
        LAST_EMBED_ERROR = f"{type(e).__name__}: {str(e)[:160]}"
        print(f"[rag] embeddings unavailable ({LAST_EMBED_ERROR}) - using keyword search")
        return None


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)

# ------------------------------------------------------------------ indexing

def index_document(db: Session, student_id: int, filename: str, data: bytes,
                   title: str = "", subject: str = "") -> Document:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File too large (max 10 MB).")
    pages = extract_pages(filename, data)
    chunks = chunk_pages(pages)
    if not chunks:
        raise ValueError("No readable text found (scanned/image-only PDFs need OCR).")

    vectors = embed_texts([c[1] for c in chunks], "RETRIEVAL_DOCUMENT")
    doc = Document(
        student_id=student_id, title=(title or filename.rsplit(".", 1)[0])[:255], filename=filename[:255],
        subject=subject or "", n_chunks=len(chunks), n_chars=sum(len(c[1]) for c in chunks),
        embedded=vectors is not None,
    )
    db.add(doc)
    db.flush()
    for i, (page, text) in enumerate(chunks):
        db.add(DocChunk(
            document_id=doc.id, student_id=student_id, idx=i, page=page, text=text,
            embedding_json=json.dumps(vectors[i]) if vectors else None,
        ))
    db.commit()
    db.refresh(doc)
    return doc


def reindex_missing(db: Session, student_id: int) -> Dict[str, int]:
    """Adds embeddings to documents that were uploaded while embeddings were unavailable."""
    updated, failed = 0, 0
    docs = db.query(Document).filter(Document.student_id == student_id, Document.embedded == False).all()  # noqa: E712
    for d in docs:
        chunks = db.query(DocChunk).filter(DocChunk.document_id == d.id).order_by(DocChunk.idx).all()
        vectors = embed_texts([c.text for c in chunks], "RETRIEVAL_DOCUMENT")
        if not vectors:
            failed += 1
            continue
        for c, v in zip(chunks, vectors):
            c.embedding_json = json.dumps(v)
        d.embedded = True
        updated += 1
    db.commit()
    return {"updated": updated, "failed": failed}


def status(db: Session, student_id: int, probe: bool = False) -> dict:
    docs = db.query(Document).filter(Document.student_id == student_id).all()
    chunks = db.query(DocChunk).filter(DocChunk.student_id == student_id).count()
    embedded = db.query(DocChunk).filter(DocChunk.student_id == student_id, DocChunk.embedding_json.isnot(None)).count()
    out = {
        "documents": len(docs), "passages": chunks, "embeddedPassages": embedded,
        "embeddingsEnabled": embeddings_enabled(), "embedModel": settings.EMBED_MODEL,
        "pendingDocuments": sum(1 for d in docs if not d.embedded),
        "lastError": LAST_EMBED_ERROR,
    }
    if probe:   # a real call, so the page can show the truth instead of a guess
        ok = embed_texts(["connection test"], "RETRIEVAL_QUERY") is not None
        out["probeOk"] = ok
        out["lastError"] = None if ok else LAST_EMBED_ERROR
    return out

# ------------------------------------------------------------------ retrieval

def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def has_documents(db: Session, student_id: int, doc_ids: Optional[List[int]] = None) -> bool:
    q = db.query(DocChunk.id).filter(DocChunk.student_id == student_id)
    if doc_ids:
        q = q.filter(DocChunk.document_id.in_(doc_ids))
    return q.first() is not None


def retrieve_ex(db: Session, student_id: int, query: str, doc_ids: Optional[List[int]] = None,
                k: Optional[int] = None) -> Tuple[List[dict], dict]:
    """Returns (hits, info). `hits` is empty when nothing in the notes is genuinely relevant."""
    k = k or settings.RAG_TOP_K
    q = db.query(DocChunk, Document.title).join(Document, Document.id == DocChunk.document_id) \
        .filter(DocChunk.student_id == student_id)
    if doc_ids:
        q = q.filter(DocChunk.document_id.in_(doc_ids))
    rows = q.all()
    info = {"mode": "keyword", "considered": len(rows), "passed": 0, "embeddingError": None}
    if not rows:
        return [], info

    qt = tokenize(query)
    qset = set(qt)
    chunk_tokens = [tokenize(c.text) for c, _ in rows]
    chunk_sets = [set(t) for t in chunk_tokens]
    kw = _bm25(qt, chunk_tokens)
    coverage = [(len(qset & s) / len(qset)) if qset else 0.0 for s in chunk_sets]

    cos: List[Optional[float]] = [None] * len(rows)
    if any(c.embedding_json for c, _ in rows):
        qv = embed_texts([query], "RETRIEVAL_QUERY")
        if qv:
            info["mode"] = "hybrid"
            for i, (c, _) in enumerate(rows):
                if c.embedding_json:
                    cos[i] = _cosine(qv[0], json.loads(c.embedding_json))
        else:
            info["embeddingError"] = LAST_EMBED_ERROR

    # --- rank fusion decides the ORDER
    fused = [0.0] * len(rows)
    kw_order = sorted((i for i in range(len(rows)) if kw[i] > 0), key=lambda i: kw[i], reverse=True)
    for rank, i in enumerate(kw_order):
        fused[i] += 1.0 / (RRF_K + rank + 1)
    sem_order = sorted((i for i in range(len(rows)) if cos[i] is not None), key=lambda i: cos[i], reverse=True)
    for rank, i in enumerate(sem_order):
        fused[i] += 1.0 / (RRF_K + rank + 1)

    # --- absolute gate decides WHETHER a passage is relevant at all
    def passes(i: int) -> bool:
        if coverage[i] >= settings.RAG_MIN_COVERAGE:
            return True
        return cos[i] is not None and cos[i] >= settings.RAG_MIN_COSINE

    candidates = sorted((i for i in range(len(rows)) if passes(i)), key=lambda i: fused[i], reverse=True)
    info["passed"] = len(candidates)

    chosen: List[int] = []
    for i in candidates:
        if any(_jaccard(chunk_sets[i], chunk_sets[j]) > DUPLICATE_JACCARD for j in chosen):
            continue
        chosen.append(i)
        if len(chosen) >= k:
            break

    hits = []
    for i in chosen:
        c, title = rows[i]
        sem_rel = max(0.0, min(1.0, (cos[i] - 0.45) / 0.40)) if cos[i] is not None else 0.0
        hits.append({
            "chunk_id": c.id, "doc_id": c.document_id, "title": title, "page": c.page, "idx": c.idx,
            "text": c.text, "score": round(max(coverage[i], sem_rel), 3),
            "coverage": round(coverage[i], 2), "cosine": round(cos[i], 3) if cos[i] is not None else None,
            "mode": info["mode"],
        })
    return hits, info


def retrieve(db: Session, student_id: int, query: str, doc_ids: Optional[List[int]] = None, k: Optional[int] = None) -> List[dict]:
    return retrieve_ex(db, student_id, query, doc_ids, k)[0]


def build_context(hits: List[dict]) -> str:
    return "\n\n".join(f"[{i}] ({h['title']}, p.{h['page']})\n{h['text']}" for i, h in enumerate(hits, start=1))


def sources_payload(hits: List[dict]) -> List[dict]:
    return [{"n": i, "doc_id": h["doc_id"], "title": h["title"], "page": h["page"],
             "snippet": h["text"][:400], "score": h["score"], "mode": h["mode"]}
            for i, h in enumerate(hits, 1)]


def cited_numbers(reply: str, n_sources: int) -> List[int]:
    """Which [n] markers the model actually used (ignores numbers that don't exist)."""
    nums = {int(m) for m in re.findall(r"\[(\d{1,2})\]", reply)}
    return sorted(n for n in nums if 1 <= n <= n_sources)
