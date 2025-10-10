from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

# 일반 클라이언트 (anon key)
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

# 서비스 클라이언트 (service_role key, RLS 우회)
supabase_admin: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)

def get_supabase() -> Client:
    return supabase

def get_supabase_admin() -> Client:
    return supabase_admin