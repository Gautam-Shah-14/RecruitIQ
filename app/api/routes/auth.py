from fastapi import APIRouter, HTTPException, Depends
from app.db.models import RegisterRequest, LoginRequest, AuthResponse
from app.db.database import get_db_connection
from app.dependencies import get_current_user
import uuid
import hashlib
import json

router = APIRouter(prefix="/auth", tags=["auth"])

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest):
    if request.role not in ["recruiter", "candidate"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'recruiter' or 'candidate'.")
        
    user_id = str(uuid.uuid4())
    hashed_pw = hash_password(request.password)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Create User
        cursor.execute(
            "INSERT INTO users (id, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (user_id, request.email, hashed_pw, request.role)
        )
        
        # 2. Create Role-Specific Profile
        if request.role == "recruiter":
            cursor.execute(
                "INSERT INTO recruiter_profiles (id, full_name, company) VALUES (%s, %s, %s)",
                (user_id, request.full_name, request.company)
            )
        elif request.role == "candidate":
            cursor.execute(
                """INSERT INTO candidates (
                    id, user_id, full_name, headline, email, location, years_exp,
                    current_title, current_company, domain, skills,
                    education, career_history, certifications, languages, redrob_signals
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '[]', '[]', '[]', '[]', '{}')""",
                (
                    f"CAND_{str(uuid.uuid4().int)[:7]}", user_id, request.full_name, request.headline, request.email, 
                    request.location, request.years_exp, request.current_title, 
                    request.current_company, request.domain, json.dumps(request.skills)
                )
            )
            
        conn.close()
        return AuthResponse(access_token=f"auth-{user_id}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hashed_pw = hash_password(request.password)
        cursor.execute("SELECT id FROM users WHERE email = %s AND password_hash = %s", (request.email, hashed_pw))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        return AuthResponse(access_token=f"auth-{user['id']}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me")
def get_me(user = Depends(get_current_user)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user.role == "recruiter":
            cursor.execute("SELECT * FROM recruiter_profiles WHERE id = %s", (user.id,))
        else:
            cursor.execute("SELECT * FROM candidates WHERE user_id = %s", (user.id,))
            
        data = cursor.fetchone()
        conn.close()
        if not data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        if 'created_at' in data and data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
            
        # Include role in response
        data['role'] = user.role
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
