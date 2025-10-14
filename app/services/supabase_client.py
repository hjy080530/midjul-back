from supabase import Client
from app.config import get_settings
from typing import Optional

settings = get_settings()

# 전역 변수 (초기화는 나중에)
_supabase: Optional[Client] = None
_supabase_admin: Optional[Client] = None

def get_supabase() -> Client:
    """일반 Supabase 클라이언트 반환 (지연 초기화)"""
    global _supabase
    if _supabase is None:
        try:
            from supabase import create_client
            print("Supabase 클라이언트 초기화 중...")
            _supabase = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            print("Supabase 클라이언트 초기화 완료")
        except Exception as e:
            print(f"⚠️ Supabase 초기화 실패: {e}")
            print("DB 저장 없이 계속 진행합니다.")
            # 더미 객체 반환하지 않고 None 유지
    return _supabase

def get_supabase_admin() -> Client:
    """관리자 Supabase 클라이언트 반환 (지연 초기화)"""
    global _supabase_admin
    if _supabase_admin is None:
        try:
            from supabase import create_client
            print("Supabase Admin 클라이언트 초기화 중...")
            _supabase_admin = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            print("Supabase Admin 클라이언트 초기화 완료")
        except Exception as e:
            print(f"⚠️ Supabase Admin 초기화 실패: {e}")
    return _supabase_admin