from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env regardless of the folder uvicorn is started from
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8-sig", extra="ignore")

    GEMINI_API_KEY: str = ""
    # Gemini 2.0 Flash was retired; use a current flash model.
    GEMINI_MODEL: str = "gemini-3.8-flash"
    SECRET_KEY: str = "insecure_dev_secret_change_me"
    DATABASE_URL: str = "sqlite:///./eduverse.db"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    # --- Expo / performance settings ---
    # If Gemini is slow/unreachable/out of quota, serve cached or built-in
    # offline content instead of an error (clearly labelled in the UI).
    OFFLINE_FALLBACK: bool = True
    # Force offline/cached mode only (no Gemini calls) - useful when the expo
    # venue has no reliable internet.
    DEMO_MODE: bool = False
    # Seconds before a Gemini call is abandoned and the fallback is used.
    AI_TIMEOUT_SECONDS: int = 25
    # Longer allowance for big outputs (quizzes, study plans); study material and chat stream instead.
    AI_LONG_TIMEOUT_SECONDS: int = 75
    # --- RAG ---
    USE_EMBEDDINGS: bool = True                 # semantic search via Gemini embeddings (falls back to keyword search)
    EMBED_MODEL: str = "gemini-embedding-001"
    RAG_TOP_K: int = 5                          # passages handed to the model
    RAG_MIN_COSINE: float = 0.60                # semantic relevance gate (raw cosine); tune with real notes
    RAG_MIN_COVERAGE: float = 0.5               # keyword gate: share of question terms found in the passage
    CACHE_FILE: str = str(Path(__file__).resolve().parent / "data" / "ai_cache.json")
    CACHE_TTL_SECONDS: int = 60 * 60 * 24 * 7


settings = Settings()
print(f"[config] .env path: {ENV_FILE} (exists={ENV_FILE.exists()}), Gemini key set={bool(settings.GEMINI_API_KEY) and settings.GEMINI_API_KEY != 'your_gemini_api_key_here'}")
