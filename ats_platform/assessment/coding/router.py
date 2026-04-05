from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime, timedelta
from typing import Dict, Optional
from pydantic import BaseModel, field_validator

from ...database.mongodb import get_db
from ...core.dependencies import get_current_user
from ...services.final_score import calculate_final_candidate_score
from .executor import run_python_code

from .selector import select_coding_questions
from .evaluator import evaluate_solution

router = APIRouter(prefix="/coding", tags=["Coding"])


# ======================================================
# Pydantic Schema (CRITICAL FIX)
# ======================================================

class CodingSubmission(BaseModel):
    answers: Dict[str, str]

    @field_validator("answers")
    def validate_answers(cls, v):
        if not isinstance(v, dict):
            raise ValueError("answers must be a dictionary")

        for key, code in v.items():
            if not isinstance(code, str):
                raise ValueError("Each answer must be string code")

            if len(code) > 10000:  # 🚨 anti abuse
                raise ValueError("Code too large")

        return v


# ======================================================
# START CODING TEST
# ======================================================

@router.post("/start/{application_id}")
async def start_coding_test(
    application_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    if current_user["role"] != "applicant":
        raise HTTPException(403, "Unauthorized")

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

    # 🚨 Validations
    if not application.get("coding_required"):
        raise HTTPException(400, "Coding test not required")

    if not application.get("mcq_attempted"):
        raise HTTPException(400, "Complete MCQ first")

    if application.get("coding_attempted"):
        raise HTTPException(400, "Already submitted")

    if application.get("coding_started_at"):
        raise HTTPException(400, "Test already started")

    # Fetch questions
    questions = await select_coding_questions(db)

    await db["applications"].update_one(
        {"_id": app_obj},
        {
            "$set": {
                "coding_snapshot": questions,
                "coding_started_at": datetime.utcnow(),
                "coding_duration_minutes": 30,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {
        "questions": [
            {
                "_id": q["_id"],
                "title": q.get("title"),
                "description": q.get("description"),
                "difficulty": q.get("difficulty")
            }
            for q in questions
        ],
    }


# ======================================================
# SUBMIT CODING TEST
# ======================================================

@router.post("/submit/{application_id}")
async def submit_coding(
    application_id: str,
    payload: CodingSubmission,  # ✅ FIXED
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    try:
        app_obj = ObjectId(application_id)
    except:
        raise HTTPException(400, "Invalid ID")

    # 🔒 Atomic fetch
    application = await db["applications"].find_one({
        "_id": app_obj,
        "candidate_id": ObjectId(current_user["id"])
    })

    if not application:
        raise HTTPException(404, "Application not found")

    if not application.get("coding_required"):
        raise HTTPException(400, "Coding not required")

    if application.get("coding_attempted"):
        raise HTTPException(400, "Already submitted")

    snapshot = application.get("coding_snapshot")

    if not snapshot:
        raise HTTPException(400, "Test not started")

    # =====================================
    # TIME LIMIT CHECK
    # =====================================

    started_at = application.get("coding_started_at")
    duration = application.get("coding_duration_minutes", 30)

    if not started_at:
        raise HTTPException(400, "Invalid test state")

    expiry_time = started_at + timedelta(minutes=duration)

    if datetime.utcnow() > expiry_time:
        raise HTTPException(400, "Time expired")

    answers = payload.answers

    # =====================================
    # SNAPSHOT VALIDATION (ANTI CHEAT)
    # =====================================

    valid_question_ids = {q["_id"] for q in snapshot}

    for qid in answers.keys():
        if str(qid) not in valid_question_ids:
            raise HTTPException(400, "Invalid question ID detected")

    # =====================================
    # EVALUATION
    # =====================================

    scores = []

    for q in snapshot:

        user_code: Optional[str] = answers.get(str(q["_id"]))

        if not user_code:
            scores.append(0)
            continue

        try:
            score = await evaluate_solution(q, user_code)
        except Exception:
            score = 0

        scores.append(score)

    coding_score = round(sum(scores) / len(scores), 2) if scores else 0

    # =====================================
    # FINAL SCORE
    # =====================================

    score_data = calculate_final_candidate_score(
        {"final_score": application.get("resume_score", 0)},
        {"mcq_score": application.get("mcq_score", 0)},
        {"coding_score": coding_score}
    )

    final_score = score_data["final_candidate_score"]

    stage = "SHORTLISTED" if final_score >= 75 else "REJECTED"

    # =====================================
    # ATOMIC UPDATE (ANTI DOUBLE SUBMIT)
    # =====================================

    result = await db["applications"].update_one(
        {
            "_id": app_obj,
            "coding_attempted": False  # 🔒 prevents race condition
        },
        {
            "$set": {
                "coding_score": coding_score,
                "final_score": final_score,
                "stage": stage,
                "coding_attempted": True,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "stage_history": {
                    "stage": stage,
                    "timestamp": datetime.utcnow()
                }
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(400, "Submission already processed")

    return {
        "coding_score": coding_score,
        "final_score": final_score,
        "stage": stage
    }

@router.post("/run")
async def run_code(
    payload: Dict,
    current_user: dict = Depends(get_current_user)
):
    code = payload.get("code", "")
    input_data = payload.get("input", "")

    if not code:
        raise HTTPException(400, "Code is required")

    result = run_python_code(code, input_data)

    return result