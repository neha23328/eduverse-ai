import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from functools import lru_cache
from typing import Iterator, List, Optional, Tuple

import google.generativeai as genai

from app.config import settings
from app.services import cache, offline_data

log = logging.getLogger("eduverse.ai")
_configured = False
_cfg_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=8)

# Output budgets. Too small = answers that stop mid-sentence (long answers hit the cap).
TOK_MENTOR, TOK_CONTENT, TOK_QUIZ, TOK_PLAN = 2048, 4096, 4096, 4096

# source labels returned to the UI
LIVE, CACHED, OFFLINE = "live", "cache", "offline"


def _ensure_configured():
    global _configured
    with _cfg_lock:
        if not _configured:
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
                raise RuntimeError(
                    "GEMINI_API_KEY is not set. Add it to backend/.env (copy from .env.example)."
                )
            genai.configure(api_key=settings.GEMINI_API_KEY)
            _configured = True


@lru_cache(maxsize=32)
def _model(json_mode: bool, max_tokens: int, temperature: float, system: str = ""):
    """Model objects are cached - building one per request wastes time."""
    _ensure_configured()
    cfg = {"max_output_tokens": max_tokens, "temperature": temperature}
    if json_mode:
        cfg["response_mime_type"] = "application/json"
    kwargs = {"model_name": settings.GEMINI_MODEL, "generation_config": cfg}
    if system:
        kwargs["system_instruction"] = system
    return genai.GenerativeModel(**kwargs)


def _hit_limit(chunk) -> bool:
    """True when Gemini stopped because it ran out of output tokens (the answer is cut off)."""
    try:
        fr = chunk.candidates[0].finish_reason
        return getattr(fr, "name", str(fr)) == "MAX_TOKENS" or fr == 2
    except Exception:
        return False


def _generate(model, prompt) -> str:
    """Single Gemini call with a hard timeout so the UI never hangs. Long outputs get a longer allowance."""
    _ensure_configured()
    fut = _pool.submit(lambda: model.generate_content(prompt).text.strip())
    try:
        return fut.result(timeout=max(settings.AI_TIMEOUT_SECONDS, settings.AI_LONG_TIMEOUT_SECONDS))
    except FutureTimeout:
        raise TimeoutError("AI service timed out")


def _extract_json(text: str):
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", cleaned, flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _generate_json(prompt, max_tokens, temperature):
    """JSON call that survives running out of tokens: if Gemini is cut off, retry once with double the budget.
    Returns (text, still_truncated)."""
    _ensure_configured()
    text, truncated = "", False
    for budget in (max_tokens, max_tokens * 2):
        def call(b=budget):
            r = _model(True, b, temperature).generate_content(prompt)
            return r.text.strip(), _hit_limit(r)
        fut = _pool.submit(call)
        try:
            text, truncated = fut.result(timeout=max(settings.AI_TIMEOUT_SECONDS, settings.AI_LONG_TIMEOUT_SECONDS))
        except FutureTimeout:
            raise TimeoutError("AI service timed out")
        if not truncated:
            break
        log.warning("Gemini JSON answer hit the %s-token limit; retrying with a bigger budget", budget)
    return text, truncated


def _salvage_items(text: str) -> list:
    """Complete {...} objects from a JSON array that was cut off mid-way (keeps what is usable)."""
    cleaned = re.sub(r"^```json\s*|^```\s*|```$", "", text.strip(), flags=re.MULTILINE)
    start = cleaned.find("[")
    if start < 0:
        return []
    dec, i, items = json.JSONDecoder(), start + 1, []
    while True:
        while i < len(cleaned) and cleaned[i] in " \n\r\t,":
            i += 1
        if i >= len(cleaned) or cleaned[i] != "{":
            break
        try:
            obj, i = dec.raw_decode(cleaned, i)
        except json.JSONDecodeError:
            break
        items.append(obj)
    return items


def _clean_question(q):
    """A usable multiple-choice question, or None."""
    try:
        opts = [str(o) for o in q["options"]]
        idx = int(q["correct_index"])
        if len(opts) != 4 or not 0 <= idx <= 3 or not str(q["question"]).strip():
            return None
        return {"question": str(q["question"]).strip(), "options": opts, "correct_index": idx,
                "explanation": str(q.get("explanation", "")).strip()}
    except Exception:
        return None


# ---------------------------------------------------------------- Mentor

