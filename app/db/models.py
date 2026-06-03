from pydantic import BaseModel, UUID4
from typing import Optional
import uuid

# ── Auth ────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str # 'recruiter' or 'candidate'
    full_name: str
    
    # Recruiter fields
    company: Optional[str] = None
    
    # Candidate fields
    headline: Optional[str] = None
    location: Optional[str] = None
    years_exp: Optional[int] = 0
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    domain: Optional[list[str]] = []
    skills: Optional[list[str]] = []

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ── Jobs ─────────────────────────────────────────
class JobCreate(BaseModel):
    title: str
    raw_jd: str

class JobUpdate(BaseModel):
    title: Optional[str] = None
    raw_jd: Optional[str] = None

class JobResponse(BaseModel):
    id: UUID4
    title: str
    raw_jd: str
    parsed_signals: Optional[dict] = None
    created_at: str

# ── Candidates ───────────────────────────────────
class EducationEntry(BaseModel):
    degree: str
    field: str
    school: str
    year: Optional[int] = None

class CareerEntry(BaseModel):
    title: str
    company: str
    start: str          # "2020-01"
    end: Optional[str]  # None = current role
    desc: str

class BehavioralSignals(BaseModel):
    github_repos:  int = 0
    oss_commits:   int = 0
    talks:         int = 0
    articles:      int = 0
    last_active:   Optional[str] = None  # ISO date

class CandidateCreate(BaseModel):
    full_name:       str
    headline:        Optional[str] = None
    email:           Optional[str] = None
    location:        Optional[str] = None
    years_exp:       int
    current_title:   str
    current_company: str
    domain:          list[str]
    skills:          list[str]
    education:       list[EducationEntry] = []
    career_history:  list[CareerEntry]
    behavioral:      BehavioralSignals = BehavioralSignals()

class CandidateUpdate(BaseModel):
    full_name:       Optional[str] = None
    headline:        Optional[str] = None
    email:           Optional[str] = None
    location:        Optional[str] = None
    years_exp:       Optional[int] = None
    current_title:   Optional[str] = None
    current_company: Optional[str] = None
    domain:          Optional[list[str]] = None
    skills:          Optional[list[str]] = None
    education:       Optional[list[EducationEntry]] = None
    career_history:  Optional[list[CareerEntry]] = None
    behavioral:      Optional[BehavioralSignals] = None

# ── Search ───────────────────────────────────────
class SearchFilters(BaseModel):
    min_years_exp: Optional[int] = None
    location:      Optional[str] = None
    domain:        Optional[list[str]] = None

class SearchRequest(BaseModel):
    job_id:      UUID4
    top_k:       int = 20
    shortlist_n: int = 10
    filters:     Optional[SearchFilters] = None

class ScoreBreakdown(BaseModel):
    semantic_similarity: float
    skill_match:         float
    seniority_fit:       float
    trajectory_score:    float
    behavioral_score:    float

class CandidateResult(BaseModel):
    rank:                int
    candidate_id:        UUID4
    full_name:           str
    headline:            Optional[str]
    match_score:         float
    score_breakdown:     ScoreBreakdown
    why_this_candidate:  str
    why_not_flags:       list[str]

class SearchResponse(BaseModel):
    session_id:          UUID4
    job_id:              UUID4
    results:             list[CandidateResult]
    processing_time_ms:  int

# ── Feedback ─────────────────────────────────────
class FeedbackRequest(BaseModel):
    candidate_id: UUID4
    signal:       str  # "up" | "down"

# ── Stats ────────────────────────────────────────
class StatsResponse(BaseModel):
    total_jobs: int
    total_candidates: int
    total_sessions: int
