# RecruitIQ — Backend Design Specification

> Intelligent Candidate Discovery & Ranking | Redrob Hackathon Edition | v2.0

---

## Table of Contents

1. [Challenge Context](#1-challenge-context)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [Environment Variables](#4-environment-variables)
5. [Database Design (PostgreSQL)](#5-database-design-postgresql)
6. [API Endpoints](#6-api-endpoints)
7. [Core AI Pipeline](#7-core-ai-pipeline)
8. [Groq Client](#8-groq-client)
9. [Pydantic Models](#9-pydantic-models)
10. [Seed Script & Challenge Data Ingestion](#10-seed-script--challenge-data-ingestion)
11. [Streamlit Frontend](#11-streamlit-frontend)
12. [Startup Order](#12-startup-order)
13. [Testing Checklist](#13-testing-checklist)
14. [Hackathon Submission Strategy](#14-hackathon-submission-strategy)

---

## 1. Challenge Context

### The Redrob Hackathon — Intelligent Candidate Discovery & Ranking

RecruitIQ is built as a solution for the **India Runs Data & AI Challenge** hosted by Redrob. The core problem:

> Given a **single Job Description** (Senior AI/ML Engineer at Redrob) and a pool of **100,000 candidate profiles** (JSONL), produce a **ranked top-100 CSV** of best-fit candidates with per-candidate reasoning.

### What Makes This Hard

The challenge is deliberately designed to punish naive keyword-matching approaches:

| Trap | Description |
|---|---|
| **Keyword Stuffers** | Candidates with perfect AI skill lists but non-technical titles (Marketing Manager, HR Manager). Their `skills` array is loaded with AI terms, but their career history is entirely non-technical. |
| **Plain-Language Tier 5s** | Genuinely strong candidates who never use buzzwords like "RAG" or "Pinecone" but whose career history shows they built recommendation/ranking systems at product companies. |
| **Behavioral Twins** | Two candidates with near-identical skill profiles — one is actively job-seeking (high response rate, recent login), the other is dormant. The active one is the better hire. |
| **Honeypots (~80)** | Subtly impossible profiles (e.g., 8 years experience at a 3-year-old company, "expert" in 10 skills with 0 months usage). >10% honeypot rate in top-100 = disqualification. |

### The JD in Brief

Redrob seeks a **Senior AI/ML Engineer (5–9 years)** to own the intelligence layer — ranking, retrieval, and matching systems. Key requirements:
- Production experience with **embeddings-based retrieval** (sentence-transformers, BGE, E5)
- Production experience with **vector databases / hybrid search** (Pinecone, Weaviate, FAISS, etc.)
- Strong Python, **evaluation frameworks** (NDCG, MRR, MAP), A/B testing
- Shipped end-to-end ranking/search/recommendation to real users
- Product-company experience preferred; pure consulting/services career is a negative signal
- Active on-platform behavioral signals matter (response rate, recency, interview completion)

### Explicit Disqualifiers from the JD
- Pure research backgrounds with no production deployment
- AI experience limited to recent (<12mo) LangChain/OpenAI wrapper projects
- Entire career at consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini)
- Primary expertise in CV/speech/robotics without NLP/IR exposure
- Senior engineers who haven't written production code in 18+ months

### Evaluation Criteria

```
Final Composite = 0.50 × NDCG@10 + 0.30 × NDCG@50 + 0.15 × MAP + 0.05 × P@10
```

Evaluation is staged:
1. **Stage 1**: Format validation (exactly 100 rows, ranks 1–100, no duplicates)
2. **Stage 2**: Automated scoring against hidden ground truth
3. **Stage 3**: Code reproduction in sandboxed Docker (16 GB RAM, CPU only, 5 min limit, no network)
4. **Stage 4**: Manual review — reasoning quality, honeypot rate check
5. **Stage 5**: Live interview — defend architecture and design choices

### Compute Constraints (Ranking Step)

| Constraint | Limit |
|---|---|
| Runtime | ≤ 5 minutes |
| Memory | ≤ 16 GB |
| Compute | CPU only (no GPU) |
| Network | No external API calls during ranking |

> Pre-computation (embeddings, indexes) can exceed these limits, but the final ranking step that produces the CSV must comply.

---

## 2. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend API | FastAPI (Python 3.11) | REST endpoints, orchestration |
| LLM / Re-ranker | Groq API (`llama3-70b-8192`) | JD parsing, explanation generation, re-ranking |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Vector encoding of JDs and profiles |
| Vector Store | ChromaDB (persistent, cosine) | Candidate embedding storage and ANN retrieval |
| Primary DB | PostgreSQL (via `psycopg2`) | Candidate profiles, jobs, sessions, auth |
| Frontend (Web) | Streamlit | Recruiter & candidate dashboard for testing |
| Frontend (Mobile) | Flutter | Cross-platform recruiter/candidate app |
| Hosting | Railway / Render | API deployment |

> **Migration Note (v1 → v2):** The original design used Supabase Auth + REST client. The current implementation uses **direct `psycopg2` connections** with a custom `users` table and SHA-256 password hashing. All Supabase references are replaced.

---

## 3. Project Structure

```
RecruitIQ-/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # pydantic-settings env loader
│   ├── dependencies.py          # Auth guard (Bearer token → user lookup)
│   │
│   ├── api/
│   │   ├── middleware.py        # CORS configuration
│   │   └── routes/
│   │       ├── auth.py          # POST /auth/register, /auth/login, GET /auth/me
│   │       ├── jobs.py          # CRUD /jobs, GET /jobs/{id}/sessions
│   │       ├── candidates.py    # CRUD /candidates, /candidates/bulk, /candidates/me/recommended_jobs
│   │       ├── search.py        # POST /search, feedback, session retrieval
│   │       └── stats.py         # GET /stats (dashboard metrics)
│   │
│   ├── core/
│   │   ├── embedder.py          # sentence-transformers wrapper
│   │   ├── vector_store.py      # ChromaDB client + CRUD
│   │   ├── groq_client.py       # Groq API wrapper (singleton)
│   │   ├── jd_parser.py         # Step 1: JD → structured signals via Groq
│   │   ├── scorer.py            # Step 4: multi-signal composite scoring
│   │   ├── reranker.py          # Step 5: LLM contextual re-ranker
│   │   └── pipeline.py          # Orchestrates search steps 1–5
│   │
│   └── db/
│       ├── database.py          # psycopg2 connection factory (RealDictCursor)
│       └── models.py            # Pydantic request/response schemas
│
├── scripts/
│   ├── init_db.py               # Creates all SQL tables + seeds dummy users/jobs
│   └── seed_candidates.py       # Ingests challenge candidates into PG + ChromaDB
│
├── India_runs_data_and_ai_challenge/
│   ├── README.docx              # Challenge overview & rules
│   ├── job_description.docx     # The target JD to rank candidates against
│   ├── submission_spec.docx     # Evaluation pipeline, format rules, compute constraints
│   ├── redrob_signals_doc.docx  # 23 behavioral signals reference
│   ├── candidate_schema.json    # JSON Schema for candidate profiles
│   ├── sample_candidates.json   # 10 sample candidate profiles (~300KB)
│   ├── candidates.jsonl         # Full 100K candidate pool (~487MB)
│   └── sample_submission.csv    # Format reference (100 rows)
│
├── API_ENDPOINTS.md             # Full API reference for Flutter integration
│
├── streamlit_app.py             # Recruiter + Candidate dual-role dashboard
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. Environment Variables

```env
# Postgres Connection (direct psycopg2)
DATABASE_URL=postgresql://postgres.your-project:your-password@aws-0-region.pooler.supabase.com:6543/postgres

# Groq
GROQ_API_KEY=gsk_your_groq_key
GROQ_MODEL=llama3-70b-8192

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION=candidates

# App
APP_ENV=development
SECRET_KEY=your-jwt-secret
ALLOWED_ORIGINS=*
```

Loaded via `pydantic-settings` in `app/config.py`:

```python
class Settings(BaseSettings):
    database_url: str
    groq_api_key: str
    groq_model: str = "llama3-70b-8192"
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "candidates"
    app_env: str = "development"
    secret_key: str = "dev-secret-key"
    allowed_origins: str = "*"
    class Config:
        env_file = ".env"
```

---

## 5. Database Design (PostgreSQL)

All tables are created via `scripts/init_db.py`. No Supabase RLS — access control is handled at the application layer.

### 5.1 Tables

#### `users`
```sql
CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL,       -- 'recruiter' | 'candidate'
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

#### `recruiter_profiles`
```sql
CREATE TABLE IF NOT EXISTS recruiter_profiles (
  id          UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  full_name   TEXT NOT NULL,
  company     TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

#### `jobs`
```sql
CREATE TABLE IF NOT EXISTS jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recruiter_id    UUID NOT NULL REFERENCES recruiter_profiles(id) ON DELETE CASCADE,
  title           TEXT NOT NULL,
  raw_jd          TEXT NOT NULL,
  parsed_signals  JSONB,
  embedding_id    TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### `candidates`

Aligned with the challenge's `candidate_schema.json` — stores the full Redrob profile structure:

```sql
CREATE TABLE IF NOT EXISTS candidates (
  id               TEXT PRIMARY KEY,            -- CAND_XXXXXXX format from challenge
  user_id          UUID REFERENCES users(id) ON DELETE CASCADE,  -- NULL for seeded candidates
  full_name        TEXT NOT NULL,
  headline         TEXT,
  email            TEXT UNIQUE,
  location         TEXT,
  years_exp        FLOAT,
  current_title    TEXT,
  current_company  TEXT,
  domain           TEXT[],
  skills           JSONB,                       -- [{name, proficiency, endorsements, duration_months}]
  education        JSONB,                       -- [{institution, degree, field_of_study, ...}]
  career_history   JSONB,                       -- [{company, title, start_date, end_date, ...}]
  certifications   JSONB,                       -- [{name, issuer, year}]
  languages        JSONB,                       -- [{language, proficiency}]
  redrob_signals   JSONB,                       -- All 23 behavioral signals
  activity_score   FLOAT DEFAULT 0,
  trajectory_score FLOAT DEFAULT 0,
  embedding_id     TEXT,
  raw_profile_text TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);
```

#### `search_sessions`
```sql
CREATE TABLE IF NOT EXISTS search_sessions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recruiter_id UUID NOT NULL REFERENCES recruiter_profiles(id),
  job_id       UUID NOT NULL REFERENCES jobs(id),
  results      JSONB,
  feedback     JSONB DEFAULT '{}',
  created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 Indexes
```sql
CREATE INDEX IF NOT EXISTS idx_candidates_domain  ON candidates USING GIN (domain);
CREATE INDEX IF NOT EXISTS idx_candidates_skills  ON candidates USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_jobs_recruiter     ON jobs (recruiter_id);
CREATE INDEX IF NOT EXISTS idx_sessions_recruiter ON search_sessions (recruiter_id);
```

---

## 6. API Endpoints

### 6.1 Auth (Dual-Role)

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/auth/register` | Create account (recruiter or candidate) | No |
| POST | `/auth/login` | Login → returns `auth-{uuid}` token | No |
| GET | `/auth/me` | Returns role-specific profile | Yes |

Auth uses a **simple prefix-token strategy**: `Authorization: Bearer auth-{user_uuid}`. The `get_current_user` dependency extracts the UUID, looks up the `users` table, and returns an `AuthUser(id, role)`.

### 6.2 Jobs

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/jobs` | Create job → triggers JD parsing + embedding | Yes |
| GET | `/jobs` | List recruiter's jobs | Yes |
| GET | `/jobs/{id}` | Get single job with parsed signals | Yes |
| PUT | `/jobs/{id}` | Update job → re-parses JD | Yes |
| DELETE | `/jobs/{id}` | Delete job | Yes |
| GET | `/jobs/{id}/sessions` | List search sessions for a job | Yes |

### 6.3 Candidates

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/candidates` | Ingest single candidate | Service Key |
| POST | `/candidates/bulk` | Bulk ingest from JSON array | Service Key |
| GET | `/candidates` | List all candidates | No |
| GET | `/candidates/{id}` | Get full candidate profile | No |
| PUT | `/candidates/{id}` | Update candidate (re-embeds) | No |
| DELETE | `/candidates/{id}` | Delete candidate | Service Key |
| GET | `/candidates/me/recommended_jobs` | AI-powered job recommendations for candidates | Yes (candidate) |

### 6.4 Search (Core Endpoint)

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/search` | Run 5-step AI pipeline → ranked shortlist | Yes |
| POST | `/search/{session_id}/feedback` | Submit thumbs up/down | Yes |
| GET | `/search/{session_id}` | Get session results + feedback | Yes |

### 6.5 Stats

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/stats` | Dashboard metrics (jobs, candidates, sessions count) | Yes |

---

## 7. Core AI Pipeline

Orchestrated in `app/core/pipeline.py`, called by `POST /search`:

```
POST /search
    │
    ▼
Step 1: jd_parser.py      ← Groq extracts structured signals from JD
    │
    ▼
Step 2: embedder.py        ← Encode JD into a 384-dim vector (all-MiniLM-L6-v2)
    │
    ▼
Step 3: vector_store.py    ← ChromaDB ANN cosine search → top-K candidates
    │
    ▼
Step 4: scorer.py          ← Multi-signal composite scoring (5 weighted signals)
    │
    ▼
Step 5: reranker.py        ← Groq contextual re-rank + explanation generation
    │
    ▼
    Return SearchResponse
```

### Step 1 — JD Parser (`app/core/jd_parser.py`)

Extracts structured hiring signals via Groq LLM:

```json
{
  "required_skills": [],
  "preferred_skills": [],
  "seniority_level": "junior|mid|senior|staff|principal",
  "years_exp_min": 0,
  "domain": [],
  "culture_signals": [],
  "soft_skills": []
}
```

- `temperature=0` for deterministic output
- Retry once on JSON parse failure, then return `None`

### Step 2 — Embedder (`app/core/embedder.py`)

- **Model:** `all-MiniLM-L6-v2` (384-dim, runs locally)
- **JD text:** `"{title}. {raw_jd} Required skills: {skills}"`
- **Candidate text:** Concatenation of title, company, skills, domain, experience years, and last 2 career roles
- Candidates are embedded **once on ingest**; JDs embedded on job creation

### Step 3 — Vector Store (`app/core/vector_store.py`)

ChromaDB with `cosine` similarity space. Supports metadata pre-filtering on `years_exp`.

```python
similarity = 1 - (distance / 2)  # Convert cosine distance → similarity
```

### Step 4 — Multi-Signal Scorer (`app/core/scorer.py`)

| Signal | Weight | How Computed |
|---|---|---|
| `semantic_similarity` | 30% | `1 - (chroma_distance / 2)` |
| `skill_match` | 25% | Jaccard overlap (JD required skills ∩ candidate skills) |
| `seniority_fit` | 15% | Gaussian decay centered on JD seniority level |
| `trajectory_score` | 15% | Career progression: role count, title-level promotions, company diversity, tenure stability |
| `behavioral_score` | 15% | Computed from 23 Redrob signals: response rate (25%), activity recency (20%), interview completion (15%), open-to-work (10%), profile completeness (10%), GitHub (10%), notice period (5%), verification (5%) |

**Challenge-specific modifiers:**
- **Honeypot detection:** Candidates with impossible profiles (expert skills with 0 months, impossible tenures) are scored 0.0
- **Consulting penalty:** Entire-career-at-consulting candidates get a 0.3× multiplier; majority-consulting gets 0.7×

**Composite:** `(0.30×sem + 0.25×skill + 0.15×sen + 0.15×traj + 0.15×behav) × consulting_penalty`

### Step 5 — LLM Re-ranker (`app/core/reranker.py`)

Sends top-N scored candidates to Groq for contextual re-ranking. Returns:
```json
[{
  "candidate_id": "uuid",
  "why_this_candidate": "One sentence explanation",
  "why_not_flags": ["Any concern"]
}]
```
- `temperature=0.2` for slight creativity
- Falls back to scorer order if Groq fails

---

## 8. Groq Client (`app/core/groq_client.py`)

Singleton wrapper with automatic retry (2 attempts, 1s backoff):

```python
groq_client = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
```

> **Rate limit:** Groq free tier ≈ 30 req/min on `llama3-70b-8192`. The search flow makes 2 calls (JD parse + re-rank).

---

## 9. Pydantic Models (`app/db/models.py`)

Key models reflecting the **implemented** state (not the v1 design):

- **`RegisterRequest`** — supports `role` field (`recruiter` | `candidate`) with optional candidate-specific fields
- **`CandidateCreate`** — includes `certifications`, `languages`, `redrob_signals` (aligned with challenge schema)
- **`CandidateUpdate`** — all fields optional for partial updates
- **`SearchRequest`** — `job_id`, `top_k`, `shortlist_n`, optional `SearchFilters`
- **`SearchResponse`** — session_id, job_id, ranked results with `ScoreBreakdown`, processing time
- **`StatsResponse`** — total_jobs, total_candidates, total_sessions

---

## 10. Seed Script & Challenge Data Ingestion

### `scripts/init_db.py`
Creates all tables and seeds 3 dummy recruiter users + 3 dummy jobs. Calls `seed_candidates.py` automatically.

### `scripts/seed_candidates.py`
Ingests candidates from `India_runs_data_and_ai_challenge/sample_candidates.json`:

1. Reads the challenge-format JSON (Redrob schema)
2. Maps challenge fields → internal schema (e.g., `profile.current_title` → `current_title`)
3. Computes embeddings using `get_candidate_embedding()`
4. Inserts into PostgreSQL with `ON CONFLICT (id) DO UPDATE`
5. Adds embeddings + metadata to ChromaDB

> For the full 100K pool, use `candidates.jsonl` (one JSON object per line, ~487MB).

---

## 11. Streamlit Frontend (`streamlit_app.py`)

Dual-role dashboard at `http://localhost:8501`:

### Candidate View
- **My Profile** — Edit name, title, skills, education, career history
- **Find Matching Jobs** — AI-powered job recommendations via Groq

### Recruiter View
- **Dashboard Stats** — Total jobs, candidates, search sessions
- **Manage Jobs** — Create/view jobs with AI-parsed signals
- **Candidate Database** — Browse all candidates
- **Run AI Search** — Execute the 5-step pipeline with configurable filters

---

## 12. Startup Order

```bash
# 1. Configure environment
copy .env.example .env    # Fill DATABASE_URL, GROQ_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database + seed data
python scripts/init_db.py

# 4. Start FastAPI
uvicorn app.main:app --reload --port 8005

# 5. Start Streamlit (optional)
streamlit run streamlit_app.py

# 6. Verify
# API docs: http://localhost:8005/docs
# Streamlit: http://localhost:8501
```

---

## 13. Testing Checklist

| Test | Expected Result |
|---|---|
| `POST /auth/register` (recruiter) → `POST /auth/login` | Returns `auth-{uuid}` token |
| `POST /auth/register` (candidate) | Creates user + candidate profile |
| `POST /jobs` with real JD text | `parsed_signals` JSONB populated |
| `GET /candidates` | Returns all seeded candidates |
| `PUT /candidates/{id}` | Updates profile, re-computes embedding |
| `POST /search` with valid `job_id` | Returns ranked results with score breakdowns |
| `GET /candidates/me/recommended_jobs` (as candidate) | Returns top-3 job matches |
| `POST /search/{session_id}/feedback` | Feedback stored in session |
| Invalid token → any protected route | Returns `401 Unauthorized` |

---

## 14. Hackathon Submission Strategy

### What the Challenge Expects

A `submission.csv` with exactly 100 rows:

```csv
candidate_id,rank,score,reasoning
CAND_0001234,1,0.9500,Senior ML engineer with 7 years production experience in ranking systems...
CAND_0002345,2,0.9200,...
...
```

### Key Ranking Signals to Leverage

| Signal Category | What to Extract | Weight Recommendation |
|---|---|---|
| **Career Narrative** | Product-company experience in search/ranking/recommendation | High |
| **Skill Depth** | Embeddings, vector DBs, Python — with `duration_months` > 12 | High |
| **Seniority Band** | 5–9 years total, 4–5 in applied ML/AI | High |
| **Behavioral Fitness** | `recruiter_response_rate`, `last_active_date`, `open_to_work_flag` | Medium |
| **Anti-patterns** | Consulting-only career, keyword-stuffing, impossible profiles | Disqualify |
| **Education Tier** | `tier_1` / `tier_2` institutions (tiebreaker) | Low |

### Honeypot Detection Strategy

Check for impossible profiles:
- `years_of_experience` > company founding plausibility
- Skills with `proficiency: "expert"` but `duration_months: 0`
- Skill assessment scores that contradict proficiency levels
- Career history dates that overlap impossibly

### Redrob Behavioral Signals (23 total)

Key signals for candidate availability/quality:
- `profile_completeness_score` (0–100) — higher = more serious candidate
- `last_active_date` — recency of platform activity
- `open_to_work_flag` — boolean intent signal
- `recruiter_response_rate` (0–1) — actual engagement rate
- `avg_response_time_hours` — responsiveness
- `interview_completion_rate` (0–1) — follow-through
- `offer_acceptance_rate` (-1 to 1) — hiring track record
- `github_activity_score` (-1 to 100) — technical activity (-1 = no GitHub)
- `notice_period_days` (0–180) — sub-30 preferred by JD
- `skill_assessment_scores` — platform-verified skill levels
- `verified_email`, `verified_phone`, `linkedin_connected` — trust signals

### Submission Rules

- Exactly 100 rows, ranks 1–100
- Scores must be monotonically decreasing with rank
- No duplicate `candidate_id` values
- All `candidate_id` values must exist in `candidates.jsonl`
- Max 3 submissions; last valid one counts
- Reasoning should be specific and honest (no templates, no hallucinated skills)

---

*RecruitIQ — Built for the Redrob Data & AI Challenge: Intelligent Candidate Discovery & Ranking*