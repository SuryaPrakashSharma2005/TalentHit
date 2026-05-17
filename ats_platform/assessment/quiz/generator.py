from typing import List, Dict
from bson import ObjectId
import random


async def generate_mcqs(
    db,
    skills: List[str],
    questions_per_skill: int = 2
) -> List[Dict]:
    """
    Generate MCQs from `assessment_questions` collection for the given skills.
    Returns a flat list of questions sampled per skill.
    """

    if not skills:
        return []

    # fetch candidate questions matching any of the skills
    pool = await db["assessment_questions"].find(
        {"skills": {"$in": skills}, "is_active": True}
    ).to_list(length=1000)

    # group by skill
    by_skill = {s: [] for s in skills}
    for q in pool:
        for s in q.get("skills", []):
            if s in by_skill:
                by_skill[s].append(q)

    mcqs = []
    for skill in skills:
        items = by_skill.get(skill, [])
        if not items:
            continue

        selected = random.sample(items, min(len(items), questions_per_skill))
        for q in selected:
            options = [{"id": o.get("id"), "text": o.get("text")} for o in q.get("options", [])]
            mcqs.append({
                "id": str(q.get("_id")),
                "skill": skill,
                "question": q.get("question_text"),
                "options": options
            })

    return mcqs
