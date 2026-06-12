import math
from datetime import datetime, date

SENIORITY_MAP = {"junior": 1, "mid": 2, "senior": 3, "staff": 4, "principal": 5}

CONSULTING_COMPANIES = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "hcl", "tech mahindra", "mindtree", "mphasis", "ltimindtree",
    "deloitte", "kpmg", "ey", "pwc"
}

TITLE_SENIORITY = {
    "intern": 0, "junior": 1, "associate": 1, "analyst": 1,
    "engineer": 2, "developer": 2, "designer": 2,
    "senior": 3, "lead": 3, "sr.": 3,
    "staff": 4, "principal": 4, "architect": 4,
    "manager": 3, "director": 5, "vp": 5, "head": 5,
    "cto": 6, "ceo": 6, "founder": 6
}


def compute_skill_match(jd_skills: list[str], candidate_skills: list) -> float:
    """Jaccard overlap between JD required skills and candidate skills."""
    jd_set = set(s.lower() for s in jd_skills if isinstance(s, str))
    cand_set = set(
        (s.get("name", "").lower() if isinstance(s, dict) else str(s).lower())
        for s in candidate_skills
    )
    if not jd_set:
        return 0.0
    intersection = len(jd_set & cand_set)
    union = len(jd_set | cand_set)
    return intersection / union


def compute_seniority_fit(jd_level: str, candidate_years) -> float:
    """Gaussian decay centered on expected years for JD seniority level."""
    candidate_years = float(candidate_years) if candidate_years else 0
    target_years = {1: 1, 2: 3, 3: 6, 4: 10, 5: 15}.get(
        SENIORITY_MAP.get(jd_level, 2), 3
    )
    diff = abs(candidate_years - target_years)
    return float(math.exp(-0.5 * (diff / 2) ** 2))


def _get_title_level(title: str) -> int:
    title_lower = title.lower()
    level = 1
    for keyword, lvl in TITLE_SENIORITY.items():
        if keyword in title_lower:
            level = max(level, lvl)
    return level


def compute_trajectory(career_history: list[dict]) -> float:
    """
    Career progression score (0-1). Considers:
    - Number of distinct roles
    - Title-level progression (promotions)
    - Company diversity
    - Tenure stability (penalizes extreme job-hopping)
    """
    if not career_history:
        return 0.1
    if len(career_history) == 1:
        return 0.3

    score = 0.0

    # Factor 1: Role count (30%)
    score += min(len(career_history) / 5, 1.0) * 0.3

    # Factor 2: Title progression — detect promotions (30%)
    title_levels = [_get_title_level(r.get("title", "")) for r in career_history]
    progressions = sum(
        1 for i in range(1, len(title_levels)) if title_levels[i] > title_levels[i - 1]
    )
    if len(title_levels) > 1:
        score += min(progressions / (len(title_levels) - 1), 1.0) * 0.3

    # Factor 3: Company diversity (20%)
    companies = set(r.get("company", "").lower().strip() for r in career_history)
    score += min(len(companies) / 3, 1.0) * 0.2

    # Factor 4: Tenure stability (20%)
    durations = [r.get("duration_months", 12) for r in career_history]
    avg_duration = sum(durations) / len(durations) if durations else 12
    if avg_duration >= 24:
        score += 0.2
    elif avg_duration >= 12:
        score += 0.1

    return min(round(score, 4), 1.0)


