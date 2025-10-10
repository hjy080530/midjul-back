from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api import auth, processing
from app.config import get_settings

settings = get_settings()

# 업로드 폴더 생성
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("ml_models", exist_ok=True)

app = FastAPI(
    title="믿줄 API (Supabase)",
    description="텍스트 하이라이팅 및 요약 API with Supabase + 카카오 로그인",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router)
app.include_router(processing.router)

@app.get("/")
async def root():
    return {"message": "믿줄 API (Supabase)", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "supabase"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)