from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

# Extractor imports
from ..extractor.pdf import extract_pdf_text
from ..extractor.clean import clean_text
from ..extractor.personal import extract_personal_info
from ..extractor.skills import extract_skills
from ..extractor.experience import extract_experience_years
from ..extractor.education import extract_education

# Services
from ..services.llm_client import LLMClient
from ..services.scoring_service import calculate_resume_score
from ..services.final_score import calculate_final_candidate_score

# Mongo CRUD
from ..database.crud import get_or_create_candidate, create_evaluation


async def process_resume(
    resume_path: str,
    job_requirements: Dict[str, Any],
    job_id: str,
    db: AsyncIOMotorDatabase
) -> Dict[str, Any]:
    """
    Production-safe resume evaluation engine.
    """

    # ======================================================
    # 1️⃣ Extract raw text
    # ======================================================

    raw_text = extract_pdf_text(resume_path)

    if not raw_text or len(raw_text.strip()) < 20:
        raise ValueError("Resume content is empty or unreadable")

    # ======================================================
    # 2️⃣ Clean text
    # ======================================================

    cleaned_text = clean_text(raw_text)

    # ======================================================
    # 3️⃣ Extract structured data
    # ======================================================

    personal_info = extract_personal_info(raw_text)
    skills = extract_skills(cleaned_text)
    experience_years = extract_experience_years(cleaned_text)
    education = extract_education(cleaned_text) or {}

    # Normalize email
    email = personal_info.get("email")
    if email:
        email = email.strip().lower()

    # ======================================================
    # 4️⃣ Resume scoring
    # ======================================================

    resume_score = calculate_resume_score(
        candidate_skills=skills,
        candidate_experience=experience_years,
        candidate_education=education,
        job_requirements=job_requirements or {}
    )

    # ======================================================
    # 5️⃣ LLM Summary (Safe Fallback Built-in)
    # ======================================================

    llm = LLMClient()
    summary = llm.generate_resume_summary(
        name=personal_info.get("name"),
        skills=skills,
        experience_years=experience_years,
        education=education
    )

    # ======================================================
    # 6️⃣ Final Score (Resume Only)
    # ======================================================

    final_result = calculate_final_candidate_score(
        resume_score=resume_score,
        mcq_score={"mcq_score": 0}
    )

    # ======================================================
    # 7️⃣ Candidate Handling (SAFE)
    # ======================================================

    if not email:
        raise ValueError("Email not found in resume")

    candidate = await get_or_create_candidate(
        db=db,
        name=personal_info.get("name"),
        email=email
    )

    await db["candidates"].update_one(
        {"_id": candidate["_id"]},
        {
            "$set": {
                "skills": skills,
                "experience_years": experience_years,
                "education": education,
                "updated_at": datetime.utcnow()
            }
        }
    )

    # ======================================================
    # 8️⃣ Save Evaluation (Only if job_id provided)
    # ======================================================

    evaluation_id = None

    if job_id:
        evaluation = await create_evaluation(
            db=db,
            job_id=job_id,
            candidate_id=candidate["_id"],
            resume_score=resume_score["final_score"],
            mcq_score=0,
            final_score=final_result["final_candidate_score"],
            decision=None,
            resume_breakdown=resume_score,
            mcq_breakdown=None
        )

        evaluation_id = str(evaluation["_id"])

    # ======================================================
    # 9️⃣ Response
    # ======================================================

    return {
        "candidate_id": str(candidate["_id"]),
        "job_id": job_id,
        "evaluation_id": evaluation_id,
        "personal_info": personal_info,
        "skills": skills,
        "experience_years": experience_years,
        "education": education,
        "resume_score": resume_score,
        "final_score": final_result,
        "summary": summary
    }