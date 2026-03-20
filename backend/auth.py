import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_cached(handle: str) -> dict:
    sb = get_supabase()
    if not sb:
        return None
    try:
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        result = sb.table("analyses").select("result").eq("handle", handle).gte("created_at", cutoff).order("created_at", desc=True).limit(1).execute()
        if result.data:
            return result.data[0]["result"]
    except Exception as e:
        print(f"Cache get error: {e}")
    return None

def save_analysis(handle: str, score: int, label: str, result: dict):
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("analyses").insert({
            "handle": handle,
            "score": score,
            "label": label,
            "result": result
        }).execute()
    except Exception as e:
        print(f"Cache save error: {e}")
