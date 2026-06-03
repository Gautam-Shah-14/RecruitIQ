from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

def add_middleware(app: FastAPI):
    origins = settings.allowed_origins.split(",") if settings.allowed_origins else ["*"]
    if "*" in origins:
        origins = ["*"]
        
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
