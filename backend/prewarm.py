"""Pre-generate the expo demo content so it is served INSTANTLY (and offline).

Run once with internet + a valid GEMINI_API_KEY, the night before the expo:

    python prewarm.py

Edit DEMO_* below to match what you plan to show on stage.
"""
from app.services import ai_service, cache

DEMO_MENTOR = [
    ("Explain how a hash table handles collisions", "Data Structures", "intermediate"),
    ("What is overfitting and how do I prevent it?", "Programming", "beginner"),
    ("Explain deadlock and the four necessary conditions", "Other", "intermediate"),
]
DEMO_QUIZZES = [
    ("Data Structures", "Binary Trees", "intermediate", 5),
    ("Machine Learning", "Overfitting", "intermediate", 5),
]
DEMO_CONTENT = [
    ("Operating Systems", "Deadlocks", t, "intermediate")
    for t in ("notes", "summary", "flashcards", "revision")
] + [("Data Structures", "Binary Trees", "flashcards", "intermediate")]


def main():
    ok = fail = 0

    def step(label, fn):
        nonlocal ok, fail
        try:
            fn()
            ok += 1
            print("  ok  ", label)
        except Exception as e:
            fail += 1
            print("  FAIL", label, "-", e)

    for q, subj, level in DEMO_MENTOR:
        def run(q=q, subj=subj, level=level):
            for kind, _ in ai_service.stream_mentor(q, subj, level, None, None):
                pass
            # stream_mentor caches a live answer; make sure it really was live
            assert cache.get(cache.make_key("mentor", q, subj, level)), "no live answer cached"
        step(f"mentor: {q[:45]}", run)

    for subj, topic, diff, n in DEMO_QUIZZES:
        step(f"quiz: {subj}/{topic}", lambda a=(subj, topic, diff, n): ai_service.generate_quiz(*a))

    for subj, topic, mtype, level in DEMO_CONTENT:
        step(f"{mtype}: {topic}", lambda a=(subj, topic, mtype, level): ai_service.generate_study_material(*a))

    print(f"\nDone: {ok} cached, {fail} failed. Cache file: app/data/ai_cache.json")


if __name__ == "__main__":
    main()
