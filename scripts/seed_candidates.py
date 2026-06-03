import json
import psycopg2
import uuid
import os
from dotenv import load_dotenv
from app.core.embedder import get_candidate_embedding
from app.core.vector_store import add_candidates

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def seed_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    file_path = os.path.join("India_runs_data_and_ai_challenge", "sample_candidates.json")
    with open(file_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    embeddings = []
    ids = []
    metadatas = []
    
    # We will just seed the first 100 to save time
    # candidates = candidates[:100]
    
    print(f"Seeding {len(candidates)} candidates from challenge schema...")
    
    for c in candidates:
        cid = c["candidate_id"]
        
        # Calculate derived fields for embedding
        c_dict = {
            "current_title": c["profile"].get("current_title", ""),
            "current_company": c["profile"].get("current_company", ""),
            "skills": [s["name"] for s in c.get("skills", [])],
            "domain": [c["profile"].get("current_industry", "")],
            "years_exp": c["profile"].get("years_of_experience", 0),
            "career_history": c.get("career_history", [])
        }
        
        text  = f"{c_dict['current_title']} at {c_dict['current_company']}. "
        text += f"Skills: {', '.join(c_dict['skills'])}. "
        text += f"Domain: {', '.join(c_dict['domain'])}. "
        text += f"{c_dict['years_exp']} years of experience. "
        for role in c_dict['career_history'][:2]:
            text += f"{role.get('title', '')} at {role.get('company', '')}: {role.get('description', '')}. "
            
        emb = get_candidate_embedding(c_dict)
        embeddings.append(emb)
        ids.append(cid)
        
        # Simple metadata for chroma filters
        metadatas.append({
            "years_exp": c_dict["years_exp"],
            "domain": ",".join(c_dict["domain"]),
            "location": c["profile"].get("location", "")
        })
        
        # Calculate dummy trajectory/behavioral using old logic or defaults
        trajectory_score = 0.5  # placeholder
        activity_score = (c.get("redrob_signals", {}).get("profile_completeness_score", 50) / 100.0)
        
        # Insert into PG
        cursor.execute("""
            INSERT INTO candidates (
                id, user_id, full_name, headline, email, location, years_exp,
                current_title, current_company, domain, skills,
                education, career_history, certifications, languages, redrob_signals,
                activity_score, trajectory_score, embedding_id, raw_profile_text
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                years_exp = EXCLUDED.years_exp,
                skills = EXCLUDED.skills,
                domain = EXCLUDED.domain,
                embedding_id = EXCLUDED.embedding_id,
                raw_profile_text = EXCLUDED.raw_profile_text
        """, (
            cid, None, c["profile"].get("anonymized_name", ""), c["profile"].get("headline", ""), f"{cid}@example.com", 
            c["profile"].get("location", ""), c_dict["years_exp"],
            c_dict["current_title"], c_dict["current_company"], c_dict["domain"], 
            json.dumps(c.get("skills", [])), json.dumps(c.get("education", [])), 
            json.dumps(c.get("career_history", [])), json.dumps(c.get("certifications", [])), 
            json.dumps(c.get("languages", [])), json.dumps(c.get("redrob_signals", {})),
            activity_score, trajectory_score, cid, text
        ))
        
    conn.commit()
    cursor.close()
    conn.close()
    
    print("Saving to ChromaDB...")
    add_candidates(
        candidate_ids=ids,
        embeddings=embeddings,
        metadatas=metadatas
    )
    
    print(f"Seeded {len(candidates)} candidates successfully.")

if __name__ == "__main__":
    seed_data()
