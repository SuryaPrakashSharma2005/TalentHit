from typing import List, Dict, Any


DEFAULT_WEIGHTS = {
    "skills": 0.5,
    "experience": 0.3,
    "education": 0.2
}


# ======================================================
# MAIN FUNCTION
# ======================================================

def calculate_resume_score(
    candidate_skills: List[str],
    candidate_experience: float,
    candidate_education: Dict[str, str],
    job_requirements: Dict[str, Any]
) -> Dict[str, float]:

    # ==============================
    # NORMALIZATION
    # ==============================

    candidate_skills = [
        s.strip().lower() for s in (candidate_skills or [])
    ]

    required_skills = [
        s.strip().lower() for s in job_requirements.get("skills", [])
    ]

    required_exp = float(job_requirements.get("min_experience", 0.0))
    required_degree = job_requirements.get("degree")

    weights = job_requirements.get("weights") or DEFAULT_WEIGHTS

    # 🔒 Ensure weights sum to 1
    total_weight = sum(weights.values())
    if total_weight == 0:
        weights = DEFAULT_WEIGHTS
    else:
        weights = {k: v / total_weight for k, v in weights.items()}

    # ==============================
    # COMPONENT SCORES
    # ==============================

    skill_score = _skill_score(candidate_skills, required_skills)
    experience_score = _experience_score(candidate_experience, required_exp)
    education_score = _education_score(candidate_education, required_degree)

    # ==============================
    # FINAL SCORE
    # ==============================

    final_score = round(
        skill_score * weights["skills"] +
        experience_score * weights["experience"] +
        education_score * weights["education"],
        2
    )

    return {
        "final_score": final_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "education_score": education_score
    }


# ======================================================
# SKILL SCORING (INTELLIGENT MATCH)
# ======================================================

def _skill_score(candidate_skills: List[str],
                 required_skills: List[str]) -> float:

    if not required_skills:
        return 100.0

    if not candidate_skills:
        return 0.0

    matched = 0

    for req in required_skills:
        for cand in candidate_skills:
            if req in cand or cand in req:
                matched += 1
                break

    base_score = (matched / len(required_skills)) * 100

    # 🔥 BONUS for extra skills
    extra_skills = len(set(candidate_skills) - set(required_skills))
    bonus = min(extra_skills * 2, 10)  # max +10

    return round(min(base_score + bonus, 100), 2)


# ======================================================
# EXPERIENCE SCORING (SMART CURVE)
# ======================================================

def _experience_score(candidate_exp: float,
                      required_exp: float) -> float:

    candidate_exp = float(candidate_exp or 0.0)

    if required_exp <= 0:
        return 100.0

    if candidate_exp <= 0:
        return 0.0

    ratio = candidate_exp / required_exp

    if ratio >= 1:
        return 100.0

    # Smooth scaling instead of linear
    return round((ratio ** 0.7) * 100, 2)


# ======================================================
# EDUCATION SCORING (CONSISTENT 0–100)
# ======================================================

def _education_score(candidate_edu, required_degree):

    if not candidate_edu:
        return 0.0

    if isinstance(candidate_edu, str):
        candidate_degree = candidate_edu.lower()
    elif isinstance(candidate_edu, dict):
        candidate_degree = candidate_edu.get("degree", "").lower()
    else:
        return 0.0

    if not required_degree:
        return 100.0

    required_degree = required_degree.lower()

    # Exact match
    if required_degree in candidate_degree:
        return 100.0

    # Partial match (B.Tech vs B.E etc.)
    if any(word in candidate_degree for word in required_degree.split()):
        return 70.0

    return 0.0