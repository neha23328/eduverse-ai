"""Built-in offline content used ONLY when Gemini is unreachable / over quota.

The UI labels anything served from here as "offline demo content" so it is
never passed off as live AI output.
"""
from typing import List, Optional

QUIZ_BANK = {
    "data structures": [
        {"question": "Which data structure uses LIFO (Last In, First Out) ordering?",
         "options": ["Queue", "Stack", "Linked list", "Heap"], "correct_index": 1,
         "explanation": "A stack removes the most recently added element first."},
        {"question": "What is the average time complexity of searching in a balanced binary search tree?",
         "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"], "correct_index": 2,
         "explanation": "Each comparison halves the remaining search space in a balanced BST."},
        {"question": "Which structure is best suited for implementing BFS traversal of a graph?",
         "options": ["Stack", "Queue", "Priority queue", "Hash table"], "correct_index": 1,
         "explanation": "BFS visits nodes level by level, which needs FIFO order - a queue."},
        {"question": "Which of these gives O(1) average-case lookup by key?",
         "options": ["Hash table", "Sorted array", "Linked list", "Binary heap"], "correct_index": 0,
         "explanation": "A hash table maps keys to buckets, giving constant average lookup."},
        {"question": "In a min-heap, where is the smallest element?",
         "options": ["At a leaf", "At the root", "At the last index", "In the middle"], "correct_index": 1,
         "explanation": "The heap property guarantees the minimum sits at the root."},
    ],
    "machine learning": [
        {"question": "What problem does regularization mainly address?",
         "options": ["Underfitting", "Overfitting", "Missing data", "Slow training"], "correct_index": 1,
         "explanation": "Regularization penalizes model complexity to reduce overfitting."},
        {"question": "Which algorithm is an example of unsupervised learning?",
         "options": ["Linear regression", "Logistic regression", "K-means clustering", "Decision tree classifier"],
         "correct_index": 2, "explanation": "K-means groups unlabeled data into clusters."},
        {"question": "What does a confusion matrix summarize?",
         "options": ["Training time", "Classification predictions vs. true labels", "Feature importance", "Learning rate"],
         "correct_index": 1, "explanation": "It tabulates true/false positives and negatives."},
        {"question": "Which split is used to tune hyperparameters without touching the final test set?",
         "options": ["Training set", "Validation set", "Test set", "Holdout of the test set"], "correct_index": 1,
         "explanation": "The validation set guides tuning; the test set stays untouched until the end."},
        {"question": "Gradient descent updates parameters in which direction?",
         "options": ["Along the gradient", "Opposite the gradient", "Perpendicular to the gradient", "Random"],
         "correct_index": 1, "explanation": "It moves opposite the gradient to reduce the loss."},
    ],
}


def quiz_for(subject: str, topic: str, n: int) -> Optional[List[dict]]:
    text = f"{subject} {topic}".lower()
    aliases = {
        "data structures": ["data structure", "dsa", "stack", "queue", "tree", "graph", "heap", "hash"],
        "machine learning": ["machine learning", "ml", "regression", "classification", "neural", "overfit"],
    }
    for key, words in aliases.items():
        if any(w in text for w in words):
            return QUIZ_BANK[key][:max(1, min(n, len(QUIZ_BANK[key])))]
    return None


def study_material(subject: str, topic: str, material_type: str) -> str:
    if material_type == "flashcards":
        return (
            f"Q: What is the core idea of {topic}?\nA: (Offline mode) Connect to the internet to generate real flashcards.\n\n"
            f"Q: Why does {topic} matter in {subject}?\nA: (Offline mode) Reconnect to get AI-generated answers.\n"
        )
    return (
        f"# {topic} ({subject})\n\n"
        "> **Offline demo content.** The AI service is not reachable right now, so this is a placeholder. "
        "Reconnect to generate full, personalized material.\n\n"
        "## What to cover\n- Definition and motivation\n- Key terms and formulas\n- Worked example\n- Common mistakes\n"
    )


def mentor_reply(message: str) -> str:
    return (
        "**Offline mode:** I can't reach the AI service right now, so I can't answer this live.\n\n"
        "Try one of the pre-loaded demo questions, or check the internet connection / Gemini API key."
    )


def study_plan(subject_progress: List[dict], goal: str, hours_per_day: float, days: int) -> dict:
    """Deterministic planner: rank subjects by weakness and rotate them."""
    ranked = sorted(
        subject_progress,
        key=lambda s: (s.get("percentage", 0) + s.get("averageScore", 0)) / 2,
    ) or [{"subject": "General revision"}]
    plan = []
    for d in range(1, days + 1):
        focus = [ranked[(d - 1) % len(ranked)]["subject"]]
        if len(ranked) > 1:
            focus.append(ranked[d % len(ranked)]["subject"])
        plan.append({
            "day": d,
            "focus_subjects": focus,
            "tasks": [
                f"Revise core concepts of {focus[0]} (45 min)",
                f"Solve practice problems on {focus[0]}",
                "Take a short quiz and review wrong answers",
            ],
            "estimated_hours": hours_per_day,
        })
    return {"plan": plan, "notes": "Offline plan: weakest subjects are scheduled most often."}
