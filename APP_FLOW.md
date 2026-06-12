# RecruitIQ — Flutter App Flow & Screen Guide

> A complete reference for the Flutter developer building the RecruitIQ mobile app.  
> Base API URL: `http://<server>:8005`

---

## Table of Contents

1. [App Architecture](#1-app-architecture)
2. [Navigation Map](#2-navigation-map)
3. [Auth Flow (Shared)](#3-auth-flow-shared)
4. [Recruiter Flow — Screens](#4-recruiter-flow--screens)
5. [Candidate Flow — Screens](#5-candidate-flow--screens)
6. [State Management Notes](#6-state-management-notes)
7. [Token & Session Handling](#7-token--session-handling)
8. [Screen Summary Table](#8-screen-summary-table)

---

## 1. App Architecture

### Dual-Role App

RecruitIQ is a **single app with two distinct experiences** based on the user's role:

- **Recruiter** — Creates job descriptions, runs AI-powered candidate searches, reviews ranked results, and provides feedback.
- **Candidate** — Manages their profile, views AI-generated job recommendations, and keeps their information up to date.

The role is determined at registration and returned by `GET /auth/me`. After login, the app routes the user to the appropriate home screen.

### API Communication Pattern

```
Flutter App
    │
    ├── Store token in secure storage after login/register
    ├── Attach "Authorization: Bearer {token}" to all protected requests
    ├── All requests/responses are JSON
    └── Parse "detail" field on error responses for user-facing messages
```

---

## 2. Navigation Map

### Overall Flow

```
App Launch
    │
    ▼
[Splash Screen] ──(has saved token?)──► [Check /auth/me]
    │                                        │
    │ (no token)                    (valid)   │   (401 = expired)
    ▼                                 │       │       │
[Login/Register Screen]               ▼       │       ▼
    │                          Check role      │   Clear token
    │                              │           │   Go to Login
    │◄─────────────────────────────┘           │
    │                                          │
    ├── role == "recruiter" ──► [Recruiter Home]
    │                                │
    │                                ├── Dashboard Tab
    │                                ├── Jobs Tab
    │                                ├── Candidates Tab
    │                                └── Search Tab
    │
    └── role == "candidate" ──► [Candidate Home]
                                     │
                                     ├── My Profile Tab
                                     └── Job Matches Tab
```

### Recruiter Navigation (Deep)

```
Recruiter Home (Bottom Nav: Dashboard | Jobs | Candidates | Search)
    │
    ├── Dashboard Tab
    │       └── Stats cards (jobs count, candidates count, sessions count)
    │
    ├── Jobs Tab
    │       ├── Job List
    │       │     └── Tap job ──► Job Detail Screen
    │       │                         ├── View parsed signals
    │       │                         ├── Edit Job button ──► Edit Job Screen
    │       │                         ├── Delete Job button
    │       │                         └── View Past Sessions ──► Session List
    │       │                                                      └── Tap ──► Session Detail
    │       └── FAB (+) ──► Create Job Screen
    │
    ├── Candidates Tab
    │       ├── Candidate List (scrollable, paginated)
    │       └── Tap candidate ──► Candidate Detail Screen
    │
    └── Search Tab
            ├── Select Job dropdown
            ├── Set filters (min experience)
            ├── "Run AI Search" button
            └── Results ──► Search Results Screen
                              ├── Ranked candidate cards
                              ├── Tap card ──► Candidate Detail Screen
                              └── Thumbs up/down buttons per card
```

### Candidate Navigation (Deep)

```
Candidate Home (Bottom Nav: Profile | Job Matches)
    │
    ├── Profile Tab
    │       ├── View current profile info
    │       └── "Edit Profile" button ──► Edit Profile Screen
    │               ├── Personal info fields
    │               ├── Skills editor
    │               ├── Education editor
    │               ├── Career history editor
    │               └── Save button
    │
    └── Job Matches Tab
            ├── "Find Matching Jobs" button
            └── Recommendation cards
                    ├── Job title, match score, reason
                    └── (Optional) Tap ──► Job Detail Preview
```

---

## 3. Auth Flow (Shared)

### Screen 1: Splash Screen

**Purpose:** Check for existing session on app launch.

**Logic:**
1. Check secure storage for saved `access_token`
2. If token exists → call `GET /auth/me`
   - **200 OK** → Read `role` from response → navigate to Recruiter Home or Candidate Home
   - **401/error** → Clear token → navigate to Login Screen
3. If no token → navigate to Login Screen

**UI Elements:**
- App logo/branding
- Loading spinner

---

### Screen 2: Login Screen

**Purpose:** Authenticate existing users.

**API Call:** `POST /auth/login`

**UI Elements:**
- Email text field
- Password text field (obscured)
- "Login" button
- "Don't have an account? Register" link → navigates to Register Screen

**Flow on "Login" tap:**
```
1. POST /auth/login
   Body: { "email": "...", "password": "..." }

2. On 200:
   - Save response.access_token to secure storage
   - Call GET /auth/me with the token
   - Read role from response
   - Save user profile data to app state
   - Navigate to Recruiter Home or Candidate Home based on role

3. On 401:
   - Show SnackBar: "Invalid email or password"

4. On other error:
   - Show SnackBar with response.detail
```

---

### Screen 3: Register Screen

**Purpose:** Create a new account. Form adapts based on selected role.

**API Call:** `POST /auth/register`

**UI Elements — Common:**
- Role selector (toggle/dropdown: Recruiter | Candidate)
- Email text field
- Password text field
- Full Name text field

**UI Elements — Recruiter-specific (show when role = "recruiter"):**
- Company text field

**UI Elements — Candidate-specific (show when role = "candidate"):**
- Headline text field
- Current Title text field
- Current Company text field
- Years of Experience number field
- Domain chips input (comma-separated → array)
- Skills input (add skill name, proficiency dropdown)

**Flow on "Register" tap:**
```
1. Build payload based on role:

   Recruiter:
   {
     "email": "...", "password": "...", "role": "recruiter",
     "full_name": "...", "company": "..."
   }

   Candidate:
   {
     "email": "...", "password": "...", "role": "candidate",
     "full_name": "...", "headline": "...",
     "current_title": "...", "current_company": "...",
     "years_exp": 5.0,
     "domain": ["ml", "backend"],
     "skills": [{"name": "Python", "proficiency": "advanced", "endorsements": 0}]
   }

2. POST /auth/register

3. On 200:
   - Save response.access_token to secure storage
   - Call GET /auth/me
   - Navigate to appropriate home screen
   - Show success toast: "Account created!"

4. On 400:
   - Show error (likely duplicate email): response.detail
```

---

## 4. Recruiter Flow — Screens

### Screen 4: Recruiter Home (Shell with Bottom Navigation)

**Tabs:** Dashboard | Jobs | Candidates | Search

This is a scaffold with a `BottomNavigationBar`. Each tab loads its own screen content.

---

### Screen 5: Dashboard Tab

**Purpose:** At-a-glance stats overview.

**API Call:** `GET /stats`

**When to call:** On tab focus / pull-to-refresh.

**UI Elements:**
- Three metric cards in a row:
  - 💼 **Total Jobs** — `response.total_jobs`
  - 👥 **Total Candidates** — `response.total_candidates`
  - 🔍 **Search Sessions** — `response.total_sessions`
- Pull-to-refresh gesture

**Response shape:**
```json
{ "total_jobs": 3, "total_candidates": 150, "total_sessions": 5 }
```

---

### Screen 6: Jobs Tab (Job List)

**Purpose:** View and manage all recruiter's jobs.

**API Call:** `GET /jobs`

**UI Elements:**
- List of job cards, each showing:
  - Job title (bold)
  - Created date (formatted)
  - Chip showing seniority from `parsed_signals.seniority_level` (if available)
  - Required skills as small chips (first 3-4 from `parsed_signals.required_skills`)
- Floating Action Button (+) → navigates to Create Job Screen
- Tap on a job card → navigates to Job Detail Screen
- Empty state: "No jobs yet. Create your first job description!"

---

### Screen 7: Create Job Screen

**Purpose:** Create a new job description. The backend parses it with AI and extracts structured signals.

**API Call:** `POST /jobs`

**UI Elements:**
- "Job Title" text field
- "Job Description" multi-line text area (large, at least 6 lines)
- "Create Job" button with loading state
- Back button in app bar

**Flow:**
```
1. User fills in title and raw_jd

2. Tap "Create Job"
   - Show loading spinner (AI parsing takes 2-5 seconds)
   - POST /jobs { "title": "...", "raw_jd": "..." }

3. On 201:
   - Navigate back to Jobs Tab
   - Show success toast: "Job created and parsed by AI!"
   - Jobs list refreshes automatically

4. On error:
   - Show error SnackBar
```

---

### Screen 8: Job Detail Screen

**Purpose:** View a job with its AI-parsed signals, and access actions.

**API Call:** `GET /jobs/{id}` (if not already loaded from list)

**UI Elements:**
- **Header section:**
  - Job title (large text)
  - Created date
- **Raw JD section:**
  - Expandable card showing the full job description text
- **Parsed Signals section** (the AI output):
  - Required Skills — displayed as colored chips
  - Preferred Skills — displayed as outlined chips
  - Seniority Level — badge (e.g., "Senior")
  - Min Years Experience — text
  - Domain Tags — chips
  - Culture Signals — chips
  - Soft Skills — chips
- **Actions:**
  - "Run AI Search" button → navigates to Search Tab with this job pre-selected
  - "Edit" icon button → navigates to Edit Job Screen
  - "View Past Sessions" → navigates to Session List Screen
  - "Delete" icon button → confirmation dialog → `DELETE /jobs/{id}`

---

### Screen 9: Edit Job Screen

**Purpose:** Update a job's title and description. Re-triggers AI parsing.

**API Call:** `PUT /jobs/{id}`

**UI Elements:** Same as Create Job Screen, but pre-filled with existing values.

**Flow:** Same as Create Job, but uses PUT instead of POST.

---

### Screen 10: Candidates Tab (Candidate List)

**Purpose:** Browse all candidates in the database.

**API Call:** `GET /candidates`

**UI Elements:**
- Search bar (client-side filter by name/title/skills)
- Scrollable list of candidate cards, each showing:
  - Full name (bold)
  - Headline
  - Current title @ Current company
  - Years of experience
  - Activity score as a small progress indicator
  - Top 3 skill names as chips
- Tap on candidate → navigates to Candidate Detail Screen
- Empty state if no candidates

> **Note:** `GET /candidates` returns all candidates. For large datasets, implement client-side pagination (show 20 at a time with "Load More" button).

---

### Screen 11: Search Tab

**Purpose:** Run the AI-powered search pipeline against a selected job.

**API Calls:**
1. `GET /jobs` — to populate the job selector dropdown
2. `POST /search` — to execute the pipeline

**UI Elements:**
- **Job Selector:** Dropdown populated from `GET /jobs`. Each option shows `"title (id)"`.
- **Filters section:**
  - "Min Years Experience" number input (optional)
- **Advanced settings** (collapsible):
  - `top_k` slider (5–50, default 20) — how many candidates to retrieve from vector search
  - `shortlist_n` slider (3–20, default 10) — how many to return after scoring
- **"Run AI Search" button** — large, prominent, with loading animation
- After search completes → navigates to Search Results Screen

**Flow:**
```
1. User selects a job and optionally sets filters

2. Tap "Run AI Search"
   - Show full-screen loading with animated text:
     "Step 1: Parsing job description..."
     "Step 2: Encoding with AI..."
     "Step 3: Searching vector database..."
     "Step 4: Scoring candidates..."
     "Step 5: AI re-ranking..."
   
   POST /search
   {
     "job_id": "selected-uuid",
     "top_k": 20,
     "shortlist_n": 10,
     "filters": { "min_years_exp": 3 }
   }

3. On 200:
   - Navigate to Search Results Screen with response data
   - Show processing time: "Completed in {processing_time_ms}ms"

4. On 404:
   - "Job not found" error

5. On 500:
   - "Search failed. Please try again."
```

---

### Screen 12: Search Results Screen

**Purpose:** Display AI-ranked candidates with scores, explanations, and feedback buttons.

**Data:** Passed from Search Tab (the `POST /search` response).

**API Call:** `POST /search/{session_id}/feedback` — when recruiter taps thumbs up/down.

**UI Elements:**
- **Header:**
  - "Search Results" title
  - Session ID (small text)
  - Processing time badge
- **Results list** — ordered by rank. Each card contains:
  - **Rank badge** (#1, #2, etc.) with gradient color (gold→silver→bronze for top 3)
  - **Candidate name** (bold) + headline
  - **Match score** — large, prominent (e.g., "91.00%") with a circular progress indicator
  - **"Why this candidate"** — the AI-generated explanation text
  - **"Flags"** — if `why_not_flags` is non-empty, show as warning chips
  - **Score breakdown** — expandable section with 5 mini progress bars:
    - Semantic Similarity: `score_breakdown.semantic_similarity`
    - Skill Match: `score_breakdown.skill_match`
    - Seniority Fit: `score_breakdown.seniority_fit`
    - Trajectory: `score_breakdown.trajectory_score`
    - Behavioral: `score_breakdown.behavioral_score`
  - **Feedback row:** 👍 and 👎 icon buttons
  - **Tap on card** → navigates to Candidate Detail Screen

**Feedback flow:**
```
User taps 👍 on candidate CAND_0000123:

POST /search/{session_id}/feedback
{
  "candidate_id": "CAND_0000123",
  "signal": "up"
}

On 200: 
  - Change button to filled/highlighted state
  - Show subtle confirmation animation

On error:
  - Show SnackBar with error
```

---

### Screen 13: Candidate Detail Screen

**Purpose:** Full profile view of a single candidate.

**API Call:** `GET /candidates/{id}`

**UI Elements:**
- **Profile header:**
  - Full name (large)
  - Headline
  - Location
  - Years of experience badge
  - Activity score indicator (colored dot: green/yellow/red)
- **Skills section:**
  - Chips for each skill showing name + proficiency level (color-coded: expert=green, advanced=blue, intermediate=yellow, beginner=grey)
  - Endorsement count per skill
- **Career History section:**
  - Timeline view of roles:
    - Title @ Company
    - Date range + duration
    - Industry badge
    - Description (expandable)
- **Education section:**
  - Institution, degree, field of study
  - Year range
  - Tier badge (tier_1, tier_2, etc.)
- **Certifications section:**
  - Name, issuer, year
- **Languages section:**
  - Language + proficiency level
- **Redrob Signals section** (collapsible "Platform Activity"):
  - Profile completeness bar
  - Open to work indicator
  - Recruiter response rate
  - Last active date
  - GitHub activity score
  - Notice period
  - Verification badges (email ✓, phone ✓, LinkedIn ✓)

---

### Screen 14: Session List Screen

**Purpose:** View past AI search sessions for a specific job.

**API Call:** `GET /jobs/{id}/sessions`

**UI Elements:**
- List of sessions, each showing:
  - Session date/time (formatted)
  - Session ID (truncated)
- Tap on session → navigates to Session Detail Screen

---

### Screen 15: Session Detail Screen

**Purpose:** Revisit a past search session's results and feedback.

**API Call:** `GET /search/{session_id}`

**UI Elements:** Same layout as Search Results Screen (Screen 12), but:
- Results loaded from `response.results` (stored JSON)
- Feedback state loaded from `response.feedback` object
- Feedback buttons reflect saved state (pre-highlighted if already voted)

---

## 5. Candidate Flow — Screens

### Screen 16: Candidate Home (Shell with Bottom Navigation)

**Tabs:** Profile | Job Matches

---

### Screen 17: Profile Tab

**Purpose:** View current profile information.

**Data:** Loaded from `GET /auth/me` response (stored in app state at login).

**UI Elements:**
- Profile card at top:
  - Name, headline, title @ company
  - Location, years of experience
- Skills chips with proficiency badges
- Career history timeline (read-only)
- Education cards
- "Edit Profile" button → navigates to Edit Profile Screen

---

### Screen 18: Edit Profile Screen

**Purpose:** Update candidate's profile. Backend re-computes embeddings and scores on save.

**API Call:** `PUT /candidates/{candidate_id}`

**UI Elements:**
- **Personal Info section:**
  - Full Name text field
  - Headline text field
  - Current Title text field
  - Current Company text field
  - Location text field
  - Years of Experience number field
- **Domain section:**
  - Chips input — add/remove domain tags
- **Skills section:**
  - List of skill entries, each with:
    - Skill name text field
    - Proficiency dropdown (beginner/intermediate/advanced/expert)
    - "Remove" button
  - "Add Skill" button
- **Education section:**
  - List of education entries, each with:
    - Institution, degree, field of study text fields
    - Start year / End year number fields
  - "Add Education" button
- **Career History section:**
  - List of career entries, each with:
    - Company, title text fields
    - Start date, end date date pickers
    - Description multi-line text area
    - "Is Current" toggle
  - "Add Role" button
- **Save button** (fixed at bottom)

**Flow:**
```
1. User edits fields

2. Tap "Save"
   - Build the full CandidateCreate payload:
   {
     "full_name": "...",
     "headline": "...",
     "email": "user@email.com",
     "location": "...",
     "years_exp": 6.5,
     "current_title": "...",
     "current_company": "...",
     "domain": ["ml", "backend"],
     "skills": [
       {"name": "Python", "proficiency": "advanced", "endorsements": 0, "duration_months": 48}
     ],
     "education": [...],
     "career_history": [
       {
         "company": "...", "title": "...",
         "start_date": "2022-01-01", "end_date": null,
         "duration_months": 30, "is_current": true,
         "industry": "...", "company_size": "51-200",
         "description": "..."
       }
     ],
     "certifications": [...],
     "languages": [...],
     "redrob_signals": { ...preserve existing signals... }
   }

   PUT /candidates/{id}

3. On 200:
   - Show success toast: "Profile updated! Your search ranking has been recalculated."
   - Refresh /auth/me data in app state
   - Navigate back to Profile Tab

4. On error:
   - Show validation error
```

> **Important:** When saving, preserve the existing `redrob_signals`, `certifications`, and `languages` from the original profile data. The PUT endpoint expects the full object, not a partial patch.

---

### Screen 19: Job Matches Tab

**Purpose:** View AI-generated job recommendations based on the candidate's profile.

**API Call:** `GET /candidates/me/recommended_jobs`

**UI Elements:**
- "Find Matching Jobs" button (or auto-load on tab focus)
- Loading state with AI animation
- List of recommendation cards (typically 3), each showing:
  - **Job title** (large, bold)
  - **Match score** — percentage with circular indicator
  - **Reason** — AI-generated explanation of why this job fits
- Empty state: "No matching jobs found. Update your profile to improve recommendations."

**Flow:**
```
1. Tap "Find Matching Jobs" or auto-load

2. GET /candidates/me/recommended_jobs
   (loading state: "Analyzing your profile against open roles...")

3. On 200:
   Response:
   [
     {
       "job_id": "uuid",
       "job_title": "Senior AI/ML Engineer",
       "reason": "Strong Python and ML skills match core requirements",
       "match_score": 92
     }
   ]
   
   Display recommendation cards.

4. On 403:
   - "Only candidates can view this" (shouldn't happen if role-gating is correct)

5. On 500:
   - "Failed to generate recommendations. Try again later."
```

---

## 6. State Management Notes

### Recommended Approach

Use **Riverpod** or **Provider** for state management:

```
AuthProvider
  ├── token: String?
  ├── user: UserProfile?
  ├── role: String? ("recruiter" | "candidate")
  ├── isLoggedIn: bool
  ├── login(email, password) → Future
  ├── register(payload) → Future
  └── logout()

JobsProvider (recruiter only)
  ├── jobs: List<Job>
  ├── fetchJobs() → Future
  ├── createJob(title, rawJd) → Future
  ├── updateJob(id, title, rawJd) → Future
  └── deleteJob(id) → Future

CandidatesProvider
  ├── candidates: List<Candidate>
  ├── fetchCandidates() → Future
  └── getCandidate(id) → Future<Candidate>

SearchProvider (recruiter only)
  ├── isSearching: bool
  ├── lastResults: SearchResponse?
  ├── runSearch(jobId, topK, shortlistN, filters) → Future
  └── submitFeedback(sessionId, candidateId, signal) → Future

StatsProvider (recruiter only)
  ├── stats: StatsResponse?
  └── fetchStats() → Future

ProfileProvider (candidate only)
  ├── profile: CandidateProfile?
  ├── recommendations: List<JobRecommendation>
  ├── updateProfile(payload) → Future
  └── fetchRecommendations() → Future
```

---

## 7. Token & Session Handling

### Token Storage

```dart
// Use flutter_secure_storage
final storage = FlutterSecureStorage();

// After login/register:
await storage.write(key: 'access_token', value: token);

// On app launch:
final token = await storage.read(key: 'access_token');

// On logout:
await storage.delete(key: 'access_token');
```

### API Interceptor Pattern

```dart
class ApiClient {
  final String baseUrl;
  String? _token;

  ApiClient(this.baseUrl);

  void setToken(String token) => _token = token;
  void clearToken() => _token = null;

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  Future<dynamic> get(String endpoint) async {
    final res = await http.get(Uri.parse('$baseUrl$endpoint'), headers: _headers);
    return _handleResponse(res);
  }

  Future<dynamic> post(String endpoint, Map<String, dynamic> body) async {
    final res = await http.post(
      Uri.parse('$baseUrl$endpoint'),
      headers: _headers,
      body: jsonEncode(body),
    );
    return _handleResponse(res);
  }

  Future<dynamic> put(String endpoint, Map<String, dynamic> body) async {
    final res = await http.put(
      Uri.parse('$baseUrl$endpoint'),
      headers: _headers,
      body: jsonEncode(body),
    );
    return _handleResponse(res);
  }

  Future<dynamic> delete(String endpoint) async {
    final res = await http.delete(Uri.parse('$baseUrl$endpoint'), headers: _headers);
    return _handleResponse(res);
  }

  dynamic _handleResponse(http.Response res) {
    final body = jsonDecode(res.body);
    if (res.statusCode >= 200 && res.statusCode < 300) return body;
    
    // Handle 401 globally → trigger logout
    if (res.statusCode == 401) {
      clearToken();
      // Navigate to login screen via global navigator key
      throw UnauthorizedException(body['detail'] ?? 'Session expired');
    }
    
    throw ApiException(res.statusCode, body['detail'] ?? 'Unknown error');
  }
}
```

---

## 8. Screen Summary Table

| # | Screen Name | Role | API Endpoints Used | Key Actions |
|---|---|---|---|---|
| 1 | Splash | Both | `GET /auth/me` | Check saved session, route to home |
| 2 | Login | Both | `POST /auth/login`, `GET /auth/me` | Authenticate, save token |
| 3 | Register | Both | `POST /auth/register`, `GET /auth/me` | Create account, role selection |
| 4 | Recruiter Home | Recruiter | — | Bottom nav shell (4 tabs) |
| 5 | Dashboard Tab | Recruiter | `GET /stats` | View metrics |
| 6 | Jobs Tab | Recruiter | `GET /jobs` | List jobs, navigate to create/detail |
| 7 | Create Job | Recruiter | `POST /jobs` | Enter title + JD, AI parsing |
| 8 | Job Detail | Recruiter | `GET /jobs/{id}`, `DELETE /jobs/{id}` | View parsed signals, actions |
| 9 | Edit Job | Recruiter | `PUT /jobs/{id}` | Update title + JD, re-parse |
| 10 | Candidates Tab | Recruiter | `GET /candidates` | Browse all candidates |
| 11 | Search Tab | Recruiter | `GET /jobs`, `POST /search` | Select job, set filters, run pipeline |
| 12 | Search Results | Recruiter | `POST /search/{id}/feedback` | View ranked results, give feedback |
| 13 | Candidate Detail | Both | `GET /candidates/{id}` | Full profile view |
| 14 | Session List | Recruiter | `GET /jobs/{id}/sessions` | View past search sessions |
| 15 | Session Detail | Recruiter | `GET /search/{session_id}` | Revisit past results + feedback |
| 16 | Candidate Home | Candidate | — | Bottom nav shell (2 tabs) |
| 17 | Profile Tab | Candidate | `GET /auth/me` | View own profile |
| 18 | Edit Profile | Candidate | `PUT /candidates/{id}` | Update profile, triggers re-scoring |
| 19 | Job Matches Tab | Candidate | `GET /candidates/me/recommended_jobs` | AI job recommendations |

**Total: 19 screens** (15 unique screens + 4 shell/nav wrappers)

---

*RecruitIQ — Flutter App Flow v1.0*
