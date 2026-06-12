from fastapi import APIRouter, HTTPException, Depends
from app.db.models import CandidateCreate
from app.db.database import get_db_connection
from app.dependencies import require_service_role, get_current_user
from app.core.embedder import get_candidate_embedding
from app.core.vector_store import add_candidates
from app.core.scorer import compute_trajectory, compute_behavioral
import uuid
import json

router = APIRouter(prefix="/candidates", tags=["candidates"])

def process_and_ingest(candidates: list[CandidateCreate]):
    embeddings = []
    ids = []
    metadatas = []
    db_records = []
    
    for c in candidates:
        cid = str(uuid.uuid4())
        c_dict = c.model_dump()
        c_dict["id"] = cid
        c_dict["trajectory_score"] = compute_trajectory(c_dict["career_history"])
        
        # Compute behavioral score from redrob signals
        activity_score = compute_behavioral(c_dict.get("redrob_signals", {}))
        c_dict["activity_score"] = activity_score
        c_dict["embedding_id"] = cid
        
        text  = f"{c_dict.get('current_title', '')} at {c_dict.get('current_company', '')}. "
        skill_names = [s.get('name', '') for s in c_dict.get('skills', []) if isinstance(s, dict)]
        text += f"Skills: {', '.join(skill_names)}. "
        text += f"Domain: {', '.join(c_dict.get('domain', []))}. "
        text += f"{c_dict.get('years_exp', 0)} years of experience. "
        for role in c_dict.get('career_history', [])[-2:]:
            text += f"{role.get('title', '')} at {role.get('company', '')}: {role.get('description', role.get('desc', ''))}. "
            
        c_dict["raw_profile_text"] = text
        
        emb = get_candidate_embedding(c_dict)
        embeddings.append(emb)
        ids.append(cid)
        metadatas.append({
            "years_exp": float(c_dict["years_exp"]),
            "domain": ",".join(c_dict["domain"]),
            "location": c_dict.get("location", "")
        })
        db_records.append(c_dict)
        
    if db_records:
        conn = get_db_connection()
        cursor = conn.cursor()
        for c in db_records:
            cursor.execute("""
                INSERT INTO candidates (
                    id, full_name, headline, email, location, years_exp,
                    current_title, current_company, domain, skills,
                    education, career_history, certifications, languages, redrob_signals,
                    activity_score, trajectory_score, embedding_id, raw_profile_text
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    years_exp = EXCLUDED.years_exp,
                    skills = EXCLUDED.skills,
                    domain = EXCLUDED.domain,
                    embedding_id = EXCLUDED.embedding_id,
                    raw_profile_text = EXCLUDED.raw_profile_text
            """, (
                c["id"], c["full_name"], c.get("headline"), c.get("email"), c.get("location"), c["years_exp"],
                c["current_title"], c["current_company"], c["domain"], json.dumps(c["skills"]),
                json.dumps(c["education"]), json.dumps(c["career_history"]), json.dumps(c.get("certifications", [])),
                json.dumps(c.get("languages", [])), json.dumps(c.get("redrob_signals", {})),
                c["activity_score"], c["trajectory_score"], c["embedding_id"], c["raw_profile_text"]
            ))
        conn.close()
        
    if ids:
        add_candidates(ids, embeddings, metadatas)
        
    return {"inserted": len(ids)}

@router.post("", dependencies=[Depends(require_service_role)])
def create_candidate(candidate: CandidateCreate):
    try:
        return process_and_ingest([candidate])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bulk", dependencies=[Depends(require_service_role)])
def create_candidates_bulk(candidates: list[CandidateCreate]):
    try:
        return process_and_ingest(candidates)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("")
def get_all_candidates():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidates")
        cands = cursor.fetchall()
        conn.close()
        for cand in cands:
            if 'created_at' in cand and cand['created_at']:
                cand['created_at'] = cand['created_at'].isoformat()
        return cands
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{id}")
def get_candidate(id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidates WHERE id = %s", (id,))
        cand = cursor.fetchone()
        conn.close()
        if not cand:
            raise HTTPException(status_code=404, detail="Candidate not found")
        cand['created_at'] = cand['created_at'].isoformat()
        return cand
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=404, detail="Candidate not found")

