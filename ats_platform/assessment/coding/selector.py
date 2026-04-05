from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import random


# ======================================================
# CONFIG
# ======================================================

DEFAULT_DISTRIBUTION = {
    "easy": 1,
    "medium": 1,
    "hard": 0
}


# ======================================================
# MAIN SELECTOR
# ======================================================

async def select_coding_questions(
    db: AsyncIOMotorDatabase,
    count: int = 2,
    exclude_ids: Optional[List[str]] = None,
    preferred_domains: Optional[List[str]] = None
) -> List[Dict]:
    """
    Production-grade selector:
    - Difficulty balancing
    - Avoid repeats
    - Domain-aware selection
    """

    exclude_ids = exclude_ids or []
    exclude_object_ids = [
        ObjectId(qid) for qid in exclude_ids if ObjectId.is_valid(qid)
    ]

    questions: List[Dict] = []

    # =====================================
    # BUILD MATCH FILTER
    # =====================================

    base_match = {}

    if exclude_object_ids:
        base_match["_id"] = {"$nin": exclude_object_ids}

    if preferred_domains:
        base_match["domain"] = {"$in": preferred_domains}

    # =====================================
    # SELECT BY DIFFICULTY
    # =====================================

    for difficulty, limit in DEFAULT_DISTRIBUTION.items():

        if limit == 0:
            continue

        pipeline = [
            {"$match": {**base_match, "difficulty": difficulty}},
            {"$sample": {"size": limit}}
        ]

        cursor = db["coding_questions"].aggregate(pipeline)

        async for q in cursor:
            questions.append(_format_question(q))

    # =====================================
    # FALLBACK IF NOT ENOUGH QUESTIONS
    # =====================================

    if len(questions) < count:
        remaining = count - len(questions)

        pipeline = [
            {"$match": base_match},
            {"$sample": {"size": remaining}}
        ]

        cursor = db["coding_questions"].aggregate(pipeline)

        async for q in cursor:
            questions.append(_format_question(q))

    if len(questions) < count:
        raise ValueError("Not enough coding questions in database")

    return questions[:count]


# ======================================================
# FORMATTER
# ======================================================

def _format_question(q: Dict) -> Dict:
    return {
        "_id": str(q["_id"]),
        "title": q.get("title", ""),
        "description": q.get("description", ""),
        "difficulty": q.get("difficulty", "medium"),
        "domain": q.get("domain", ""),
        "test_cases": q.get("test_cases", []),
        "hidden_test_cases": q.get("hidden_test_cases", [])
    }