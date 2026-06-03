from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    groq_api_key: str
    groq_model: str = "llama3-70b-8192"
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "candidates"
    app_env: str = "development"
    secret_key: str = "dev-secret-key"
    allowed_origins: str = "*"

    class Config:
        env_file = ".env"

settings = Settings()