@router.put("/{id}")
def update_candidate(id: str, candidate_update: CandidateCreate):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidates WHERE id = %s", (id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Candidate not found")
            
        c = candidate_update.model_dump()
        c["trajectory_score"] = compute_trajectory(c["career_history"])
        c["activity_score"] = compute_behavioral(c.get("redrob_signals", {}))
        
        text  = f"{c.get('current_title', '')} at {c.get('current_company', '')}. "
        skill_names = [s.get('name', '') for s in c.get('skills', []) if isinstance(s, dict)]
        text += f"Skills: {', '.join(skill_names)}. "
        text += f"Domain: {', '.join(c.get('domain', []))}. "
        text += f"{c.get('years_exp', 0)} years of experience. "
        for role in c.get('career_history', [])[-2:]:
            text += f"{role.get('title', '')} at {role.get('company', '')}: {role.get('description', role.get('desc', ''))}. "
            
        c["raw_profile_text"] = text
        emb = get_candidate_embedding(c)
        
        cursor.execute("""
            UPDATE candidates SET
                full_name = %s, headline = %s, email = %s, location = %s, years_exp = %s,
                current_title = %s, current_company = %s, domain = %s, skills = %s,
                education = %s, career_history = %s, certifications = %s, languages = %s, redrob_signals = %s,
                activity_score = %s, trajectory_score = %s, raw_profile_text = %s
            WHERE id = %s
        """, (
            c["full_name"], c.get("headline"), c.get("email"), c.get("location"), c["years_exp"],
            c["current_title"], c["current_company"], c["domain"], json.dumps(c["skills"]),
            json.dumps(c["education"]), json.dumps(c["career_history"]), json.dumps(c.get("certifications", [])),
            json.dumps(c.get("languages", [])), json.dumps(c.get("redrob_signals", {})),
            c["activity_score"], c["trajectory_score"], c["raw_profile_text"], id
        ))
        conn.close()
        
        # update chroma
        add_candidates([id], [emb], [{"years_exp": c["years_exp"], "domain": ",".join(c["domain"]), "location": c.get("location", "")}])
        
        return {"detail": "Candidate updated"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", dependencies=[Depends(require_service_role)])
def delete_candidate(id: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM candidates WHERE id = %s", (id,))
        conn.close()
        return {"detail": "Candidate deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me/recommended_jobs")
def get_recommended_jobs(user = Depends(get_current_user)):
    if user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidates can view recommended jobs")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM candidates WHERE user_id = %s", (user.id,))
        cand = cursor.fetchone()
        
        cursor.execute("SELECT id, title, raw_jd, parsed_signals FROM jobs")
        jobs = cursor.fetchall()
        conn.close()
        
        if not cand or not jobs:
            return []
            
        cand_str = f"Name: {cand.get('full_name')}, Title: {cand.get('current_title')}, Exp: {cand.get('years_exp')}, Skills: {[s.get('name', '') for s in cand.get('skills', []) if isinstance(s, dict)][:10]}"
        
        jobs_str = ""
        for j in jobs:
            jobs_str += f"JobID: {j['id']} | Title: {j['title']} | Seniority: {(j.get('parsed_signals') or {}).get('seniority_level', 'mid')}\n"
            
        system = "You are a job matching AI. Given a candidate profile and a list of jobs, return a JSON array of the top 3 recommended jobs in format: [{\"job_id\": \"id\", \"reason\": \"string match explanation\", \"match_score\": 95}]. Output ONLY JSON array."
        user_prompt = f"Candidate Profile:\n{cand_str}\n\nAvailable Jobs:\n{jobs_str}"
        
        from app.core.groq_client import groq_client
        res = groq_client.chat(system, user_prompt, temperature=0.1)
        recommendations = json.loads(res)
        
        jobs_map = {str(j["id"]): j for j in jobs}
        for rec in recommendations:
            job = jobs_map.get(str(rec["job_id"]))
            if job:
                rec["job_title"] = job["title"]
                
        return [r for r in recommendations if "job_title" in r]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
