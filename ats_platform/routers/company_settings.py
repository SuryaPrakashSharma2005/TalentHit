from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Dict, Any
from datetime import datetime

from ..database.mongodb import get_db
from ..core.dependencies import get_current_user

router = APIRouter(prefix="/company", tags=["Company Settings"])


# ======================================================
# DEFAULT SETTINGS TEMPLATE
# ======================================================

def default_company_settings(company_object_id: ObjectId):
    return {
        "company_id": company_object_id,
        "name": "",
        "email": "",
        "website": "",
        "notify_new_applications": True,
        "notify_assessment_complete": True,
        "notify_weekly_reports": False,
        "auto_screen": True,
        "require_assessment": True,
        "screening_cutoff": 60,  # ✅ NEW (production-ready threshold)
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


# ======================================================
# GET COMPANY SETTINGS
# ======================================================

@router.get("/{company_id}/settings")
async def get_company_settings(
    company_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        company_object_id = ObjectId(company_id)
    except:
        raise HTTPException(400, "Invalid company_id")

    if current_user["role"] != "company":
        raise HTTPException(403, "Not authorized")

    if current_user["id"] != company_id:
        raise HTTPException(403, "Forbidden")

    settings = await db["company_settings"].find_one({
        "company_id": company_object_id
    })

    if not settings:
        settings = default_company_settings(company_object_id)
        await db["company_settings"].insert_one(settings)

    settings["_id"] = str(settings["_id"])
    settings["company_id"] = str(settings["company_id"])

    return settings


# ======================================================
# UPDATE COMPANY SETTINGS
# ======================================================

@router.patch("/{company_id}/settings")
async def update_company_settings(
    company_id: str,
    payload: Dict[str, Any],
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        company_object_id = ObjectId(company_id)
    except:
        raise HTTPException(400, "Invalid company_id")

    if current_user["role"] != "company":
        raise HTTPException(403, "Not authorized")

    if current_user["id"] != company_id:
        raise HTTPException(403, "Forbidden")

    existing = await db["company_settings"].find_one({
        "company_id": company_object_id
    })

    if not existing:
        raise HTTPException(404, "Settings not found")

    # 🔐 Prevent protected field override
    payload.pop("company_id", None)
    payload.pop("_id", None)
    payload.pop("created_at", None)

    # 🛡 Validate screening_cutoff
    if "screening_cutoff" in payload:
        cutoff = payload["screening_cutoff"]
        if not isinstance(cutoff, (int, float)) or not (0 <= cutoff <= 100):
            raise HTTPException(
                status_code=400,
                detail="screening_cutoff must be between 0 and 100"
            )

    payload["updated_at"] = datetime.utcnow()

    await db["company_settings"].update_one(
        {"company_id": company_object_id},
        {"$set": payload}
    )

    return {"message": "Settings updated successfully"}