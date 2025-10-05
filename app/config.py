from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "믿줄 Backend"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:3000"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str  # anon key
    SUPABASE_SERVICE_KEY: str  # service_role key

    # Kakao OAuth
    KAKAO_CLIENT_ID: str
    KAKAO_CLIENT_SECRET: str = ""

    # Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024

    # AI Models
    KEYWORD_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    SUMMARY_MODEL: str = "eenzeenee/t5-base-korean-summarization"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()