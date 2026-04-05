from typing import Dict, List
from .questions import MCQ_BANK


def evaluate_mcqs(
    answers: Dict[str, int]
) -> Dict[str, float]:
    """
    answers = {
      "py_1": 0,
      "sql_1": 2
    }
    """

    total = 0
    correct = 0

    for skill_questions in MCQ_BANK.values():
        for q in skill_questions:
            qid = q["id"]
            if qid in answers:
                total += 1
                if answers[qid] == q["correct_index"]:
                    correct += 1

    score = (correct / total) * 100 if total else 0

    return {
        "total_questions": total,
        "correct_answers": correct,
        "mcq_score": round(score, 2)
    }
