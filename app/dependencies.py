from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.db.database import get_db_connection

security = HTTPBearer()

class AuthUser(BaseModel):
    id: str
    role: str

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # We are using a simple prefix token strategy: "auth-<uuid>"
    if not token.startswith("auth-"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = token.replace("auth-", "")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, role FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
    return AuthUser(id=str(user['id']), role=user['role'])

def require_service_role():
    pass
