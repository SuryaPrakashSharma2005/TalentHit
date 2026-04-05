from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from pymongo.errors import DuplicateKeyError


# ======================================================
# GET OR CREATE CANDIDATE (RACE-SAFE)
# ======================================================

async def get_or_create_candidate(db, name: str, email: str) -> Dict[str, Any]:
    """
    Safely find or create candidate by email.
    Handles race conditions via unique index.
    """

    if not email:
        raise ValueError("Email is required")

    email = email.strip().lower()

    existing = await db["candidates"].find_one({"email": email})
    if existing:
        return existing

    candidate_data = {
        "name": name or email.split("@")[0],
        "email": email,
        "skills": [],
        "experience_years": 0,
        "education": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    try:
        result = await db["candidates"].insert_one(candidate_data)
        candidate_data["_id"] = result.inserted_id
        return candidate_data

    except DuplicateKeyError:
        # In case two requests race at same time
        return await db["candidates"].find_one({"email": email})


# ======================================================
# CREATE EVALUATION (UPSERT SAFE)
# ======================================================

async def create_evaluation(
    db,
    job_id: str,
    candidate_id: ObjectId,
    resume_score: float,
    mcq_score: float,
    final_score: float,
    decision: Optional[str],
    resume_breakdown: Dict[str, Any],
    mcq_breakdown: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create or update evaluation per (job_id, candidate_id).
    Prevents duplicate evaluations.
    """

    if not job_id:
        raise ValueError("job_id required")

    try:
        job_object_id = ObjectId(job_id)
    except:
        raise ValueError("Invalid job_id")

    now = datetime.utcnow()

    evaluation_data = {
        "job_id": job_object_id,
        "candidate_id": candidate_id,
        "resume_score": float(resume_score),
        "mcq_score": float(mcq_score),
        "final_score": float(final_score),
        "decision": decision,
        "resume_breakdown": resume_breakdown,
        "mcq_breakdown": mcq_breakdown,
        "updated_at": now
    }

    # Upsert ensures single evaluation per job per candidate
    result = await db["evaluations"].find_one_and_update(
        {
            "job_id": job_object_id,
            "candidate_id": candidate_id
        },
        {
            "$set": evaluation_data,
            "$setOnInsert": {"created_at": now}
        },
        upsert=True,
        return_document=True
    )

    return result