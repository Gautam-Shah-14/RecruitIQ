from fastapi import APIRouter, HTTPException, Depends
from app.db.models import SearchRequest, SearchResponse, FeedbackRequest
from app.db.database import get_db_connection
from app.dependencies import get_current_user
from app.core.pipeline import run_search_pipeline
import json

router = APIRouter(prefix="/search", tags=["search"])

@router.post("", response_model=SearchResponse)
def search(request: SearchRequest, user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = %s AND recruiter_id = %s", (str(request.job_id), user.id))
        job = cursor.fetchone()
        
        if not job:
            conn.close()
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Run Pipeline
        result = run_search_pipeline(
            job=job,
            top_k=request.top_k,
            shortlist_n=request.shortlist_n,
            filters=request.filters.model_dump() if request.filters else None,
            conn=conn
        )
        
        # Save Search Session
        cursor.execute("""
            INSERT INTO search_sessions (id, recruiter_id, job_id, results, feedback)
            VALUES (%s, %s, %s, %s, %s)
        """, (result["session_id"], user.id, str(request.job_id), json.dumps(result["results"]), json.dumps({})))
        
        conn.close()
        return result
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/feedback")
def submit_feedback(session_id: str, request: FeedbackRequest, user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT feedback FROM search_sessions WHERE id = %s AND recruiter_id = %s", (session_id, user.id))
        session = cursor.fetchone()
        if not session:
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")
            
        feedback = session.get("feedback", {})
        if not isinstance(feedback, dict):
            feedback = {}
            
        feedback[str(request.candidate_id)] = request.signal
        
        cursor.execute("UPDATE search_sessions SET feedback = %s WHERE id = %s", (json.dumps(feedback), session_id))
        conn.close()
        return {"detail": "Feedback saved"}
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{session_id}")
def get_session(session_id: str, user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM search_sessions WHERE id = %s AND recruiter_id = %s", (session_id, user.id))
        session = cursor.fetchone()
        conn.close()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session['created_at'] = session['created_at'].isoformat()
        return session
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=404, detail="Session not found")
