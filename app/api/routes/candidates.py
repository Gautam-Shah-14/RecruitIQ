from fastapi import APIRouter, HTTPException, Depends
from app.db.models import CandidateCreate
from app.db.database import get_db_connection
from app.dependencies import require_service_role
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
        c_dict["activity_score"] = compute_behavioral(c_dict["behavioral"])
        c_dict["embedding_id"] = cid
        
        text  = f"{c_dict.get('current_title', '')} at {c_dict.get('current_company', '')}. "
        text += f"Skills: {', '.join(c_dict.get('skills', []))}. "
        text += f"Domain: {', '.join(c_dict.get('domain', []))}. "
        text += f"{c_dict.get('years_exp', 0)} years of experience. "
        for role in c_dict.get('career_history', [])[-2:]:
            text += f"{role.get('title', '')} at {role.get('company', '')}: {role.get('desc', '')}. "
            
        c_dict["raw_profile_text"] = text
        
        emb = get_candidate_embedding(c_dict)
        embeddings.append(emb)
        ids.append(cid)
        metadatas.append({
            "years_exp": c_dict["years_exp"],
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
                    education, career_history, behavioral,
                    activity_score, trajectory_score, embedding_id, raw_profile_text
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    years_exp = EXCLUDED.years_exp,
                    skills = EXCLUDED.skills,
                    domain = EXCLUDED.domain,
                    embedding_id = EXCLUDED.embedding_id,
                    raw_profile_text = EXCLUDED.raw_profile_text
            """, (
                c["id"], c["full_name"], c.get("headline"), c.get("email"), c.get("location"), c["years_exp"],
                c["current_title"], c["current_company"], c["domain"], c["skills"],
                json.dumps(c["education"]), json.dumps(c["career_history"]), json.dumps(c["behavioral"]),
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
        c["activity_score"] = compute_behavioral(c["behavioral"])
        
        text  = f"{c.get('current_title', '')} at {c.get('current_company', '')}. "
        text += f"Skills: {', '.join(c.get('skills', []))}. "
        text += f"Domain: {', '.join(c.get('domain', []))}. "
        text += f"{c.get('years_exp', 0)} years of experience. "
        for role in c.get('career_history', [])[-2:]:
            text += f"{role.get('title', '')} at {role.get('company', '')}: {role.get('desc', '')}. "
            
        c["raw_profile_text"] = text
        emb = get_candidate_embedding(c)
        
        cursor.execute("""
            UPDATE candidates SET
                full_name = %s, headline = %s, email = %s, location = %s, years_exp = %s,
                current_title = %s, current_company = %s, domain = %s, skills = %s,
                education = %s, career_history = %s, behavioral = %s,
                activity_score = %s, trajectory_score = %s, raw_profile_text = %s
            WHERE id = %s
        """, (
            c["full_name"], c.get("headline"), c.get("email"), c.get("location"), c["years_exp"],
            c["current_title"], c["current_company"], c["domain"], c["skills"],
            json.dumps(c["education"]), json.dumps(c["career_history"]), json.dumps(c["behavioral"]),
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
