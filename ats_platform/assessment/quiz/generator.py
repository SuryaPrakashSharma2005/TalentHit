from typing import List, Dict
from .questions import MCQ_BANK
import random


def generate_mcqs(
    skills: List[str],
    questions_per_skill: int = 2
) -> List[Dict]:
    """
    Generate MCQs based on detected skills.
    """

    mcqs = []

    for skill in skills:
        if skill not in MCQ_BANK:
            continue

        pool = MCQ_BANK[skill]
        selected = random.sample(
            pool,
            min(len(pool), questions_per_skill)
        )

        for q in selected:
            mcqs.append({
                "id": q["id"],
                "skill": skill,
                "question": q["question"],
                "options": q["options"]
            })

    return mcqs
