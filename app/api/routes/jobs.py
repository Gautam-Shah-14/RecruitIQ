from fastapi import APIRouter, HTTPException, Depends
from app.db.models import JobCreate, JobResponse
from app.db.database import get_db_connection
from app.dependencies import get_current_user
from app.core.jd_parser import parse_jd
from app.core.embedder import get_jd_embedding
import uuid
import json

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobResponse, status_code=201)
def create_job(job: JobCreate, user = Depends(get_current_user)):
    parsed_signals = parse_jd(job.raw_jd)
    new_id = str(uuid.uuid4())
    jd_embedding = get_jd_embedding(job.title, job.raw_jd, parsed_signals)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (id, recruiter_id, title, raw_jd, parsed_signals, embedding_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, title, raw_jd, parsed_signals, created_at;
        """, (new_id, user.id, job.title, job.raw_jd, json.dumps(parsed_signals) if parsed_signals else None, new_id))
        created_job = cursor.fetchone()
        
        # Convert datetime to string for response
        created_job['created_at'] = created_job['created_at'].isoformat()
        
        conn.close()
        return created_job
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=list[JobResponse])
def get_jobs(user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE recruiter_id = %s", (user.id,))
        jobs = cursor.fetchall()
        for j in jobs:
            j['created_at'] = j['created_at'].isoformat()
        conn.close()
        return jobs
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}", response_model=JobResponse)
def get_job(id: str, user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = %s AND recruiter_id = %s", (id, user.id))
        job = cursor.fetchone()
        if not job:
            conn.close()
            raise HTTPException(status_code=404, detail="Job not found")
            
        job['created_at'] = job['created_at'].isoformat()
        conn.close()
        return job
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=404, detail="Job not found")

@router.put("/{id}", response_model=JobResponse)
def update_job(id: str, job_update: JobCreate, user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = %s AND recruiter_id = %s", (id, user.id))
        existing_job = cursor.fetchone()
        if not existing_job:
            conn.close()
            raise HTTPException(status_code=404, detail="Job not found")
            
        parsed_signals = parse_jd(job_update.raw_jd)
        jd_embedding = get_jd_embedding(job_update.title, job_update.raw_jd, parsed_signals)
        
        cursor.execute("""
            UPDATE jobs SET title = %s, raw_jd = %s, parsed_signals = %s
            WHERE id = %s AND recruiter_id = %s
            RETURNING id, title, raw_jd, parsed_signals, created_at;
        """, (job_update.title, job_update.raw_jd, json.dumps(parsed_signals) if parsed_signals else None, id, user.id))
        
        updated_job = cursor.fetchone()
        updated_job['created_at'] = updated_job['created_at'].isoformat()
        conn.close()
        return updated_job
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}")
def delete_job(id: str, user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE id = %s AND recruiter_id = %s", (id, user.id))
        conn.close()
        return {"detail": "Job deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}/sessions")
def get_job_sessions(id: str, user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, created_at FROM search_sessions WHERE job_id = %s AND recruiter_id = %s ORDER BY created_at DESC", (id, user.id))
        sessions = cursor.fetchall()
        for s in sessions:
            if 'created_at' in s and s['created_at']:
                s['created_at'] = s['created_at'].isoformat()
        conn.close()
        return sessions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
