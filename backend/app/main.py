from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import models  # noqa: F401 - ensures models are registered
from app.routers import (
    auth_router, chat_router, progress_router, tasks_router,
    quiz_router, content_router, planner_router, gamification_router, docs_router,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EduVerse AI API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"],
    allow_origin_regex=r"http://(192\.168|10)\.\d+\.\d+\.\d+:(5173|4173)",  # phones on the expo Wi-Fi
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(progress_router.router)
app.include_router(tasks_router.router)
app.include_router(quiz_router.router)
app.include_router(content_router.router)
app.include_router(planner_router.router)
app.include_router(gamification_router.router)
app.include_router(docs_router.router)


@app.get("/")
def root():
    return {"status": "EduVerse AI backend running"}


@app.get("/api/health")
def health():
    from app.config import settings
    return {
        "status": "ok",
        "model": settings.GEMINI_MODEL,
        "ai_key_set": bool(settings.GEMINI_API_KEY) and settings.GEMINI_API_KEY != "your_gemini_api_key_here",
        "demo_mode": settings.DEMO_MODE,
        "offline_fallback": settings.OFFLINE_FALLBACK,
    }
