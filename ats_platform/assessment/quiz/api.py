from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from pydantic import BaseModel, field_validator
from bson import ObjectId
from datetime import datetime, timedelta

from ...database.mongodb import get_db
from ...core.dependencies import get_current_user

router = APIRouter(prefix="/quiz", tags=["MCQ"])


# ======================================================
# SCHEMAS
# ======================================================

class QuizGenerateRequest(BaseModel):
    application_id: str


class QuizSubmitRequest(BaseModel):
    answers: Dict[str, int]

    @field_validator("answers")
    def validate_answers(cls, v):
        if not isinstance(v, dict):
            raise ValueError("answers must be a dictionary")

        for key, val in v.items():
            if not isinstance(val, int):
                raise ValueError("Each answer must be an integer index")

        return v


# ======================================================
# GENERATE QUIZ (SNAPSHOT BASED)
# ======================================================

@router.post("/generate")
async def generate_quiz(
    payload: QuizGenerateRequest,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        app_obj = ObjectId(payload.application_id)
    except:
        raise HTTPException(400, "Invalid application_id")

    application = await db["applications"].find_one({
        "_id": app_obj,
        "candidate_id": ObjectId(current_user["id"])
    })

    if not application:
        raise HTTPException(404, "Application not found")

    if application.get("mcq_attempted"):
        raise HTTPException(400, "MCQ already submitted")

    if application.get("mcq_started_at"):
        raise HTTPException(400, "MCQ already started")

    # -------------------------------------
    # GET SKILLS FROM JOB
    # -------------------------------------

    job = await db["jobs"].find_one({"_id": application["job_id"]})

    if not job:
        raise HTTPException(404, "Job not found")

    required_skills = job.get("required_skills", [])

    # -------------------------------------
    # FETCH QUESTIONS FROM DB
    # -------------------------------------

    pool = await db["mcq_bank"].find({
        "skill": {"$in": required_skills}
    }).to_list(length=100)

    if len(pool) < 10:
        raise HTTPException(400, "Not enough questions")

    import random
    selected = random.sample(pool, 10)

    snapshot = []

    for q in selected:
        options = q["options"][:]
        random.shuffle(options)

        correct_index = options.index(q["options"][q["correct"]])

        snapshot.append({
            "id": str(q["_id"]),
            "question": q["question"],
            "options": options,
            "correct": correct_index
        })

    # -------------------------------------
    # SAVE SNAPSHOT
    # -------------------------------------

    await db["applications"].update_one(
        {"_id": app_obj},
        {
            "$set": {
                "mcq_snapshot": snapshot,
                "mcq_started_at": datetime.utcnow(),
                "mcq_duration_minutes": 15,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "questions": [
            {
                "id": q["id"],
                "question": q["question"],
                "options": q["options"]
            }
            for q in snapshot
        ]
    }


# ======================================================
# SUBMIT QUIZ
# ======================================================

@router.post("/submit/{application_id}")
async def submit_quiz(
    application_id: str,
    payload: QuizSubmitRequest,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        app_obj = ObjectId(application_id)
    except:
        raise HTTPException(400, "Invalid ID")

    application = await db["applications"].find_one({
        "_id": app_obj,
        "candidate_id": ObjectId(current_user["id"])
    })

    if not application:
        raise HTTPException(404, "Application not found")

    if application.get("mcq_attempted"):
        raise HTTPException(400, "Already submitted")

    if not application.get("mcq_snapshot"):
        raise HTTPException(400, "Test not started")

    # =====================================
    # TIME CHECK
    # =====================================

    started_at = application.get("mcq_started_at")
    duration = application.get("mcq_duration_minutes", 15)

    if not started_at:
        raise HTTPException(400, "Invalid test state")

    expiry = started_at + timedelta(minutes=duration)

    if datetime.utcnow() > expiry:
        raise HTTPException(400, "Time expired")

    snapshot = application["mcq_snapshot"]
    answers = payload.answers

    # =====================================
    # VALIDATE QUESTION IDS
    # =====================================

    valid_ids = {q["id"] for q in snapshot}

    for qid in answers.keys():
        if qid not in valid_ids:
            raise HTTPException(400, "Invalid question ID")

    # =====================================
    # SCORING
    # =====================================

    correct = 0

    for q in snapshot:
        selected = answers.get(q["id"])

        if selected == q["correct"]:
            correct += 1

    total = len(snapshot)
    score = (correct / total) * 100 if total else 0

    # =====================================
    # SAVE RESULT (ATOMIC)
    # =====================================

    result = await db["applications"].update_one(
        {
            "_id": app_obj,
            "mcq_attempted": False
        },
        {
            "$set": {
                "mcq_score": round(score, 2),
                "mcq_attempted": True,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(400, "Already submitted")

    return {
        "mcq_score": round(score, 2),
        "correct": correct,
        "total": total
    }