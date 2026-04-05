from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from ..config.settings import SCORING_CONFIG

router = APIRouter(prefix="/ranking", tags=["Ranking"])


@router.post("/candidates")
def rank_candidates(payload: Dict[str, Any]):
    """
    Rank candidates based on final_candidate_score.
    """

    candidates: List[Dict[str, Any]] = payload.get("candidates")

    if not candidates or not isinstance(candidates, list):
        raise HTTPException(
            status_code=400,
            detail="candidates must be a list"
        )

    cutoff = SCORING_CONFIG["shortlist_cutoff"]

    # Sort candidates by score (desc)
    sorted_candidates = sorted(
        candidates,
        key=lambda x: x.get("final_candidate_score", 0),
        reverse=True
    )

    ranked = []
    for idx, c in enumerate(sorted_candidates, start=1):
        score = c.get("final_candidate_score", 0)

        ranked.append({
            "rank": idx,
            "candidate_id": c.get("candidate_id"),
            "final_candidate_score": score,
            "decision": "SHORTLIST" if score >= cutoff else "REJECT"
        })

    return {
        "shortlist_cutoff": cutoff,
        "ranked_candidates": ranked
    }
