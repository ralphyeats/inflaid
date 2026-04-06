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
            cached = result.data[0]["result"]
            # Invalidate stale cache: missing new verdict/ROI fields means old scoring
            verdict = cached.get("verdict") or {}
            roi = cached.get("roi_estimate") or {}
            if "warning_flags" not in verdict or "confidence_explanation" not in roi:
                return None
            return cached
    except Exception as e:
        print(f"Cache get error: {e}")
    return None

def save_analysis(handle: str, score: int, label: str, result: dict, user_email: str = None):
    sb = get_supabase()
    if not sb:
        return
    try:
        record = {
            "handle": handle,
            "score": score,
            "label": label,
            "result": result,
        }
        if user_email:
            record["user_email"] = user_email
        sb.table("analyses").insert(record).execute()
    except Exception as e:
        print(f"Cache save error: {e}")
