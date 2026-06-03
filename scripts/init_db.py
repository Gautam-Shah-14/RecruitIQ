import os
import sys
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment variables. Please add it to your .env file.")
    sys.exit(1)

SQL_SCRIPT = """
-- Create users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert dummy users for existing recruiters (password: password123)
INSERT INTO users (id, email, password_hash, role)
VALUES 
  ('00000000-0000-0000-0000-000000000001', 'dummy1@example.com', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'recruiter'),
  ('00000000-0000-0000-0000-000000000002', 'dummy2@example.com', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'recruiter'),
  ('00000000-0000-0000-0000-000000000003', 'dummy3@example.com', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f', 'recruiter')
ON CONFLICT (email) DO NOTHING;

-- Create recruiter_profiles table (references users)
CREATE TABLE IF NOT EXISTS recruiter_profiles (
  id          UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  full_name   TEXT NOT NULL,
  company     TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Insert dummy recruiters so queries don't fail
INSERT INTO recruiter_profiles (id, full_name, company) 
VALUES 
  ('00000000-0000-0000-0000-000000000001', 'Dummy Recruiter', 'Dummy Corp'),
  ('00000000-0000-0000-0000-000000000002', 'Alice Smith', 'Tech Giant Inc'),
  ('00000000-0000-0000-0000-000000000003', 'Bob Jones', 'Startup Co')
ON CONFLICT (id) DO NOTHING;

-- Create jobs table
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

-- Seed some dummy jobs
INSERT INTO jobs (id, recruiter_id, title, raw_jd)
VALUES
  ('11111111-1111-1111-1111-111111111111', '00000000-0000-0000-0000-000000000001', 'Senior Backend Engineer', 'Looking for a Senior Backend Engineer with Python and Postgres experience.'),
  ('22222222-2222-2222-2222-222222222222', '00000000-0000-0000-0000-000000000002', 'Machine Learning Engineer', 'We need an ML Engineer proficient in PyTorch and AWS.'),
  ('33333333-3333-3333-3333-333333333333', '00000000-0000-0000-0000-000000000003', 'Frontend Developer', 'Seeking a frontend developer experienced with React and TailwindCSS.')
ON CONFLICT (id) DO NOTHING;

-- Create candidates table
CREATE TABLE IF NOT EXISTS candidates (
  id               TEXT PRIMARY KEY,
  user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
  full_name        TEXT NOT NULL,
  headline         TEXT,
  email            TEXT UNIQUE,
  location         TEXT,
  years_exp        FLOAT,
  current_title    TEXT,
  current_company  TEXT,
  domain           TEXT[],
  skills           JSONB,
  education        JSONB,
  career_history   JSONB,
  certifications   JSONB,
  languages        JSONB,
  redrob_signals   JSONB,
  activity_score   FLOAT DEFAULT 0,
  trajectory_score FLOAT DEFAULT 0,
  embedding_id     TEXT,
  raw_profile_text TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Create search_sessions table
CREATE TABLE IF NOT EXISTS search_sessions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recruiter_id UUID NOT NULL REFERENCES recruiter_profiles(id),
  job_id       UUID NOT NULL REFERENCES jobs(id),
  results      JSONB,
  feedback     JSONB DEFAULT '{}',
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Create Indexes
CREATE INDEX IF NOT EXISTS idx_candidates_domain  ON candidates USING GIN (domain);
CREATE INDEX IF NOT EXISTS idx_candidates_skills  ON candidates USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_jobs_recruiter     ON jobs (recruiter_id);
CREATE INDEX IF NOT EXISTS idx_sessions_recruiter ON search_sessions (recruiter_id);
"""

def init_db():
    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Executing schema creation script (no RLS/Auth)...")
        cursor.execute(SQL_SCRIPT)
        print("Schema created successfully!")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
    
    print("\\nDatabase schemas initialized. Now seeding candidate data...")
    try:
        from scripts.seed_candidates import seed_data
        seed_data()
        print("Done!")
    except Exception as e:
        print(f"Failed to seed data: {e}")
