from typing import Dict, Optional
from ..config.settings import SCORING_CONFIG


def calculate_final_candidate_score(
    resume_score: Dict[str, float],
    mcq_score: Optional[Dict[str, float]] = None,
    coding_score: Optional[Dict[str, float]] = None
) -> Dict[str, float]:

    # ==============================
    # SAFE EXTRACTION
    # ==============================

    resume_final = float(resume_score.get("final_score", 0))

    mcq_final = float(mcq_score.get("mcq_score", 0)) if mcq_score else None
    coding_final = float(coding_score.get("coding_score", 0)) if coding_score else None

    # ==============================
    # BASE WEIGHTS
    # ==============================

    resume_weight = SCORING_CONFIG.get("resume_weight", 0.5)
    mcq_weight = SCORING_CONFIG.get("mcq_weight", 0.3)
    coding_weight = SCORING_CONFIG.get("coding_weight", 0.2)

    # ==============================
    # DYNAMIC WEIGHT ADJUSTMENT
    # ==============================

    active_weights = {
        "resume": resume_weight,
        "mcq": mcq_weight if mcq_final is not None else 0,
        "coding": coding_weight if coding_final is not None else 0
    }

    total_active_weight = sum(active_weights.values())

    if total_active_weight == 0:
        total_active_weight = 1  # prevent division error

    # Normalize weights dynamically
    normalized_weights = {
        k: v / total_active_weight for k, v in active_weights.items()
    }

    # ==============================
    # FINAL SCORE CALCULATION
    # ==============================

    final_score = (
        resume_final * normalized_weights["resume"] +
        (mcq_final or 0) * normalized_weights["mcq"] +
        (coding_final or 0) * normalized_weights["coding"]
    )

    final_score = round(final_score, 2)

    # ==============================
    # DECISION LOGIC
    # ==============================

    cutoff = SCORING_CONFIG.get("shortlist_cutoff", 70)

    decision = "SHORTLISTED" if final_score >= cutoff else "REJECTED"

    # ==============================
    # PERFORMANCE LABEL (BONUS FEATURE)
    # ==============================

    if final_score >= 85:
        performance = "EXCELLENT"
    elif final_score >= 70:
        performance = "GOOD"
    elif final_score >= 50:
        performance = "AVERAGE"
    else:
        performance = "WEAK"

    # ==============================
    # RESPONSE
    # ==============================

    return {
        "final_candidate_score": final_score,
        "resume_score": resume_final,
        "mcq_score": mcq_final or 0,
        "coding_score": coding_final or 0,
        "weights": normalized_weights,
        "decision": decision,
        "performance": performance
    }