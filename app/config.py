from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "믿줄 Backend"
    DEBUG: bool = True

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str  # anon key
    SUPABASE_SERVICE_KEY: str  # service_role key

    # Kakao OAuth
    KAKAO_CLIENT_ID: str
    KAKAO_CLIENT_SECRET: str = ""

    # 국립국어원 API (타입 어노테이션 추가!)
    KOREAN_DICT_API_KEY: str = "FB926305D20DFB92DBEE11E8DF7BB3C7"

    # Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # AI Models
    KEYWORD_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    SUMMARY_MODEL: str = "eenzeenee/t5-base-korean-summarization"

    # Database
    DATABASE_URL: str = "sqlite:///./mitjul.db"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()