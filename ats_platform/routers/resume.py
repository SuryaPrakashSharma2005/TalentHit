from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Dict, Any
import json
import os

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..services.resume_service import process_resume
from ats_platform.storage.local import save_uploaded_file
from ..database.mongodb import get_db   # 🔥 IMPORTANT

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post("/analyze")
async def analyze_resume(
    resume_file: UploadFile = File(...),
    job_id: str = Form(...),
    job_requirements: str = Form(...),
    db: AsyncIOMotorDatabase = Depends(get_db)  # 🔥 INJECT DB
):

    if resume_file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        job_requirements_dict: Dict[str, Any] = json.loads(job_requirements)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid job_requirements JSON")

    resume_path = None

    try:
        resume_path = save_uploaded_file(resume_file)

        result = await process_resume(
            resume_path=resume_path,
            job_requirements=job_requirements_dict,
            job_id=job_id,
            db=db  # 🔥 PASS DB
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if resume_path and os.path.exists(resume_path):
            os.remove(resume_path)