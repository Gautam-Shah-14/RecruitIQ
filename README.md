# RecruitIQ — Backend

> Intelligent Candidate Discovery | Hackathon Edition | v1.0

RecruitIQ is an intelligent backend service designed to power a next-generation technical recruiter platform. By combining dense vector embeddings with multi-signal heuristics and Large Language Model (LLM) contextual re-ranking, it moves beyond keyword search to actually match candidate capability, seniority, and trajectory against a job description.

---

## 🚀 Features

- **Multi-Role Authentication**: Unified login and registration supporting both `recruiter` and `candidate` roles.
- **AI-Powered Job Parsing**: Upload a raw job description, and the backend utilizes Groq (LLaMA3) to extract structured signals (skills, seniority, domain, culture).
- **Semantic Candidate Search**: Profiles and jobs are encoded locally using `sentence-transformers` and searched blazing-fast using **ChromaDB**.
- **Multi-Signal Scoring Algorithm**: Candidates are ranked based on a composite score combining semantic similarity, Jaccard skill match, Gaussian seniority fit, trajectory, and behavioral metrics.
- **LLM Contextual Re-ranking**: The top candidates are passed through a final Groq pass to re-rank based on nuanced career narratives, generating a plain-English `why_this_candidate` explanation.
- **Direct Postgres Integration**: Bypasses BaaS REST APIs by directly interacting with the PostgreSQL database using `psycopg2` for speed and absolute flexibility.

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **API Framework** | FastAPI (Python 3.11) | REST endpoints, dependency injection |
| **LLM Inference** | Groq API (`llama3-70b-8192`) | JD parsing, contextual explanation generation |
| **Embeddings** | `sentence-transformers` | `all-MiniLM-L6-v2` local vector encoding |
| **Vector Database** | ChromaDB | Local ANN (Approximate Nearest Neighbor) search |
| **Primary Database** | PostgreSQL | Raw connection via `psycopg2` for relational data |

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.11+
- A PostgreSQL database (e.g., Supabase, RDS, or local Postgres)
- A Groq API Key

### 2. Install Dependencies
Clone the repository and install the Python dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory based on the `.env.example` file:

```env
# Postgres Connection
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

### 4. Database Initialization & Seeding
We provide a unified script that will create all necessary SQL schemas (Users, Recruiters, Candidates, Jobs, Sessions) and seed the database with test data:

```bash
python scripts/init_db.py
```
*Note: This script also populates ChromaDB with vector embeddings for the seeded candidates.*

### 5. Run the Server
Start the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```
The interactive API documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📡 Core API Endpoints

### Auth
- `POST /auth/register`: Register as a `recruiter` or `candidate`.
- `POST /auth/login`: Authenticate and receive a Bearer token.
- `GET /auth/me`: Get the currently authenticated profile.

### Jobs
- `GET /jobs`: List all jobs for the authenticated recruiter.
- `POST /jobs`: Create a new job description (triggers LLM parsing and embedding).
- `PUT /jobs/{id}`: Update job details.
- `GET /jobs/{id}/sessions`: Retrieve past AI search sessions for a specific role.

### Candidates
- `GET /candidates`: Fetch all candidates.
- `POST /candidates`: Ingest a single candidate profile.
- `PUT /candidates/{id}`: Update candidate details (auto-recalculates embeddings & scores).

### Search Pipeline
- `POST /search`: Execute the 5-step AI pipeline (Parse -> Embed -> Vector Search -> Score -> Re-rank). Returns a shortlisted, scored array of candidates.
- `POST /search/{session_id}/feedback`: Submit recruiter thumbs-up/thumbs-down feedback on a search result.

---

## 🧠 The AI Search Pipeline (`app/core/pipeline.py`)

When `POST /search` is called, the following execution graph occurs:

1. **Step 1 (Parse)**: Passes the raw Job Description to Groq to extract structured JSON rules.
2. **Step 2 (Embed)**: Encodes the job into a 384-dimensional dense vector locally.
3. **Step 3 (Retrieve)**: Queries ChromaDB for the Top-K candidates using cosine similarity.
4. **Step 4 (Score)**: Applies a fast Python-native composite scoring heuristic mixing vector distance with Jaccard skill metrics and Gaussian seniority decay.
5. **Step 5 (Re-Rank)**: Prompts LLaMA3-70b via Groq to review the Top-N candidates contextually and output a final ranked list alongside qualitative explanations.