def compute_behavioral(redrob_signals: dict) -> float:
    """
    Behavioral fitness score (0-1) from 23 Redrob platform signals.
    Prioritizes signals that indicate candidate is actually reachable and hire-able.
    """
    if not redrob_signals:
        return 0.3

    score = 0.0

    # 1. Recruiter response rate (25%) — most predictive of hire-ability
    score += redrob_signals.get("recruiter_response_rate", 0) * 0.25

    # 2. Recency of activity (20%)
    last_active = redrob_signals.get("last_active_date")
    if last_active:
        try:
            last_dt = datetime.strptime(str(last_active), "%Y-%m-%d").date()
            days_ago = (date.today() - last_dt).days
            recency = max(0, 1 - (days_ago / 365))
            score += recency * 0.20
        except (ValueError, TypeError):
            score += 0.05
    else:
        score += 0.05

    # 3. Open to work flag (10%)
    if redrob_signals.get("open_to_work_flag", False):
        score += 0.10

    # 4. Interview completion rate (15%)
    score += redrob_signals.get("interview_completion_rate", 0) * 0.15

    # 5. Profile completeness (10%)
    score += (redrob_signals.get("profile_completeness_score", 0) / 100.0) * 0.10

    # 6. GitHub activity (10%) — technical credibility signal
    github = redrob_signals.get("github_activity_score", -1)
    if github >= 0:
        score += (github / 100.0) * 0.10

    # 7. Notice period — JD prefers sub-30 days (5%)
    notice = redrob_signals.get("notice_period_days", 90)
    if notice <= 30:
        score += 0.05
    elif notice <= 60:
        score += 0.03
    elif notice <= 90:
        score += 0.01

    # 8. Verification signals (5%)
    verified = 0
    if redrob_signals.get("verified_email"):
        verified += 1
    if redrob_signals.get("verified_phone"):
        verified += 1
    if redrob_signals.get("linkedin_connected"):
        verified += 1
    score += (verified / 3) * 0.05

    return min(round(score, 4), 1.0)


def detect_honeypot(candidate: dict) -> bool:
    """
    Detect subtly impossible profiles (honeypots).
    ~80 exist in the challenge dataset. >10% in top-100 = disqualification.
    """
    skills = candidate.get("skills", [])
    career_history = candidate.get("career_history", [])
    years_exp = float(candidate.get("years_exp", 0) or 0)

    # Check 1: Expert proficiency with 0 months duration
    expert_zero = sum(
        1 for s in skills
        if isinstance(s, dict)
        and s.get("proficiency") == "expert"
        and s.get("duration_months", 1) == 0
    )
    if expert_zero >= 3:
        return True

    # Check 2: Too many expert skills for low experience
    expert_count = sum(
        1 for s in skills
        if isinstance(s, dict) and s.get("proficiency") == "expert"
    )
    if expert_count >= 8 and years_exp < 5:
        return True

    # Check 3: Impossibly long single tenure
    for role in career_history:
        if isinstance(role, dict) and role.get("duration_months", 0) > 180:
            return True

    # Check 4: Total career months vastly exceeds claimed years
    total_months = sum(
        r.get("duration_months", 0) for r in career_history if isinstance(r, dict)
    )
    if years_exp > 0 and total_months > (years_exp * 12 * 1.5):
        return True

    return False


def compute_consulting_penalty(career_history: list[dict]) -> float:
    """
    Returns a multiplier (0.0–1.0). 1.0 = no penalty.
    The JD explicitly says entire-career-at-consulting is a disqualifier.
    """
    if not career_history:
        return 1.0

    consulting_roles = sum(
        1 for role in career_history
        if any(c in (role.get("company", "") or "").lower() for c in CONSULTING_COMPANIES)
    )

    ratio = consulting_roles / len(career_history)
    if ratio >= 1.0:
        return 0.3  # Entire career at consulting — heavy penalty
    elif ratio >= 0.5:
        return 0.7  # Majority consulting
    return 1.0


def compute_composite_score(
    semantic_similarity: float,
    skill_match: float,
    seniority_fit: float,
    trajectory_score: float,
    behavioral_score: float,
    honeypot: bool = False,
    consulting_penalty: float = 1.0,
) -> float:
    """
    Weighted composite score. Challenge-tuned weights:
    - Behavioral raised to 15% (challenge emphasizes availability signals)
    - Honeypots forced to 0.0
    - Consulting-only careers penalized via multiplier
    """
    if honeypot:
        return 0.0

    raw = (
        0.30 * semantic_similarity
        + 0.25 * skill_match
        + 0.15 * seniority_fit
        + 0.15 * trajectory_score
        + 0.15 * behavioral_score
    )
    return round(raw * consulting_penalty, 4)
