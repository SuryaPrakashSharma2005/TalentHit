from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from bson import ObjectId
import random

from ..database.mongodb import get_db
from ..core.dependencies import get_current_user
from ..services.scoring_service import calculate_resume_score
from ..services.final_score import calculate_final_candidate_score
from ..routers.notification import create_notification

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# ======================================================
# RECOMMENDED JOBS (SKILL MATCH BASED)
# ======================================================

from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

@router.get("/recommended")
async def get_recommended_jobs(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "applicant":
        raise HTTPException(403, "Only applicants allowed")

    user_id = ObjectId(current_user["id"])

    # ======================================================
    # 🔥 GET OR CREATE CANDIDATE
    # ======================================================
    candidate = await db["candidates"].find_one({
        "_id": user_id
    })

    if not candidate:
        candidate = {
            "_id": user_id,
            "name": current_user.get("email", "").split("@")[0],
            "email": current_user.get("email"),
            "skills": [],
            "experience_years": 0,
            "education": {},
            "created_at": datetime.now(timezone.utc)
        }

        await db["candidates"].insert_one(candidate)

    # ======================================================
    # 🔥 CANDIDATE SKILLS
    # ======================================================
    candidate_skills = set(
        skill.lower()
        for skill in candidate.get("skills", [])
    )

    # ======================================================
    # 🔥 GET APPLIED JOBS
    # ======================================================
    applied_jobs = await db["applications"].find(
        {"candidate_id": user_id},
        {"job_id": 1}
    ).to_list(length=1000)

    applied_job_ids = {
        str(app["job_id"])
        for app in applied_jobs
        if app.get("job_id")
    }

    # ======================================================
    # 🔥 FETCH ACTIVE JOBS
    # ======================================================
    jobs = []

    cursor = db["jobs"].find({
        "status": "ACTIVE"
    })

    async for job in cursor:

        # Skip already applied jobs
        if str(job["_id"]) in applied_job_ids:
            continue

        # ======================================================
        # 🔥 JOB SKILLS
        # ======================================================
        job_skills = set(
            skill.lower()
            for skill in job.get("required_skills", [])
        )

        # ======================================================
        # 🔥 MATCH CALCULATION
        # ======================================================
        if job_skills:
            match_percent = (
                len(candidate_skills & job_skills)
                / len(job_skills)
            ) * 100
        else:
            match_percent = 0

        # ======================================================
        # 🔥 FILTER LOW MATCH
        # ======================================================
        if candidate_skills and match_percent < 75:
            continue

        # ======================================================
        # 🔥 COMPANY DETAILS
        # ======================================================
        company = await db["companies"].find_one({
            "_id": job.get("company_id")
        })

        jobs.append({
            "_id": str(job["_id"]),

            # JOB
            "title": job.get("title"),
            "domain": job.get("domain"),
            "department": job.get("department"),

            # COMPANY
            "company_name": (
                company.get("name")
                if company else "Unknown Company"
            ),

            "company_logo": (
                company.get("logo")
                if company else None
            ),

            "company_website": (
                company.get("website")
                if company else None
            ),

            # REQUIREMENTS
            "min_experience": job.get(
                "min_experience",
                0
            ),

            "required_skills": job.get(
                "required_skills",
                []
            ),

            # MATCH
            "match_percentage": round(
                match_percent,
                2
            )
        })

    # ======================================================
    # 🔥 SORT
    # ======================================================
    jobs.sort(
        key=lambda x: x["match_percentage"],
        reverse=True
    )

    return jobs


# ======================================================
# PUBLIC ACTIVE JOB LISTING
# ======================================================

@router.get("")
async def get_active_jobs(
    skip: int = 0,
    limit: int = 20,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    jobs = []
    cursor = db["jobs"].find({"status": "ACTIVE"}).skip(skip).limit(limit)

    async for job in cursor:
        job["_id"] = str(job["_id"])
        job["company_id"] = str(job["company_id"])
        jobs.append(job)

    return jobs


# ======================================================
# CREATE JOB
# ======================================================

@router.post("/create")
async def create_job(
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):

    if current_user["role"] != "company":
        raise HTTPException(403, "Only companies can create jobs")

    if not payload.get("title"):
        raise HTTPException(400, "Title required")

    job = {
    "company_id": ObjectId(current_user["id"]),
    "title": payload["title"],
    "perks": payload.get("perks", []),
    "description": payload.get("description"),
    "eligibility_criteria": payload.get("eligibility_criteria"),

    # 🔥 NEW STRUCTURE
    "department": payload.get("department", "General"),
    "domain": payload.get("domain"),
    "sub_domain": payload.get("sub_domain"),

    "required_skills": payload.get("required_skills", []),
    "min_experience": payload.get("min_experience", 0),

    "degree": payload.get("degree"),
    "weights": payload.get("weights"),

    "openings": payload.get("openings", 1),
    "coding_language": payload.get("coding_language"),

    "status": "ACTIVE",
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}

    result = await db["jobs"].insert_one(job)

    job["_id"] = str(result.inserted_id)
    job["company_id"] = str(job["company_id"])

    return job


# ======================================================
# APPLY TO JOB (PRODUCTION LEVEL)
# ======================================================

@router.post("/{job_id}/apply")
async def apply_to_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):

    if current_user["role"] != "applicant":
        raise HTTPException(403, "Only applicants can apply")

    try:
        job_object_id = ObjectId(job_id)
        candidate_object_id = ObjectId(current_user["id"])
    except:
        raise HTTPException(400, "Invalid ID")

    job = await db["jobs"].find_one({"_id": job_object_id})
    if not job:
        raise HTTPException(404, "Job not found")

    if job.get("status") != "ACTIVE":
        raise HTTPException(400, "Job is closed")

    # Duplicate protection
    existing_application = await db["applications"].find_one({
        "job_id": job_object_id,
        "candidate_id": candidate_object_id
    })

    if existing_application:
        raise HTTPException(400, "Already applied to this job")

    # Openings enforcement
    shortlisted_count = await db["applications"].count_documents({
        "job_id": job_object_id,
        "stage": "SHORTLISTED"
    })

    if shortlisted_count >= job.get("openings", 1):
        raise HTTPException(400, "All openings have been filled")

    candidate = await db["candidates"].find_one({"_id": candidate_object_id})
    if not candidate or not candidate.get("skills"):
        raise HTTPException(400, "Upload resume before applying")

    # Resume scoring
    job_requirements = {
        "skills": job.get("required_skills", []),
        "min_experience": job.get("min_experience", 0),
        "degree": job.get("degree"),
        "weights": job.get("weights")
    }

    resume_score_breakdown = calculate_resume_score(
        candidate_skills=candidate.get("skills", []),
        candidate_experience=candidate.get("experience_years", 0),
        candidate_education=candidate.get("education", {}),
        job_requirements=job_requirements
    )

    pre_screen_score = resume_score_breakdown["final_score"]

        # 🔥 REAL SKILL MATCH CALCULATION
    candidate_skills = set(
        skill.lower() for skill in candidate.get("skills", [])
    )

    job_skills = set(
        skill.lower() for skill in job.get("required_skills", [])
    )

    skill_match_percentage = (
        (len(candidate_skills & job_skills) / len(job_skills)) * 100
        if job_skills else 0
    )

    if skill_match_percentage < 75:
        stage = "SKILL_REJECTED"

    elif job.get("domain") == "Software":
        stage = "ASSESSMENT_PENDING"   # MCQ + Coding

    else:
        stage = "MCQ_PENDING"          # Only MCQ

    application = {
    "job_id": job_object_id,
    "company_id": job["company_id"],
    "candidate_id": candidate_object_id,

    # ===============================
    # SCORES
    # ===============================
    "resume_score": pre_screen_score,
    "mcq_score": 0,
    "coding_score": 0,

    # ===============================
    # ASSESSMENT TYPE FLAGS
    # ===============================
    "mcq_required": True,
    "coding_required": job.get("domain") == "Software",
    # ===============================
    # MATCH METRICS
    # ===============================
    "skill_match_percentage": round(skill_match_percentage, 2),

    # Initial final score (resume only stage)
    "final_score": round(pre_screen_score * 0.5, 2),

    # ===============================
    # CODING TEST STATE
    # ===============================
    "coding_snapshot": [],
    "coding_started_at": None,
    "coding_duration_minutes": 30,
    "coding_attempted": False,

    # ===============================
    # MCQ TEST STATE
    # ===============================
    "mcq_snapshot": [],
    "mcq_started_at": None,
    "mcq_duration_minutes": 15,
    "mcq_attempted": False,

    # ===============================
    # APPLICATION STATUS
    # ===============================
    "stage": stage,
    "status": "ACTIVE",

    # ===============================
    # RESUME ANALYSIS BREAKDOWN
    # ===============================
    "resume_breakdown": resume_score_breakdown,

    # ===============================
    # STAGE HISTORY
    # ===============================
    "stage_history": [
        {
            "stage": stage,
            "timestamp": datetime.utcnow()
        }
    ],

    # ===============================
    # TIMESTAMPS
    # ===============================
    "created_at": datetime.utcnow(),
    "updated_at": datetime.utcnow()
}
    result = await db["applications"].insert_one(application)

    # 🔔 Notify company
    await create_notification(
        db=db,
        user_id=job["company_id"],
        title="New Application Received",
        message=f"A candidate applied for {job['title']}",
        metadata={"job_id": job_id}
    )

    return {
        "application_id": str(result.inserted_id),
        "stage": stage
    }


# ======================================================
# START TEST (SNAPSHOT BASED - PRODUCTION SAFE)
# ======================================================

@router.post("/{job_id}/applications/{application_id}/start-test")
async def start_test(
    job_id: str,
    application_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "applicant":
        raise HTTPException(403, "Unauthorized")

    try:
        app_obj = ObjectId(application_id)
        job_obj = ObjectId(job_id)
    except:
        raise HTTPException(400, "Invalid ID")

    application = await db["applications"].find_one({
        "_id": app_obj,
        "candidate_id": ObjectId(current_user["id"])
    })

    if not application:
        raise HTTPException(404, "Application not found")

    if application["stage"] not in [
        "ASSESSMENT_PENDING",
        "MCQ_PENDING",
        "ASSESSMENT_STARTED"
    ]:
        raise HTTPException(400, "Assessment not allowed")

    if application.get("mcq_attempted"):
        raise HTTPException(400, "Test already submitted")

    job = await db["jobs"].find_one({"_id": job_obj})
    required_skills = job.get("required_skills", [])

    question_pool = await db["mcq_bank"].find(
        {"skill": {"$in": required_skills}}
    ).to_list(length=200)

    if len(question_pool) < 10:
        raise HTTPException(400, "Not enough questions")

    selected = random.sample(question_pool, 10)

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

    await db["applications"].update_one(
        {"_id": app_obj},
        {
            "$set": {
                "stage": "ASSESSMENT_STARTED",
                "mcq_snapshot": snapshot,
                "mcq_started_at": datetime.utcnow(),
                "mcq_duration_minutes": 15,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "stage_history": {
                    "stage": "ASSESSMENT_STARTED",
                    "timestamp": datetime.utcnow()
                }
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
# SUBMIT MCQ (FINALIZE TEST)
# ======================================================

@router.post("/{job_id}/applications/{application_id}/submit-mcq")
async def submit_mcq(
    job_id: str,
    application_id: str,
    answers: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
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
        raise HTTPException(400, "Test already submitted")

    if application["stage"] != "ASSESSMENT_STARTED":
        raise HTTPException(400, "Test not started")

    started_at = application.get("mcq_started_at")
    duration = application.get("mcq_duration_minutes", 15)

    if started_at:
        expiry_time = started_at + timedelta(minutes=duration)
        if datetime.utcnow() > expiry_time:
            raise HTTPException(400, "Assessment time expired")

    snapshot = application.get("mcq_snapshot", [])

    if not snapshot:
        raise HTTPException(400, "No questions found")

    correct = 0

    for q in snapshot:
        selected = answers.get(q["id"])

        try:
            selected = int(selected)
        except (TypeError, ValueError):
            selected = None

        if selected == q["correct"]:
            correct += 1

    total = len(snapshot)
    mcq_score = (correct / total) * 100 if total else 0

    resume_score_value = application.get("resume_score", 0)

    score_data = calculate_final_candidate_score(
        {"final_score": resume_score_value},
        {"mcq_score": mcq_score},
        {"coding_score": application.get("coding_score", 0)}
    )

    final_score = score_data["final_candidate_score"]

    if application.get("coding_required"):
        stage = "CODING_PENDING"
    else:
        stage = "SHORTLISTED" if final_score >= 70 else "REJECTED"

    await db["applications"].update_one(
        {"_id": app_obj},
        {
            "$set": {
                "mcq_score": round(mcq_score, 2),
                "final_score": final_score,
                "stage": stage,
                "mcq_attempted": True,
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

    return {
        "mcq_score": round(mcq_score, 2),
        "final_score": final_score,
        "stage": stage
    }


# ======================================================
# MANUAL STAGE UPDATE (COMPANY CONTROL)
# ======================================================

@router.patch("/{job_id}/applications/{application_id}/stage")
async def update_application_stage(
    job_id: str,
    application_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "company":
        raise HTTPException(403, "Only companies allowed")

    new_stage = payload.get("stage")

    allowed_stages = ["INTERVIEW", "OFFERED", "HIRED", "REJECTED"]

    if new_stage not in allowed_stages:
        raise HTTPException(400, "Invalid stage")

    try:
        app_obj = ObjectId(application_id)
        job_obj = ObjectId(job_id)
    except:
        raise HTTPException(400, "Invalid ID")

    application = await db["applications"].find_one({
        "_id": app_obj,
        "job_id": job_obj,
        "company_id": ObjectId(current_user["id"])
    })

    if not application:
        raise HTTPException(404, "Application not found")

    await db["applications"].update_one(
        {"_id": app_obj},
        {
            "$set": {
                "stage": new_stage,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "stage_history": {
                    "stage": new_stage,
                    "timestamp": datetime.utcnow()
                }
            }
        }
    )

    return {"stage": new_stage}


@router.get("/{job_id}")
async def get_job_details(
    job_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):

    try:
        job_object_id = ObjectId(job_id)
    except:
        raise HTTPException(400, "Invalid job ID")

    job = await db["jobs"].find_one({
        "_id": job_object_id,
        "status": "ACTIVE"
    })

    if not job:
        raise HTTPException(404, "Job not found")

    company = await db["companies"].find_one({
        "_id": job.get("company_id")
    })

    return {
        "_id": str(job["_id"]),

        # JOB
        "title": job.get("title"),
        "description": job.get("description"),
        "eligibility_criteria": job.get("eligibility_criteria"),
        "perks": job.get("perks", []),
        "domain": job.get("domain"),
        "department": job.get("department"),
        "required_skills": job.get("required_skills", []),
        "min_experience": job.get("min_experience", 0),
        "openings": job.get("openings", 1),
        "created_at": str(job.get("created_at")),

        # COMPANY
        "company_name": (
            company.get("name")
            if company else "Unknown Company"
        ),

        "company_logo": (
            company.get("logo")
            if company else None
        ),

        "company_website": (
            company.get("website")
            if company else None
        ),

        "company_description": (
            company.get("description")
            if company else None
        ),

        # SHAREABLE LINK
        "share_url": f"https://talenthit.in/jobs/{str(job['_id'])}"
    }