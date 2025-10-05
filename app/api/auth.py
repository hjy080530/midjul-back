from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.supabase_client import get_supabase, get_supabase_admin
from supabase import Client
import httpx

router = APIRouter(prefix="/auth", tags=["authentication"])


class KakaoLoginRequest(BaseModel):
    access_token: str  # 프론트엔드에서 받은 카카오 액세스 토큰


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict


@router.post("/kakao/callback", response_model=TokenResponse)
async def kakao_login(request: KakaoLoginRequest):
    """
    프론트엔드에서 카카오 액세스 토큰을 받아서 Supabase 세션 생성
    """
    supabase = get_supabase()

    try:
        # 카카오 사용자 정보 가져오기
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {request.access_token}"}
            )
            response.raise_for_status()
            kakao_user = response.json()

        kakao_id = str(kakao_user["id"])
        kakao_account = kakao_user.get("kakao_account", {})
        email = kakao_account.get("email", f"kakao_{kakao_id}@mitjul.app")

        # Supabase Admin으로 사용자 찾기 또는 생성
        supabase_admin = get_supabase_admin()

        # 기존 사용자 확인
        existing_user = supabase_admin.table("users").select("*").eq("kakao_id", kakao_id).execute()

        if not existing_user.data:
            # 새 사용자 생성
            new_user = supabase_admin.table("users").insert({
                "kakao_id": kakao_id,
                "email": email,
                "nickname": kakao_account.get("profile", {}).get("nickname"),
                "profile_image": kakao_account.get("profile", {}).get("profile_image_url")
            }).execute()
            user_data = new_user.data[0]
        else:
            user_data = existing_user.data[0]

        # Supabase Auth 세션 생성 (JWT 토큰 생성)
        # 방법 1: signInWithPassword (이메일/비밀번호 없이 커스텀 토큰)
        # 방법 2: Admin API로 직접 JWT 생성

        # 여기서는 간단하게 사용자 정보만 반환 (프론트엔드에서 Supabase Auth 직접 사용 권장)
        return {
            "access_token": request.access_token,  # 카카오 토큰 그대로 사용
            "refresh_token": "",
            "user": {
                "id": user_data["id"],
                "email": user_data["email"],
                "nickname": user_data["nickname"],
                "profile_image": user_data["profile_image"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"카카오 로그인 실패: {str(e)}")


@router.get("/me")
async def get_current_user(supabase: Client = Depends(get_supabase)):
    """현재 로그인한 사용자 정보"""
    try:
        user = supabase.auth.get_user()
        if not user:
            raise HTTPException(status_code=401, detail="인증되지 않음")

        # DB에서 사용자 정보 조회
        user_data = supabase.table("users").select("*").eq("id", user.user.id).single().execute()
        return user_data.data
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))