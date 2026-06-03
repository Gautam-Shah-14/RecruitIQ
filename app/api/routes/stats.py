from fastapi import APIRouter, HTTPException, Depends
from app.db.database import get_db_connection
from app.db.models import StatsResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("", response_model=StatsResponse)
def get_stats(user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM jobs WHERE recruiter_id = %s", (user.id,))
        total_jobs = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM candidates")
        total_candidates = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM search_sessions WHERE recruiter_id = %s", (user.id,))
        total_sessions = cursor.fetchone()['count']
        
        conn.close()
        return StatsResponse(
            total_jobs=total_jobs,
            total_candidates=total_candidates,
            total_sessions=total_sessions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
