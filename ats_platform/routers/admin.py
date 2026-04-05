from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from ..config.settings import SCORING_CONFIG

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/scoring-config")
def get_scoring_config():
    return SCORING_CONFIG


@router.post("/scoring-config")
def update_scoring_config(payload: Dict[str, Any]):

    resume_weight = payload.get("resume_weight")
    mcq_weight = payload.get("mcq_weight")
    shortlist_cutoff = payload.get("shortlist_cutoff")

    if resume_weight is not None:
        SCORING_CONFIG["resume_weight"] = resume_weight

    if mcq_weight is not None:
        SCORING_CONFIG["mcq_weight"] = mcq_weight

    if shortlist_cutoff is not None:
        SCORING_CONFIG["shortlist_cutoff"] = shortlist_cutoff

    if SCORING_CONFIG["resume_weight"] + SCORING_CONFIG["mcq_weight"] != 1.0:
        raise HTTPException(
            status_code=400,
            detail="resume_weight + mcq_weight must equal 1.0"
        )

    return SCORING_CONFIG
