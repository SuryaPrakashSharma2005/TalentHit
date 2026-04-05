from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
import os

from ..database.mongodb import get_db
from ..services.final_score import calculate_final_candidate_score
from ..core.dependencies import get_current_user
from ats_platform.storage.local import save_uploaded_file
from ats_platform.services.resume_service import process_resume

router = APIRouter(prefix="/candidate", tags=["Candidate"])


# ======================================================
# SAFE FIELD DEFINITIONS
# ======================================================

ALLOWED_PROFILE_FIELDS = {
    "name",
    "phone",
    "location",
    "avatar",
    "experience_years",
    "education",
    "skills"
}
ALLOWED_SETTINGS_FIELDS = {"phone", "location", "settings"}


# ======================================================
# GET MY PROFILE
# ======================================================

@router.get("/me")
async def get_my_profile(
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "applicant":
        raise HTTPException(403, "Not authorized")

    candidate = await db["candidates"].find_one({
        "_id": ObjectId(current_user["id"])
    })

    if not candidate:
        raise HTTPException(404, "Profile not found")

    return {
        "_id": str(candidate["_id"]),
        "name": candidate.get("name"),
        "email": candidate.get("email"),
        "skills": candidate.get("skills", []),
        "experience_years": candidate.get("experience_years", 0),
        "education": candidate.get("education", {}),
        "avatar": candidate.get("avatar")
    }


# ======================================================
# FINAL SCORE CALCULATION
# ======================================================

@router.post("/final-score")
def final_candidate_score(payload: Dict[str, Any]):

    resume_score = payload.get("resume_score")
    mcq_score = payload.get("mcq_score")

    if resume_score is None or mcq_score is None:
        raise HTTPException(400, "resume_score and mcq_score are required")

    result = calculate_final_candidate_score(
        resume_score=resume_score,
        mcq_score=mcq_score
    )

    result["decision"] = (
        "SHORTLIST" if result["final_candidate_score"] >= 70 else "REJECT"
    )

    return result


# ======================================================
# UPDATE PROFILE (SAFE PATCH)
# ======================================================

# ======================================================
# UPDATE PROFILE (SAFE PATCH)
# ======================================================

@router.patch("/me")
async def update_my_profile(
    payload: dict,
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):

    if current_user["role"] != "applicant":
        raise HTTPException(403, "Only applicants allowed")

    candidate_id = ObjectId(current_user["id"])

    # allow only safe fields
    safe_payload = {
        k: v for k, v in payload.items()
        if k in ALLOWED_PROFILE_FIELDS
    }

    if not safe_payload:
        raise HTTPException(400, "No valid fields to update")

    safe_payload["updated_at"] = datetime.utcnow()

    await db["candidates"].update_one(
        {"_id": candidate_id},
        {"$set": safe_payload}
    )

    return {"message": "Profile updated successfully"}
# ======================================================
# GET SETTINGS (FIX FOR 405)
# ======================================================

@router.get("/{candidate_id}/settings")
async def get_candidate_settings(
    candidate_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):

    if current_user["id"] != candidate_id:
        raise HTTPException(403, "Not authorized")

    try:
        object_id = ObjectId(candidate_id)
    except:
        raise HTTPException(400, "Invalid candidate_id")

    candidate = await db["candidates"].find_one({"_id": object_id})

    if not candidate:
        raise HTTPException(404, "Candidate not found")

    return {
        "phone": candidate.get("phone"),
        "location": candidate.get("location"),
        "settings": candidate.get("settings", {})
    }
# ======================================================
# UPDATE SETTINGS (SAFE PATCH)
# ======================================================

@router.patch("/{candidate_id}/settings")
async def update_candidate_settings(
    candidate_id: str,
    payload: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):

    if current_user["id"] != candidate_id:
        raise HTTPException(403, "Not authorized")

    try:
        object_id = ObjectId(candidate_id)
    except:
        raise HTTPException(400, "Invalid candidate_id")

    safe_payload = {
        k: v for k, v in payload.items()
        if k in ALLOWED_SETTINGS_FIELDS
    }

    if not safe_payload:
        raise HTTPException(400, "No valid settings to update")

    safe_payload["updated_at"] = datetime.utcnow()

    await db["candidates"].update_one(
        {"_id": object_id},
        {"$set": safe_payload}
    )

    return {"message": "Settings updated successfully"}


# ======================================================
# GET APPLICATIONS (FIXED QUERY)
# ======================================================

@router.get("/{candidate_id}/applications")
async def get_candidate_applications(
    candidate_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):

    if current_user["id"] != candidate_id:
        raise HTTPException(403, "Not authorized")

    try:
        object_id = ObjectId(candidate_id)
    except:
        raise HTTPException(400, "Invalid candidate_id")

    apps = []

    cursor = db["applications"].find({
        "candidate_id": object_id  # ✅ FIXED
    })

    async for a in cursor:
        job = await db["jobs"].find_one({"_id": a.get("job_id")})

        apps.append({
            "_id": str(a["_id"]),
            "job_id": str(a.get("job_id")) if a.get("job_id") else None,
            "company_id": str(a.get("company_id")) if a.get("company_id") else None,
            "candidate_id": str(a.get("candidate_id")) if a.get("candidate_id") else None,
            "resume_score": float(a.get("resume_score", 0)),
            "mcq_score": float(a.get("mcq_score", 0)),
            "final_score": float(a.get("final_score", 0)),
            "stage": a.get("stage", "APPLIED"),
            "created_at": str(a.get("created_at")) if a.get("created_at") else None,
            "job_title": job.get("title") if job else "Job Closed",
            "skill_match_percentage": float(a.get("skill_match_percentage", 0)),
            "min_experience": job.get("min_experience", 0) if job else 0,
        })

    return apps


# ======================================================
# UPLOAD RESUME (HARDENED)
# ======================================================

# ======================================================
# UPLOAD RESUME (HARDENED)
# ======================================================

@router.post("/upload-resume")
async def upload_resume(
    resume_file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):

    if current_user["role"] != "applicant":
        raise HTTPException(403, "Only applicants allowed")

    candidate_id = ObjectId(current_user["id"])

    if resume_file.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF allowed")

    resume_path = save_uploaded_file(resume_file)

    try:
        result = await process_resume(
            resume_path=resume_path,
            job_requirements={},
            job_id=None,
            db=db
        )

        extracted_skills = result.get("skills", [])

        await db["candidates"].update_one(
            {"_id": candidate_id},
            {
                "$set": {
                    "skills": extracted_skills,
                    "resume_uploaded": True,
                    "resume_updated_at": datetime.utcnow()
                }
            }
        )

        return {
            "message": "Resume uploaded successfully",
            "skills": extracted_skills
        }

    finally:
        if os.path.exists(resume_path):
            os.remove(resume_path)