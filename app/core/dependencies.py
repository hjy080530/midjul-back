from fastapi import Depends, HTTPException, Header
from app.services.supabase_client import get_supabase
from supabase import Client


async def get_current_user_id(
        authorization: str = Header(...),
        supabase: Client = Depends(get_supabase)
):
    """헤더에서 JWT 토큰 검증 후 user_id 반환"""
    try:
        # "Bearer <token>" 형식
        token = authorization.replace("Bearer ", "")

        # Supabase에서 토큰 검증
        user = supabase.auth.get_user(token)

        if not user or not user.user:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰")

        return user.user.id

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"인증 실패: {str(e)}")