def _mentor_system(subject, level, student_context, context="", strict=False):
    ctx = []
    if student_context:
        if student_context.get("branch"):
            ctx.append(f"Student's branch: {student_context['branch']}")
        if student_context.get("semester"):
            ctx.append(f"Semester: {student_context['semester']}")
        if student_context.get("career_goal"):
            ctx.append(f"Career goal: {student_context['career_goal']}")
        if student_context.get("learning_style"):
            ctx.append(f"Preferred learning style: {student_context['learning_style']} - adapt examples to it.")
    base = f"""You are EduVerse AI, a personalized academic learning assistant.
Explanation level: {level} (beginner = simple language and analogies, intermediate = standard depth, advanced = rigorous).
{f"Subject focus: {subject}" if subject else ""}
{chr(10).join(ctx)}

Guidelines:
- Be clear and well structured; use Markdown (short headings, bullets, code blocks).
- Show steps for step-by-step problems.
- Answer fully. For a concept question give: a clear definition, how it works step by step, a concrete example (code in a fenced block when it is a programming topic) and the common mistakes. That is typically 300-500 words.
- Keep simple factual questions short. Go deeper whenever the student asks for detail.
- Redirect unrelated questions back to studying."""
    if not context:
        return base
    if strict:
        return base + f"""

The student asked to answer ONLY FROM THEIR OWN NOTES. Use only the numbered excerpts below.
- Cite every claim you take from an excerpt inline like [1] or [2]. Cite only excerpts you really used.
- If the excerpts do not contain the answer, say plainly that the notes don't cover it, and stop. Do not guess.
- Never invent details that are not in the excerpts.

NOTES EXCERPTS:
{context}"""
    return base + f"""

The student has uploaded their own notes. These numbered excerpts were retrieved as relevant to the question.
- Treat the excerpts as your primary source. Cite what you take from them inline like [1] or [2]; cite only excerpts you really used.
- If the excerpts only partly answer the question, answer the covered part from them, then add anything else under a line that starts "Beyond your notes:" so the student can tell the two apart.
- If an excerpt contradicts common textbook knowledge, say so instead of silently picking one.

NOTES EXCERPTS:
{context}"""


_REFERENTIAL = {"it", "its", "this", "that", "they", "them", "those", "these", "he", "she", "his", "her", "there",
                "more", "again", "another", "simpler", "shorter", "elaborate", "continue", "example", "examples",
                "former", "latter", "same", "above", "previous"}


def _is_followup(message: str) -> bool:
    """A follow-up leans on earlier turns: a pronoun/reference word, or just 1-2 words ("why?", "and then?")."""
    words = re.findall(r"[A-Za-z']+", message.lower())
    return len(words) <= 2 or bool(set(words) & _REFERENTIAL)


def condense_query(message: str, history: Optional[List[dict]]) -> str:
    """Turns a follow-up ("explain that more simply") into a standalone search query.

    Retrieval only sees one string, so without this a follow-up searches for
    nothing useful. Cheap path first: a long, self-contained question is used as is.
    """
    history = history or []
    if not history or not _is_followup(message):
        return message
    last_user = next((h["content"] for h in reversed(history) if h["role"] == "user"), "")
    heuristic = f"{last_user[:200]} {message}".strip()
    if settings.DEMO_MODE:
        return heuristic
    try:
        convo = "\n".join(f"{h['role']}: {h['content'][:300]}" for h in history[-4:])
        prompt = ("Rewrite the student's LAST message as one standalone search query for their study notes, "
                  "using the conversation for missing context. Output only the query, no quotes.\n\n"
                  f"Conversation:\n{convo}\n\nLAST message: {message}")
        fut = _pool.submit(lambda: _model(False, 60, 0.0).generate_content(prompt).text.strip())
        out = fut.result(timeout=6).splitlines()[0].strip(' "')
        return out or heuristic
    except Exception as e:   # slow/offline: fall back to a rule-based rewrite
        log.info("query rewrite fell back to heuristic: %s", type(e).__name__)
        return heuristic


def stream_mentor(message, subject="", level="intermediate", history=None,
                  student_context=None, context="", fallback_text="", strict=False) -> Iterator[Tuple[str, str]]:
    """Yields ("chunk", text) pieces and finally ("source", live|cache|offline).

    Streaming means the first words appear in ~0.5s instead of waiting for the
    whole answer.
    """
    key = cache.make_key("mentor-v2", message, subject, level)
    use_cache = not history and not context  # only STORE context-free, first-turn answers
    hit = None if context else cache.get(key)  # notes-based answers depend on the notes: never cached
    if hit:
        for i in range(0, len(hit), 40):
            yield ("chunk", hit[i:i + 40])
        yield ("source", CACHED)
        return

    if settings.DEMO_MODE:
        yield ("chunk", fallback_text or offline_data.mentor_reply(message))
        yield ("source", OFFLINE)
        return

    try:
        _ensure_configured()
        model = _model(False, TOK_MENTOR, 0.5, _mentor_system(subject, level, student_context, context, strict))
        contents = []
        for h in (history or [])[-6:]:
            contents.append({"role": "user" if h["role"] == "user" else "model", "parts": [h["content"]]})
        contents.append({"role": "user", "parts": [message]})

        full, limited = [], False
        for chunk in model.generate_content(contents, stream=True):
            limited = limited or _hit_limit(chunk)
            try:
                piece = chunk.text
            except ValueError:  # blocked / empty chunk
                continue
            if piece:
                full.append(piece)
                yield ("chunk", piece)
        if limited:   # never end silently mid-sentence
            note = "\n\n*This answer was long and got cut off. Reply “continue” to get the rest.*"
            full.append(note)
            yield ("chunk", note)
        text = "".join(full).strip()
        if not text:
            raise RuntimeError("Empty AI response")
        if use_cache:
            cache.set(key, text)
        yield ("source", LIVE)
    except Exception as e:
        log.error("Gemini mentor call failed: %s: %s", type(e).__name__, e)
        if not settings.OFFLINE_FALLBACK:
            raise
        yield ("chunk", (fallback_text or offline_data.mentor_reply(message)) + f"\n\n`Reason: {type(e).__name__}: {str(e)[:200]}`")
        yield ("source", OFFLINE)


