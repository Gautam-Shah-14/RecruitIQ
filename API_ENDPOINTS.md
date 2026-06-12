# RecruitIQ — API Endpoints Reference

> Base URL: `http://localhost:8005`  
> All protected routes require: `Authorization: Bearer auth-{user_uuid}`  
> Content-Type: `application/json`

---

## Table of Contents

1. [Health Check](#1-health-check)
2. [Authentication](#2-authentication)
3. [Jobs](#3-jobs)
4. [Candidates](#4-candidates)
5. [Search Pipeline](#5-search-pipeline)
6. [Stats](#6-stats)
7. [Error Format](#7-error-format)
8. [Flutter Integration Notes](#8-flutter-integration-notes)

---

## 1. Health Check

### `GET /health`

**Auth:** None

**Success Response (200):**
```json
{
  "status": "ok"
}
```

---

## 2. Authentication

### `POST /auth/register`

Register a new user (recruiter or candidate).

**Auth:** None

**Request Body:**
```json
{
  "email": "recruiter@example.com",
  "password": "securepassword",
  "role": "recruiter",
  "full_name": "John Doe",
  "company": "Tech Corp"
}
```

For **candidate** registration:
```json
{
  "email": "candidate@example.com",
  "password": "securepassword",
  "role": "candidate",
  "full_name": "Jane Smith",
  "headline": "ML Engineer at Google",
  "location": "Pune, India",
  "years_exp": 5.0,
  "current_title": "ML Engineer",
  "current_company": "Google",
  "domain": ["ml", "backend"],
  "skills": [
    {"name": "Python", "proficiency": "advanced", "endorsements": 10},
    {"name": "PyTorch", "proficiency": "intermediate", "endorsements": 5}
  ]
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | string | Yes | Must be unique |
| `password` | string | Yes | |
| `role` | string | Yes | `"recruiter"` or `"candidate"` |
| `full_name` | string | Yes | |
| `company` | string | No | Recruiter only |
| `headline` | string | No | Candidate only |
| `location` | string | No | Candidate only |
| `years_exp` | float | No | Candidate only, default 0.0 |
| `current_title` | string | No | Candidate only |
| `current_company` | string | No | Candidate only |
| `domain` | string[] | No | Candidate only |
| `skills` | object[] | No | Candidate only, `[{name, proficiency, endorsements}]` |

**Success Response (200):**
```json
{
  "access_token": "auth-550e8400-e29b-41d4-a716-446655440000",
  "token_type": "bearer"
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 400 | `"Invalid role. Must be 'recruiter' or 'candidate'."` |
| 400 | `"duplicate key value violates unique constraint \"users_email_key\""` |

---

### `POST /auth/login`

Authenticate an existing user.

**Auth:** None

**Request Body:**
```json
{
  "email": "recruiter@example.com",
  "password": "securepassword"
}
```

**Success Response (200):**
```json
{
  "access_token": "auth-550e8400-e29b-41d4-a716-446655440000",
  "token_type": "bearer"
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 401 | `"Invalid email or password"` |

---

### `GET /auth/me`

Get the authenticated user's profile.

**Auth:** Required

**Success Response (200) — Recruiter:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "John Doe",
  "company": "Tech Corp",
  "created_at": "2026-06-03T10:00:00+00:00",
  "role": "recruiter"
}
```

**Success Response (200) — Candidate:**
```json
{
  "id": "CAND_0000001",
  "user_id": "550e8400-...",
  "full_name": "Jane Smith",
  "headline": "ML Engineer at Google",
  "email": "candidate@example.com",
  "location": "Pune, India",
  "years_exp": 5.0,
  "current_title": "ML Engineer",
  "current_company": "Google",
  "domain": ["ml", "backend"],
  "skills": [{"name": "Python", "proficiency": "advanced", "endorsements": 10}],
  "education": [],
  "career_history": [],
  "certifications": [],
  "languages": [],
  "redrob_signals": {},
  "activity_score": 0.3,
  "trajectory_score": 0.1,
  "created_at": "2026-06-03T10:00:00+00:00",
  "role": "candidate"
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 401 | `"Invalid token"` or `"Invalid authentication credentials"` |
| 404 | `"Profile not found"` |

---

## 3. Jobs

### `POST /jobs`

Create a new job. Triggers AI parsing of the JD via Groq and generates a vector embedding.

**Auth:** Required (recruiter)

**Request Body:**
```json
{
  "title": "Senior AI/ML Engineer",
  "raw_jd": "We are looking for a Senior AI/ML Engineer with 5-9 years of experience in building production ranking and retrieval systems..."
}
```

| Field | Type | Required |
|---|---|---|
| `title` | string | Yes |
| `raw_jd` | string | Yes |

**Success Response (201):**
```json
{
  "id": "11111111-1111-1111-1111-111111111111",
  "title": "Senior AI/ML Engineer",
  "raw_jd": "We are looking for...",
  "parsed_signals": {
    "required_skills": ["Python", "PyTorch", "sentence-transformers"],
    "preferred_skills": ["Kubernetes", "LoRA"],
    "seniority_level": "senior",
    "years_exp_min": 5,
    "domain": ["ml", "backend", "search"],
    "culture_signals": ["async-first", "fast-paced"],
    "soft_skills": ["leadership", "communication"]
  },
  "created_at": "2026-06-03T10:00:00+00:00"
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 400 | Any creation error |
| 401 | Unauthorized |

---

### `GET /jobs`

List all jobs for the authenticated recruiter.

**Auth:** Required

**Success Response (200):**
```json
[
  {
    "id": "11111111-...",
    "title": "Senior AI/ML Engineer",
    "raw_jd": "...",
    "parsed_signals": { ... },
    "created_at": "2026-06-03T10:00:00+00:00"
  }
]
```

---

### `GET /jobs/{id}`

Get a single job by ID.

**Auth:** Required

**Path Params:** `id` — Job UUID

**Success Response (200):** Same shape as single item in `GET /jobs`.

**Error Responses:**

| Status | Detail |
|---|---|
| 404 | `"Job not found"` |

---

### `PUT /jobs/{id}`

Update job title and/or JD. Re-triggers AI parsing and re-embedding.

**Auth:** Required

**Request Body:** Same as `POST /jobs`.

**Success Response (200):** Same shape as `POST /jobs` response.

**Error Responses:**

| Status | Detail |
|---|---|
| 404 | `"Job not found"` |
| 400 | Any update error |

---

### `DELETE /jobs/{id}`

Delete a job.

**Auth:** Required

**Success Response (200):**
```json
{
  "detail": "Job deleted"
}
```

---

### `GET /jobs/{id}/sessions`

List all past search sessions for a specific job.

**Auth:** Required

**Success Response (200):**
```json
[
  {
    "id": "session-uuid",
    "created_at": "2026-06-03T10:05:00+00:00"
  }
]
```

---

## 4. Candidates

### `POST /candidates`

Ingest a single candidate profile. Computes embedding, trajectory score, and behavioral score.

**Auth:** Service role

**Request Body:**
```json
{
  "full_name": "Ira Vora",
  "headline": "Backend Engineer | SQL, Spark, Cloud",
  "email": "ira@example.com",
  "location": "Toronto",
  "years_exp": 6.9,
  "current_title": "Backend Engineer",
  "current_company": "Mindtree",
  "domain": ["IT Services"],
  "skills": [
    {"name": "Python", "proficiency": "advanced", "endorsements": 20, "duration_months": 48},
    {"name": "NLP", "proficiency": "advanced", "endorsements": 37, "duration_months": 26}
  ],
  "education": [
    {"institution": "LPU", "degree": "B.E.", "field_of_study": "Computer Science", "start_year": 2017, "end_year": 2020}
  ],
  "career_history": [
    {
      "company": "Mindtree", "title": "Backend Engineer",
      "start_date": "2024-03-08", "end_date": null,
      "duration_months": 27, "is_current": true,
      "industry": "IT Services", "company_size": "10001+",
      "description": "Built streaming data pipelines on Kafka and Spark..."
    }
  ],
  "certifications": [],
  "languages": [{"language": "English", "proficiency": "professional"}],
  "redrob_signals": {
    "profile_completeness_score": 86.9,
    "last_active_date": "2026-05-20",
    "open_to_work_flag": true,
    "recruiter_response_rate": 0.34,
    "interview_completion_rate": 0.71,
    "github_activity_score": 9.2,
    "notice_period_days": 60,
    "verified_email": true,
    "verified_phone": true,
    "linkedin_connected": false
  }
}
```

| Field | Type | Required |
|---|---|---|
| `full_name` | string | Yes |
| `years_exp` | float | Yes |
| `current_title` | string | Yes |
| `current_company` | string | Yes |
| `domain` | string[] | Yes |
| `skills` | object[] | Yes |
| `career_history` | object[] | Yes |
| `headline` | string | No |
| `email` | string | No |
| `location` | string | No |
| `education` | object[] | No |
| `certifications` | object[] | No |
| `languages` | object[] | No |
| `redrob_signals` | object | No |

**Success Response (200):**
```json
{
  "inserted": 1
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 400 | Validation or insert error message |

---

### `POST /candidates/bulk`

Bulk ingest an array of candidate profiles.

**Auth:** Service role

**Request Body:** Array of `CandidateCreate` objects (same shape as single `POST /candidates` body).

**Success Response (200):**
```json
{
  "inserted": 10
}
```

---

### `GET /candidates`

Fetch all candidates in the database.

**Auth:** None

**Success Response (200):**
```json
[
  {
    "id": "CAND_0000001",
    "full_name": "Ira Vora",
    "headline": "Backend Engineer | SQL, Spark, Cloud",
    "email": "CAND_0000001@example.com",
    "location": "Toronto",
    "years_exp": 6.9,
    "current_title": "Backend Engineer",
    "current_company": "Mindtree",
    "domain": ["IT Services"],
    "skills": [...],
    "education": [...],
    "career_history": [...],
    "redrob_signals": {...},
    "activity_score": 0.42,
    "trajectory_score": 0.55,
    "created_at": "2026-06-03T10:00:00+00:00"
  }
]
```

---

### `GET /candidates/{id}`

Get a single candidate's full profile.

**Path Params:** `id` — Candidate ID (e.g., `CAND_0000001` or UUID)

**Success Response (200):** Same shape as single item in `GET /candidates`.

**Error Responses:**

| Status | Detail |
|---|---|
| 404 | `"Candidate not found"` |

---

### `PUT /candidates/{id}`

Update a candidate profile. Automatically re-computes embedding, trajectory, and behavioral scores.

**Auth:** None (should be restricted in production)

**Request Body:** Same shape as `POST /candidates`.

**Success Response (200):**
```json
{
  "detail": "Candidate updated"
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 404 | `"Candidate not found"` |
| 400 | Validation error |

---

### `DELETE /candidates/{id}`

Delete a candidate profile.

**Auth:** Service role

**Success Response (200):**
```json
{
  "detail": "Candidate deleted"
}
```

---

### `GET /candidates/me/recommended_jobs`

AI-powered job recommendations for the authenticated candidate. Uses Groq to match candidate profile against all available jobs.

**Auth:** Required (candidate role only)

**Success Response (200):**
```json
[
  {
    "job_id": "11111111-...",
    "job_title": "Senior AI/ML Engineer",
    "reason": "Strong Python and ML skills match the core requirements",
    "match_score": 92
  }
]
```

**Error Responses:**

| Status | Detail |
|---|---|
| 403 | `"Only candidates can view recommended jobs"` |
| 500 | Processing error |

---

## 5. Search Pipeline

### `POST /search`

Execute the full 5-step AI search pipeline: Parse → Embed → Vector Search → Score → Re-Rank.

**Auth:** Required (recruiter)

**Request Body:**
```json
{
  "job_id": "11111111-1111-1111-1111-111111111111",
  "top_k": 20,
  "shortlist_n": 10,
  "filters": {
    "min_years_exp": 3,
    "location": "Remote",
    "domain": ["ml", "backend"]
  }
}
```

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `job_id` | UUID | Yes | | Must belong to the authenticated recruiter |
| `top_k` | int | No | 20 | Number of candidates from vector search |
| `shortlist_n` | int | No | 10 | Number of candidates to return after scoring |
| `filters` | object | No | null | Pre-filters applied at the vector search layer |
| `filters.min_years_exp` | int | No | null | Minimum years of experience |
| `filters.location` | string | No | null | Location filter |
| `filters.domain` | string[] | No | null | Domain tags filter |

**Success Response (200):**
```json
{
  "session_id": "a1b2c3d4-...",
  "job_id": "11111111-...",
  "results": [
    {
      "rank": 1,
      "candidate_id": "CAND_0000123",
      "full_name": "Jane Doe",
      "headline": "ML Eng @ OpenAI",
      "match_score": 0.9100,
      "score_breakdown": {
        "semantic_similarity": 0.88,
        "skill_match": 0.90,
        "seniority_fit": 0.85,
        "trajectory_score": 0.72,
        "behavioral_score": 0.65
      },
      "why_this_candidate": "Jane has built production ranking systems at scale with strong NLP/IR foundation.",
      "why_not_flags": []
    },
    {
      "rank": 2,
      "candidate_id": "CAND_0000456",
      "full_name": "Raj Patel",
      "headline": "Senior Search Engineer",
      "match_score": 0.8750,
      "score_breakdown": { ... },
      "why_this_candidate": "Deep experience in embeddings-based retrieval and vector databases.",
      "why_not_flags": ["Notice period is 90 days"]
    }
  ],
  "processing_time_ms": 1240
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 404 | `"Job not found"` |
| 500 | Pipeline execution error |

---

### `POST /search/{session_id}/feedback`

Submit recruiter feedback (thumbs up/down) on a search result candidate.

**Auth:** Required

**Path Params:** `session_id` — Search session UUID

**Request Body:**
```json
{
  "candidate_id": "CAND_0000123",
  "signal": "up"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `candidate_id` | string | Yes | |
| `signal` | string | Yes | `"up"` or `"down"` |

**Success Response (200):**
```json
{
  "detail": "Feedback saved"
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 404 | `"Session not found"` |

---

### `GET /search/{session_id}`

Retrieve a past search session with results and feedback.

**Auth:** Required

**Path Params:** `session_id` — Search session UUID

**Success Response (200):**
```json
{
  "id": "session-uuid",
  "recruiter_id": "recruiter-uuid",
  "job_id": "job-uuid",
  "results": [ ... ],
  "feedback": {
    "CAND_0000123": "up",
    "CAND_0000456": "down"
  },
  "created_at": "2026-06-03T10:05:00+00:00"
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 404 | `"Session not found"` |

---

## 6. Stats

### `GET /stats`

Dashboard metrics for the authenticated recruiter.

**Auth:** Required

**Success Response (200):**
```json
{
  "total_jobs": 3,
  "total_candidates": 150,
  "total_sessions": 5
}
```

**Error Responses:**

| Status | Detail |
|---|---|
| 500 | Database error |

---

## 7. Error Format

All errors follow FastAPI's default format:

```json
{
  "detail": "Human-readable error message"
}
```

Common HTTP status codes used:

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created (POST /jobs only) |
| 400 | Bad request / validation error |
| 401 | Unauthorized — invalid or missing token |
| 403 | Forbidden — wrong role |
| 404 | Resource not found |
| 500 | Internal server error |

---

## 8. Flutter Integration Notes

| Convention | Rule |
|---|---|
| Base URL | Store as `RECRUITIQ_API_URL` in Flutter config |
| Auth header | `Authorization: Bearer {access_token}` on all protected routes |
| Content-Type | `application/json` on all POST/PUT requests |
| Token storage | Persist `access_token` from login/register locally (SharedPreferences / secure storage) |
| Dates | ISO 8601 strings: `2026-06-03T10:00:00+00:00` |
| IDs | Strings in JSON — UUIDs for jobs/sessions, `CAND_XXXXXXX` for candidates |
| Pagination | Not yet implemented. `GET /candidates` returns all. Plan for `?page=1&limit=50` |
| Role-based UI | Check `role` field from `GET /auth/me` response to show recruiter vs candidate views |
| Error handling | Always parse `response.body["detail"]` for user-facing error messages |
| CORS | All origins allowed in dev. Restrict in production |

### Recommended Flutter API Service Pattern

```dart
class ApiService {
  static const String baseUrl = 'http://your-server:8005';
  String? _token;

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      _token = data['access_token'];
      return data;
    }
    throw Exception(jsonDecode(response.body)['detail']);
  }

  Future<Map<String, dynamic>> search(String jobId, {int topK = 20, int shortlistN = 10}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/search'),
      headers: _headers,
      body: jsonEncode({
        'job_id': jobId,
        'top_k': topK,
        'shortlist_n': shortlistN,
      }),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception(jsonDecode(response.body)['detail']);
  }
}
```

---

*RecruitIQ API v2.0 — Built for the Redrob Data & AI Challenge*
