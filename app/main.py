from fastapi import FastAPI
from app.api.routes import auth, jobs, candidates, search, stats
from app.api.middleware import add_middleware

app = FastAPI(title="RecruitIQ Backend")

# Middleware
add_middleware(app)

# Routes
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(search.router)
app.include_router(stats.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
