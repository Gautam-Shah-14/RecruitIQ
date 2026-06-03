import math

SENIORITY_MAP = {"junior": 1, "mid": 2, "senior": 3, "staff": 4, "principal": 5}

def compute_skill_match(jd_skills: list[str], candidate_skills: list) -> float:
    jd_set   = set(s.lower() for s in jd_skills if isinstance(s, str))
    cand_set = set((s.get("name", "").lower() if isinstance(s, dict) else str(s).lower()) for s in candidate_skills)
    if not jd_set:
        return 0.0
    intersection = len(jd_set & cand_set)
    union        = len(jd_set | cand_set)
    return intersection / union

def compute_seniority_fit(jd_level: str, candidate_years: int) -> float:
    target_years = {1: 1, 2: 3, 3: 6, 4: 10, 5: 15}.get(SENIORITY_MAP.get(jd_level, 2), 3)
    diff = abs(candidate_years - target_years)
    return float(math.exp(-0.5 * (diff / 2) ** 2))

def compute_trajectory(career_history: list[dict]) -> float:
    # Placeholder for more complex calculation, this returns a float 0-1
    # For now simply returning 0.5 if they have a job history, better than nothing
    return 0.5

def compute_behavioral(behavioral: dict) -> float:
    score  = min(behavioral.get("oss_commits", 0) / 100, 1.0) * 0.40
    score += min(behavioral.get("talks",       0) / 5,   1.0) * 0.30
    score += min(behavioral.get("articles",    0) / 10,  1.0) * 0.30
    return round(score, 4)

def compute_composite_score(
    semantic_similarity: float,
    skill_match: float,
    seniority_fit: float,
    trajectory_score: float,
    behavioral_score: float
) -> float:
    return (
        0.35 * semantic_similarity +
        0.25 * skill_match +
        0.15 * seniority_fit +
        0.15 * trajectory_score +
        0.10 * behavioral_score
    )
