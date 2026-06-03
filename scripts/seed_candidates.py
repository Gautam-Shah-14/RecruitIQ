import sys
import os
import json
import uuid
import time
import psycopg2
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.embedder import get_candidate_embedding
from app.core.scorer import compute_trajectory, compute_behavioral
from app.core.vector_store import add_candidates

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

def seed_data():
    if not DATABASE_URL:
        print("Error: DATABASE_URL not found in environment variables.")
        sys.exit(1)
        
    candidates = []
    
    # Generate some dummy candidates for demo
    for i in range(10):
        c = {
            "id": str(uuid.uuid4()),
            "full_name": f"Candidate {i}",
            "headline": "ML Engineer",
            "email": f"candidate{i}@example.com",
            "location": "Remote",
            "years_exp": 3 + i,
            "current_title": "ML Engineer",
            "current_company": "Tech Corp",
            "domain": ["ml", "backend"],
            "skills": ["Python", "PyTorch", "AWS"],
            "education": [],
            "career_history": [],
            "behavioral": {"oss_commits": 50, "talks": 2, "articles": 1}
        }
        
        c["trajectory_score"] = compute_trajectory(c["career_history"])
        c["activity_score"] = compute_behavioral(c["behavioral"])
        
        text  = f"{c.get('current_title', '')} at {c.get('current_company', '')}. "
        text += f"Skills: {', '.join(c.get('skills', []))}. "
        text += f"Domain: {', '.join(c.get('domain', []))}. "
        text += f"{c.get('years_exp', 0)} years of experience. "
        c["raw_profile_text"] = text
        c["embedding_id"] = c["id"]
        
        candidates.append(c)
        
    print("Embedding candidates...")
    embeddings = [get_candidate_embedding(c) for c in candidates]
    
    print("Saving to Postgres Database via DATABASE_URL...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()
    
    insert_sql = """
        INSERT INTO candidates (
            id, full_name, headline, email, location, years_exp,
            current_title, current_company, domain, skills,
            education, career_history, behavioral,
            activity_score, trajectory_score,
            embedding_id, raw_profile_text
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s
        ) ON CONFLICT (email) DO UPDATE SET
            full_name = EXCLUDED.full_name,
            years_exp = EXCLUDED.years_exp,
            skills = EXCLUDED.skills,
            domain = EXCLUDED.domain,
            embedding_id = EXCLUDED.embedding_id,
            raw_profile_text = EXCLUDED.raw_profile_text;
    """
    
    for c in candidates:
        cursor.execute(insert_sql, (
            c["id"], c["full_name"], c["headline"], c["email"], c["location"], c["years_exp"],
            c["current_title"], c["current_company"], c["domain"], c["skills"],
            json.dumps(c["education"]), json.dumps(c["career_history"]), json.dumps(c["behavioral"]),
            c["activity_score"], c["trajectory_score"],
            c["embedding_id"], c["raw_profile_text"]
        ))
        
    cursor.close()
    conn.close()
    
    print("Saving to ChromaDB...")
    add_candidates(
        candidate_ids=[c["id"] for c in candidates],
        embeddings=embeddings,
        metadatas=[{"years_exp": c["years_exp"], "domain": ",".join(c["domain"])} for c in candidates]
    )
    
    print(f"Seeded {len(candidates)} candidates")

if __name__ == "__main__":
    seed_data()
