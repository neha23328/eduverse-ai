# EduVerse AI

A personalized learning assistant — expo-ready build (v1.1): streaming answers, response cache, offline fallback, gamification.

Built with:
- **Backend:** FastAPI + SQLite + SQLAlchemy + Google Gemini
- **Frontend:** React (Vite) + React Router + Recharts

## What's included

- Student registration/login (JWT auth)
- AI Mentor — academic Q&A chat with subject/level context and history, powered by Gemini
- AI-generated quizzes (multiple choice, auto-graded, with explanations) that feed into subject average scores
- Study material generator (notes, summaries, flashcards, revision sheets)
- AI-generated personalized study planner based on your actual progress
- Progress dashboard — subject-wise progress bars, weekly study-time chart, task list, study streak, weak-topic tracking
- Profile page

All progress is persisted in a real backend (SQLite file), not browser storage — refreshing, logging out, or opening on another device keeps your data, matching the "backend owns progress" principle from the original spec.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (with npm)
- A **free Gemini API key** — get one at https://aistudio.google.com/app/apikey

## Setup

### 1. Backend

```bash
cd backend
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt

# Copy the env file and add your Gemini API key
cp .env.example .env
```

Open `backend/.env` and set:
```
GEMINI_API_KEY=your_actual_key_here
SECRET_KEY=any_random_string_you_want
```

Run the backend:
```bash
uvicorn app.main:app --reload --port 8000
```

The API will be live at `http://localhost:8000`. You can browse interactive docs at `http://localhost:8000/docs`.

### 2. Frontend

Open a **new terminal**:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The app will be live at `http://localhost:5173`.

### 3. Use it

1. Open `http://localhost:5173`
2. Register a new account
3. Add a subject on the Dashboard
4. Try the AI Mentor, generate a quiz, generate study notes, or build a study plan

## Project structure

```
eduverse-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entrypoint
│   │   ├── config.py            # Settings (reads .env)
│   │   ├── database.py          # SQLAlchemy engine/session
│   │   ├── auth.py              # JWT + password hashing
│   │   ├── models/models.py     # DB tables
│   │   ├── schemas/schemas.py   # Pydantic request/response models
│   │   ├── services/ai_service.py  # All Gemini calls live here
│   │   └── routers/             # One file per feature area
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── src/
    │   ├── pages/                # One component per route
    │   ├── components/           # Shared UI (Sidebar, StatCard, etc)
    │   ├── context/AuthContext.jsx
    │   ├── services/api.js       # All backend calls live here
    │   └── App.jsx                # Routing
    ├── package.json
    └── .env.example
```

## Running in Cursor

1. Open the `eduverse-ai` folder in Cursor
2. Open two integrated terminals (one for backend, one for frontend) and follow the Setup steps above in each
3. Cursor's AI can read this whole structure — routers are small and single-purpose, so it's easy to ask Cursor to extend any one feature (e.g. "add a career roadmap router following the same pattern as planner_router.py")

## Extending it (Phase 2/3/4 ideas from the original spec)

The architecture is intentionally modular so these slot in cleanly:
- **RAG over uploaded PDFs/notes** — add a `documents` table + an embeddings service (e.g. `chromadb`), a new `/api/documents` router for upload, and have `ai_service.ask_mentor` retrieve relevant chunks before calling Gemini
- **Career roadmap / resume analyzer / mock interview** — new router + a couple of new `ai_service` functions, same pattern as `planner_router.py`
- **Charts/analytics expansion** — the `Activity` table already logs every study action; more chart types just need new aggregation queries in `progress_router.py`

## Notes

