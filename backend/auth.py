import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_or_create_user(email: str) -> dict:
    sb = get_supabase()
    if not sb:
        return None
    result = sb.table("users").select("*").eq("email", email).execute()
    if result.data:
        return result.data[0]
    new_user = sb.table("users").insert({"email": email}).execute()
    return new_user.data[0] if new_user.data else None

def check_limit(user_id: str) -> bool:
    sb = get_supabase()
    if not sb:
        return True
    result = sb.table("users").select("analyses_used,analyses_limit").eq("id", user_id).execute()
    if not result.data:
        return False
    u = result.data[0]
    return u["analyses_used"] < u["analyses_limit"]

def increment_usage(user_id: str):
    sb = get_supabase()
    if not sb:
        return
    sb.rpc("increment_analyses", {"user_id_input": user_id}).execute()

def get_cached(handle: str) -> dict:
    sb = get_supabase()
    if not sb:
        return None
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    result = sb.table("analyses").select("result").eq("handle", handle).gte("created_at", cutoff).order("created_at", desc=True).limit(1).execute()
    if result.data:
        return result.data[0]["result"]
    return None

def save_analysis(user_id: str, handle: str, score: int, label: str, result: dict):
    sb = get_supabase()
    if not sb:
        return
    sb.table("analyses").insert({
        "user_id": user_id,
        "handle": handle,
        "score": score,
        "label": label,
        "result": result
    }).execute()