def ask_mentor(message, subject="", level="intermediate", history=None, student_context=None) -> str:
    """Non-streaming helper (kept for API compatibility)."""
    return "".join(p for kind, p in stream_mentor(message, subject, level, history, student_context) if kind == "chunk")


# ---------------------------------------------------------------- Quiz

def generate_quiz(subject: str, topic: str, difficulty: str, num_questions: int = 5, context: str = "") -> Tuple[List[dict], str]:
    key = cache.make_key("quiz", subject, topic, difficulty, num_questions)
    hit = None if context else cache.get(key)
    if hit:
        return hit, CACHED

    prompt = f"""Generate {num_questions} multiple-choice questions.
Subject: {subject}
Topic: {topic}
Difficulty: {difficulty}

Return ONLY a JSON array. Each item: {{"question": str, "options": [4 strings], "correct_index": 0-3, "explanation": "one short sentence"}}.
Test real understanding; vary the style. Keep every string on ONE line (no line breaks inside strings), write code inline,
and escape any double quotes."""
    if context:
        prompt += f"""

Base EVERY question strictly on the student's own notes below. Do not use facts that are not in the excerpts.
End each explanation with the excerpt it comes from, like [2].

NOTES EXCERPTS:
{context}"""
    try:
        if settings.DEMO_MODE:
            raise RuntimeError("demo mode")
        text, truncated = _generate_json(prompt, TOK_QUIZ, 0.4)
        try:
            data = _extract_json(text)
            if isinstance(data, dict) and "questions" in data:
                data = data["questions"]
        except Exception:                       # cut off or malformed: keep every complete question
            data = _salvage_items(text)
        questions = [q for q in (_clean_question(x) for x in (data or [])) if q][:num_questions]
        if len(questions) < max(1, -(-num_questions * 6 // 10)):       # fewer than ~60% usable
            raise ValueError("The AI returned an incomplete quiz. Please press Generate again.")
        if len(questions) == num_questions and not context:
            cache.set(key, questions)
        return questions, LIVE
    except Exception as e:
        log.error("Gemini quiz call failed: %s: %s", type(e).__name__, e)
        if settings.OFFLINE_FALLBACK and not context:   # the built-in bank is not from the student's notes
            bank = offline_data.quiz_for(subject, topic, num_questions)
            if bank:
                return bank, OFFLINE
        raise


# ---------------------------------------------------------------- Study material

_LEVEL_HINT = {
    "beginner": "Use plain words and everyday analogies; define every term before using it.",
    "intermediate": "Assume the basics; explain how and why, with realistic examples.",
    "advanced": "Be rigorous: internals, edge cases, complexity or trade-offs, and exam-level depth.",
}

_MATERIAL_SPEC = {
    "notes": """Write detailed, exam-ready study notes (about 800-1000 words) with exactly this structure:
## Overview
What it is and why it matters, in 2-3 sentences.
## Key concepts
Each concept gets its own ### heading, a clear explanation, the formula or syntax where relevant, and a short example. Use fenced code blocks for any code.
## Worked example
One complete example solved step by step.
## Common mistakes
4-5 bullets.
## Quick check
5 self-test questions, each followed by a one-line answer.""",
    "summary": """Write a clear summary (about 250-300 words): a short overview paragraph, then 6-8 bullets of the most important points, then one line starting "Remember:" with the single idea to keep.""",
    "flashcards": """Write exactly 12 flashcards covering definitions, why/how questions and small applications. Format every card as two lines, 'Q: ...' then 'A: ...' (answers 1-3 sentences), with a blank line between cards. No other text.""",
    "revision": """Write a revision sheet (about 500-600 words): key definitions, formulas or syntax (in code blocks where suitable), the important differences and comparisons as bullets, 8-10 must-remember points, and 5 typical exam questions with one-line answers.""",
}


def _content_prompt(subject, topic, material_type, level, learning_style, context):
    style = f" Adapt examples to a {learning_style} learner." if learning_style else ""
    prompt = (f'{_MATERIAL_SPEC.get(material_type, _MATERIAL_SPEC["notes"])}\n\n'
              f'Topic: "{topic}" in "{subject}". Level: {level}. {_LEVEL_HINT.get(level, "")}{style}\n'
              "Be accurate and complete; finish every section. Output clean Markdown only.")
    if context:
        prompt += f"""

Use ONLY the student's own notes below as the source material. Cite the excerpt you used like [1] after each point.
If the notes barely cover the topic, say so at the top instead of padding with outside facts.

NOTES EXCERPTS:
{context}"""
    return prompt


def stream_study_material(subject: str, topic: str, material_type: str, level: str = "intermediate",
                          learning_style: str = "", context: str = "") -> Iterator[Tuple[str, str]]:
    """Yields ("chunk", text) pieces, then ("source", live|cache|offline). Long notes appear as they are written,
    and if Gemini hits its length limit the rest is requested automatically (never ends mid-sentence)."""
    key = cache.make_key("content-v2", subject, topic, material_type, level, learning_style)
    hit = None if context else cache.get(key)
    if hit:
        for i in range(0, len(hit), 60):
            yield ("chunk", hit[i:i + 60])
        yield ("source", CACHED)
        return
    try:
        if settings.DEMO_MODE:
            raise RuntimeError("demo mode")
        _ensure_configured()
        model = _model(False, TOK_CONTENT, 0.4)
        base = _content_prompt(subject, topic, material_type, level, learning_style, context)
        prompt, full = base, ""
        for _round in range(3):                       # original + up to 2 continuations
            limited = False
            for chunk in model.generate_content(prompt, stream=True):
                limited = limited or _hit_limit(chunk)
                try:
                    piece = chunk.text
                except ValueError:
                    continue
                if piece:
                    full += piece
                    yield ("chunk", piece)
            if not limited:
                break
            prompt = (base + "\n\nYour previous reply was cut off by a length limit. This is how it ended:\n---\n"
                      + full[-1200:] + "\n---\nContinue from exactly where it stopped. Do not repeat anything and do not "
                      "add a new introduction.")
        if not full.strip():
            raise RuntimeError("Empty AI response")
        if not context:
            cache.set(key, full.strip())
        yield ("source", LIVE)
    except Exception as e:
        log.error("Gemini content call failed: %s: %s", type(e).__name__, e)
        if settings.OFFLINE_FALLBACK and not context:
            yield ("chunk", offline_data.study_material(subject, topic, material_type))
            yield ("source", OFFLINE)
            return
        raise


def generate_study_material(subject: str, topic: str, material_type: str, level: str = "intermediate",
                            learning_style: str = "", context: str = "") -> Tuple[str, str]:
    """Non-streaming wrapper (kept for API compatibility)."""
    parts, source = [], LIVE
    for kind, val in stream_study_material(subject, topic, material_type, level, learning_style, context):
        if kind == "chunk":
            parts.append(val)
        else:
            source = val
    return "".join(parts).strip(), source


# ---------------------------------------------------------------- Planner

def generate_study_plan(subject_progress: List[dict], goal: str, hours_per_day: float, days: int) -> Tuple[dict, str]:
    sig = json.dumps(subject_progress, sort_keys=True)
    key = cache.make_key("plan", sig, goal, hours_per_day, days)
    hit = cache.get(key)
    if hit:
        return hit, CACHED

    summary = "\n".join(
        f"- {s['subject']}: {s['percentage']:.0f}% complete, avg score {s['averageScore']:.0f}%"
        for s in subject_progress
    ) or "No subjects tracked yet."
    prompt = f"""Create a {days}-day study plan.
Progress:
{summary}
Goal: {goal or "General academic improvement"}
Time: {hours_per_day} hours/day

Return ONLY JSON: {{"plan": [{{"day": 1, "focus_subjects": [str], "tasks": [str, str, str], "estimated_hours": number}}], "notes": "one-sentence strategy"}}
Prioritize weaker subjects. Max 3 short tasks per day."""
    try:
        if settings.DEMO_MODE:
            raise RuntimeError("demo mode")
        text, _trunc = _generate_json(prompt, TOK_PLAN, 0.4)
        try:
            data = _extract_json(text)
        except Exception:
            raise ValueError("The AI returned an incomplete study plan. Please press Generate again.")
        cache.set(key, data)
        return data, LIVE
    except Exception as e:
        log.error("Gemini plan call failed: %s: %s", type(e).__name__, e)
        if settings.OFFLINE_FALLBACK:
            return offline_data.study_plan(subject_progress, goal, hours_per_day, days), OFFLINE
        raise