- Database is a single `eduverse.db` SQLite file created automatically on first run — delete it anytime to reset all data
- If quiz/chat/planner requests fail with a 503, it means `GEMINI_API_KEY` isn't set correctly in `backend/.env`
- CORS is pre-configured for `localhost:5173` (Vite's default port)


---

## Expo build (v1.1)

### What's new
- **Streaming AI Mentor** - words appear in ~0.5 s instead of waiting for the full answer.
- **Response cache** (persisted to `backend/app/data/ai_cache.json`) - repeated quizzes / notes / flashcards / plans return instantly.
- **Offline fallback** - if Gemini is slow, unreachable or out of quota, the app serves cached or built-in content, clearly labelled "Offline demo content" (no blank errors on stage).
- **Source badges** - every AI output shows `Live AI`, `Instant (cached)` or `Offline`, plus how long it took.
- **Achievements** - XP, levels, 8 badges and a leaderboard on the dashboard.
- **Flashcards** - flip cards instead of plain text.
- **Voice** - speak your question (mic) and have answers read aloud (Chrome/Edge).
- **Study plan -> tasks** - one click adds a day's plan to your task list.
- **Personalisation** - the student's learning style now shapes mentor answers and study material.
- **Speed internals** - cached model objects, token limits, SQLite WAL + indexes, one-query weekly chart, lazy-loaded pages, charts split into their own chunk.
- Markdown in answers is now HTML-escaped (the old renderer could inject markup).

### Expo-day checklist
1. Use **Python 3.11 or 3.12** (3.14 breaks `pydantic-core`).
2. `cd backend` -> `python seed_demo.py --reset` -> demo login **demo@eduverse.ai / demo1234** (4 classmates appear on the leaderboard).
3. The night before, with internet: `python prewarm.py` (edit the topics at the top of the file to match your demo). This caches the answers so they load instantly and work offline.
4. For the venue: run `npm run build` then `npm run preview` (served on port 4173) - faster than the dev server. Set `DEMO_MODE=true` in `.env` if the venue Wi-Fi is unreliable.
5. To let visitors open it on their phones: set `VITE_API_URL=http://<your-laptop-ip>:8000` in `frontend/.env` before building, and start the backend with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### Suggested 5-minute demo flow
Dashboard (level, badges, leaderboard) -> AI Mentor (tap a suggested question, show streaming + read aloud) -> Quiz (instant, then submit and watch XP/weak topics change) -> Study Material -> Flashcards (flip) -> Planner -> "Add to my tasks" -> back to Dashboard.


---

## RAG - how your notes are used (v1.4)

**What happens when you ask a question**

1. If you have notes, the mentor searches them first (mode **Auto**, the default). A follow-up like "explain that more simply" is rewritten into a standalone search query using the chat so far.
2. Two searches run together: keyword (BM25) and meaning-based (Gemini embeddings). Their rankings are fused (reciprocal-rank fusion), then an **absolute relevance gate** drops anything that is not genuinely about the question, and near-duplicate passages are removed.
3. If relevant passages are found they go into the prompt and the answer cites them as [1], [2]. Click a chip under the answer to read the exact passage; chips for passages the answer did not use are greyed out. Anything beyond the notes is labelled "Beyond your notes".
4. If nothing relevant is found, Auto mode says so and gives a normal answer. **Only my notes** refuses to guess; **Off** ignores the notes.

**Also built from your notes:** Quizzes and Study Material have a "Use my notes" option. Each question or point ends with the passage it came from. If your notes don't cover the topic you get a clear message instead of made-up content.

**My Notes page** shows a live check of whether meaning-based search is working (with the reason if not), a Re-index button for documents uploaded while it was off, and a "Check what the mentor finds" box that shows each passage with its match score. This is the best thing to demo on stage.

**Tuning** (backend/.env): `RAG_TOP_K` (default 5), `RAG_MIN_COSINE` (default 0.60) and `RAG_MIN_COVERAGE` (default 0.5). If real questions about your notes return nothing, lower `RAG_MIN_COSINE` a little (0.55); if unrelated questions still get sources, raise it (0.65).

`sample_notes/operating_systems_units_3-5.md` is a ready file for the demo. Try: "What are the four necessary conditions for deadlock?" (answered from the notes, with citations) and "How do I cook pasta?" (notes checked, nothing relevant).

## Longer, complete answers (v1.6)

Answers used to stop mid-sentence because the output limits were too small (700 tokens for the mentor, 900 for study material) and the prompts asked for short results. Now:
- The mentor gives full explanations (definition, step by step, example, common mistakes). Study notes are ~800-1000 words with a worked example and a self-check; flashcards are 12 per set; revision sheets include likely exam questions.
- Study material streams in as it is written. If Gemini reaches its length limit, the rest is requested automatically, and a mentor answer that is still cut off says so and tells you to reply "continue".
- Quizzes and study plans survive a cut-off too: the call is retried with double the budget, any complete questions are kept, and if too little is usable you get a clear "press Generate again" message instead of a parser error.
- Limits live in `backend/app/services/ai_service.py` (`TOK_MENTOR`, `TOK_CONTENT`, `TOK_QUIZ`, `TOK_PLAN`) and `AI_LONG_TIMEOUT_SECONDS` in `.env`. Old short answers in the cache are ignored automatically.

## Look and feel (v1.5)

A restrained, corporate palette: deep navy (top bar, hero), one steel blue for actions and progress, cool grey neutrals, and green/amber/red only for success, warning and error. Source Serif 4 headings with Source Sans 3 body text, installed through npm so they work offline. Layout follows common campus-portal conventions (landing page with three entry tiles, top navigation, hero with a suggested next step, a row of progress metrics) with no third-party branding.

To show your college name in the footer and on the login page, copy `frontend/.env.example` to `frontend/.env` and set `VITE_COLLEGE_NAME` (leave empty to hide it). Run `npm install` in `frontend` once after updating.

**Sign-up:** students pick their course (BCA, MCA, B.Tech CSE/IT, B.Sc IT, BBA, MBA, B.Com, M.Tech, M.Sc Data Science, or type their own). That unlocks suggestions for the right number of semesters, specialisations, career goals and starter subjects; ticked subjects are added to the dashboard automatically. The course and specialisation are also told to the AI mentor, e.g. "MCA (AI and Machine Learning)". To add or change courses, edit `frontend/src/data/courses.js`.
