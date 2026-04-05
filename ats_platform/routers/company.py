from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId

from ..database.mongodb import get_db
from ..core.dependencies import get_current_user
from ..routers.notification import create_notification

router = APIRouter(prefix="/company", tags=["Company"])


# ======================================================
# CREATE COMPANY
# ======================================================

@router.post("/create")
async def create_company(
    payload: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "company":
        raise HTTPException(403, "Only company accounts allowed")

    name = payload.get("name")
    email = payload.get("email")

    if not name or not email:
        raise HTTPException(400, "name and email required")

    existing = await db["companies"].find_one({"email": email})
    if existing:
        raise HTTPException(400, "Company already exists")

    company = {
        "_id": ObjectId(current_user["id"]),
        "name": name,
        "email": email,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    await db["companies"].insert_one(company)

    company["_id"] = str(company["_id"])
    return company


# ======================================================
# GET COMPANY PROFILE
# ======================================================

@router.get("/me")
async def get_my_company(
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "company":
        raise HTTPException(403, "Unauthorized")

    company = await db["companies"].find_one({
        "_id": ObjectId(current_user["id"])
    })

    if not company:
        raise HTTPException(404, "Company profile not found")

    company["_id"] = str(company["_id"])
    return company


# ======================================================
# GET COMPANY JOBS
# ======================================================

@router.get("/jobs")
async def get_company_jobs(
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "company":
        raise HTTPException(403, "Unauthorized")

    jobs = []
    cursor = db["jobs"].find({
        "company_id": ObjectId(current_user["id"])
    })

    async for job in cursor:
        job["_id"] = str(job["_id"])
        job["company_id"] = str(job["company_id"])
        jobs.append(job)

    return jobs


# ======================================================
# GET APPLICANTS (RANKED)
# ======================================================

@router.get("/jobs/{job_id}/applicants")
async def get_job_applicants(
    job_id: str,
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "company":
        raise HTTPException(403, "Unauthorized")

    try:
        job_object_id = ObjectId(job_id)
    except:
        raise HTTPException(400, "Invalid job_id")

    # Verify job belongs to company
    job = await db["jobs"].find_one({
        "_id": job_object_id,
        "company_id": ObjectId(current_user["id"])
    })

    if not job:
        raise HTTPException(404, "Job not found")

    applicants = []

    cursor = db["applications"].find({
        "job_id": job_object_id
    }).sort("final_score", -1)

    async for app in cursor:

        candidate = await db["candidates"].find_one({
            "_id": app["candidate_id"]
        })

        applicants.append({
            "_id": str(app["_id"]),                     # application id
            "candidate_id": str(app["candidate_id"]),

            # Candidate details
            "candidate_name": candidate.get("name") if candidate else "Unknown",
            "candidate_email": candidate.get("email") if candidate else None,
            "phone": candidate.get("phone") if candidate else None,
            "location": candidate.get("location") if candidate else None,

            # Scores
            "resume_score": app.get("resume_score", 0),
            "mcq_score": app.get("mcq_score", 0),
            "coding_score": app.get("coding_score", 0),
            "final_score": app.get("final_score", 0),
            "skill_match_percentage": app.get("skill_match_percentage", 0),

            # Application info
            "stage": app.get("stage"),
            "created_at": app.get("created_at"),

            # Candidate skills
            "skills": candidate.get("skills", []) if candidate else []
        })

    return applicants


# ======================================================
# AUTO SHORTLIST (OPENINGS x4 RULE)
# ======================================================

@router.post("/jobs/{job_id}/auto-shortlist")
async def auto_shortlist(
    job_id: str,
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):

    if current_user["role"] != "company":
        raise HTTPException(403, "Unauthorized")

    try:
        job_object_id = ObjectId(job_id)
    except:
        raise HTTPException(400, "Invalid job_id")

    job = await db["jobs"].find_one({
        "_id": job_object_id,
        "company_id": ObjectId(current_user["id"])
    })

    if not job:
        raise HTTPException(404, "Job not found")

    openings = job.get("openings", 1)
    shortlist_limit = openings * 4

    cursor = db["applications"].find({
        "job_id": job_object_id,
        "stage": {"$ne": "SHORTLISTED"}
    }).sort("final_score", -1).limit(shortlist_limit)

    shortlisted_ids = []

    async for app in cursor:

        await db["applications"].update_one(
            {"_id": app["_id"]},
            {
                "$set": {
                    "stage": "SHORTLISTED",
                    "updated_at": datetime.utcnow()
                },
                "$push": {
                    "stage_history": {
                        "stage": "SHORTLISTED",
                        "timestamp": datetime.utcnow()
                    }
                }
            }
        )

        # 🔔 Notify candidate
        await create_notification(
            db=db,
            user_id=app["candidate_id"],
            title="Application Shortlisted",
            message=f"You have been shortlisted for {job['title']}.",
            metadata={"job_id": job_id}
        )

        shortlisted_ids.append(str(app["_id"]))

    return {
        "message": "Auto shortlist completed",
        "shortlisted_count": len(shortlisted_ids)
    }


# ======================================================
# COMPANY ANALYTICS (ADVANCED)
# ======================================================

@router.get("/analytics")
async def get_company_analytics(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):
    if current_user["role"] != "company":
        raise HTTPException(403, "Unauthorized")

    company_id = ObjectId(current_user["id"])   # ✅ FIXED

    # ----------------------------
    # TOTAL JOBS
    # ----------------------------
    total_jobs = await db.jobs.count_documents({
        "company_id": company_id
    })

    # ----------------------------
    # TOTAL APPLICATIONS
    # ----------------------------
    total_applications = await db.applications.count_documents({
        "company_id": company_id
    })

    # ----------------------------
    # AVERAGE FINAL SCORE
    # ----------------------------
    avg_pipeline = [
        {"$match": {"company_id": company_id}},
        {"$group": {
            "_id": None,
            "avg_score": {"$avg": "$final_score"}
        }}
    ]

    avg_result = await db.applications.aggregate(avg_pipeline).to_list(1)

    average_final_score = (
        avg_result[0]["avg_score"]
        if avg_result else 0
    )

    # ----------------------------
    # STAGE DISTRIBUTION
    # ----------------------------
    stage_pipeline = [
        {"$match": {"company_id": company_id}},
        {"$group": {
            "_id": "$stage",
            "count": {"$sum": 1}
        }}
    ]

    stage_results = await db.applications.aggregate(stage_pipeline).to_list(None)

    stage_distribution = {
        row["_id"]: row["count"] for row in stage_results
    }

    # ----------------------------
    # SHORTLIST CONVERSION
    # ----------------------------
    shortlisted = stage_distribution.get("SHORTLISTED", 0)

    conversion_rate = (
        (shortlisted / total_applications) * 100
        if total_applications > 0 else 0
    )

    # ----------------------------
    # TOP SKILLS
    # ----------------------------
    skills_pipeline = [
        {"$match": {"company_id": company_id}},
        {"$unwind": "$required_skills"},
        {"$group": {
            "_id": "$required_skills",
            "demand": {"$sum": 1}
        }},
        {"$sort": {"demand": -1}},
        {"$limit": 5}
    ]

    skills_result = await db.jobs.aggregate(skills_pipeline).to_list(None)

    top_skills = [
        {"skill": row["_id"], "demand": row["demand"]}
        for row in skills_result
    ]

    # ----------------------------
    # JOBS BY DEPARTMENT
    # ----------------------------
    dept_pipeline = [
        {"$match": {"company_id": company_id}},
        {"$group": {
            "_id": "$department",
            "count": {"$sum": 1}
        }}
    ]

    dept_result = await db.jobs.aggregate(dept_pipeline).to_list(None)

    jobs_by_department = [
        {"department": row["_id"], "count": row["count"]}
        for row in dept_result if row["_id"]
    ]

    return {
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "average_final_score": round(average_final_score, 2),
        "shortlist_conversion_rate": round(conversion_rate, 2),
        "stage_distribution": stage_distribution,
        "top_skills": top_skills,
        "jobs_by_department": jobs_by_department
    }
# ======================================================
# COMPANY REPORTS (BASIC)
# ======================================================

# ======================================================
# COMPANY REPORTS (EXECUTIVE LEVEL)
# ======================================================

@router.get("/reports")
async def company_reports(
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "company":
        raise HTTPException(403, "Unauthorized")

    company_id = ObjectId(current_user["id"])

    # --------------------------------------------------
    # BASIC COUNTS
    # --------------------------------------------------

    total_jobs = await db["jobs"].count_documents({
        "company_id": company_id
    })

    total_applications = await db["applications"].count_documents({
        "company_id": company_id
    })

    # --------------------------------------------------
    # STAGE DISTRIBUTION
    # --------------------------------------------------

    stage_pipeline = db["applications"].aggregate([
        {"$match": {"company_id": company_id}},
        {"$group": {
            "_id": "$stage",
            "count": {"$sum": 1}
        }}
    ])

    stage_distribution = {}

    async for row in stage_pipeline:
        stage_distribution[row["_id"]] = row["count"]

    # --------------------------------------------------
    # AVERAGE FINAL SCORE
    # --------------------------------------------------

    avg_score_pipeline = db["applications"].aggregate([
        {"$match": {"company_id": company_id}},
        {"$group": {
            "_id": None,
            "avg_score": {"$avg": "$final_score"}
        }}
    ])

    avg_score_result = await avg_score_pipeline.to_list(length=1)
    average_final_score = (
        round(avg_score_result[0]["avg_score"], 2)
        if avg_score_result and avg_score_result[0]["avg_score"]
        else 0
    )

    # --------------------------------------------------
    # SHORTLIST CONVERSION RATE
    # --------------------------------------------------

    shortlisted = stage_distribution.get("SHORTLISTED", 0)

    shortlist_conversion_rate = (
        round((shortlisted / total_applications) * 100, 2)
        if total_applications > 0 else 0
    )

    # --------------------------------------------------
    # TOP SKILLS IN DEMAND (FROM JOBS)
    # --------------------------------------------------

    skill_pipeline = db["jobs"].aggregate([
        {"$match": {"company_id": company_id}},
        {"$unwind": "$required_skills"},
        {"$group": {
            "_id": "$required_skills",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ])

    top_skills = []

    async for row in skill_pipeline:
        top_skills.append({
            "skill": row["_id"],
            "demand": row["count"]
        })

    # --------------------------------------------------
    # JOBS BY DEPARTMENT (IF YOU STORE department FIELD)
    # --------------------------------------------------

    department_pipeline = db["jobs"].aggregate([
        {"$match": {"company_id": company_id}},
        {"$group": {
            "_id": "$department",
            "count": {"$sum": 1}
        }}
    ])

    jobs_by_department = []

    async for row in department_pipeline:
        if row["_id"]:  # ignore null
            jobs_by_department.append({
                "department": row["_id"],
                "count": row["count"]
            })

    # --------------------------------------------------
    # FINAL EXECUTIVE RESPONSE
    # --------------------------------------------------

    return {
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "stage_distribution": stage_distribution,
        "average_final_score": average_final_score,
        "shortlist_conversion_rate": shortlist_conversion_rate,
        "top_skills": top_skills,
        "jobs_by_department": jobs_by_department
    }

# ======================================================
# GET COMPANY SETTINGS
# ======================================================

@router.get("/settings")
async def get_company_settings(
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "company":
        raise HTTPException(403, "Unauthorized")

    company_id = ObjectId(current_user["id"])

    company = await db["companies"].find_one({"_id": company_id})

    # 🔥 AUTO CREATE IF NOT EXISTS
    if not company:
        company = {
            "_id": company_id,
            "name": "",
            "email": "",
            "website": "",
            "notify_new_applications": True,
            "notify_assessment_complete": True,
            "notify_weekly_reports": False,
            "auto_screen": True,
            "require_assessment": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        await db["companies"].insert_one(company)

    return {
        "name": company.get("name", ""),
        "email": company.get("email", ""),
        "website": company.get("website", ""),
        "logo": company.get("logo"),
        "notify_new_applications": company.get("notify_new_applications", True),
        "notify_assessment_complete": company.get("notify_assessment_complete", True),
        "notify_weekly_reports": company.get("notify_weekly_reports", False),
        "auto_screen": company.get("auto_screen", True),
        "require_assessment": company.get("require_assessment", True),
    }

# ======================================================
# UPDATE COMPANY SETTINGS
# ======================================================

@router.patch("/settings")
async def update_company_settings(
    payload: Dict[str, Any],
    current_user=Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if current_user["role"] != "company":
        raise HTTPException(403, "Unauthorized")

    company_id = ObjectId(current_user["id"])

    allowed_fields = {
        "name",
        "email",
        "website",
        "logo",
        "notify_new_applications",
        "notify_assessment_complete",
        "notify_weekly_reports",
        "auto_screen",
        "require_assessment",
    }

    update_data = {
        key: value
        for key, value in payload.items()
        if key in allowed_fields
    }

    if not update_data:
        raise HTTPException(400, "No valid fields to update")

    update_data["updated_at"] = datetime.utcnow()

    await db["companies"].update_one(
        {"_id": company_id},
        {"$set": update_data}
    )

    return {"message": "Settings updated successfully"}