import os
import stripe
import anthropic
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from scraper import fetch_profile, PrivateAccountError
from scorer import compute_score

app = FastAPI(title="Inflaid API", version="0.1.0")

DEFAULT_FRONTEND_URL = "https://inflaid.com"
FRONTEND_URL = os.getenv("FRONTEND_URL", DEFAULT_FRONTEND_URL).rstrip("/")

ALLOWED_ORIGINS = [
    "https://inflaid.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if FRONTEND_URL not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(FRONTEND_URL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

PLAN_LIMITS = {"free": 2, "trial": 2, "starter": 20, "growth": 75, "pro": 200}


def verify_token(authorization: str) -> str:
    """Verify Supabase JWT, return confirmed email. Raises 401 if invalid."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="auth_required")
    token = authorization.split(" ", 1)[1]
    try:
        from auth import get_supabase
        sb = get_supabase()
        resp = sb.auth.get_user(token)
        if not resp.user or not resp.user.email:
            raise HTTPException(status_code=401, detail="auth_required")
        return resp.user.email
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="auth_required")
PLAN_PRICE_IDS = {
    "starter": os.getenv("STRIPE_STARTER_PRICE"),
    "growth":  os.getenv("STRIPE_GROWTH_PRICE"),
    "pro":     os.getenv("STRIPE_PRO_PRICE"),
}

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class ScoreRequest(BaseModel):
    handle: str
    user_email: Optional[str] = None
    category: str = "beauty"

    @field_validator("handle")
    @classmethod
    def clean_handle(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("handle must not be empty")
        return v if v.startswith("@") else f"@{v}"


class FactorOut(BaseModel):
    key: str
    label: str
    description: str
    value: int
    weight: float
    contribution: float


class VerdictOut(BaseModel):
    verdict: str
    verdict_label: str
    reason: str
    action: str
    campaign_type: str
    budget_range: str
    risk: str
    warning_flags: list[str] = []


class RoiEstimateOut(BaseModel):
    estimated_reach_low: Optional[int]
    estimated_reach_high: Optional[int]
    estimated_conversions_low: Optional[int]
    estimated_conversions_high: Optional[int]
    confidence: str
    confidence_explanation: Optional[str] = None
    reach_explanation: Optional[str] = None
    conversion_explanation: Optional[str] = None
    note: str


class ScoreResponse(BaseModel):
    handle: str
    score: int
    label: str
    breakdown: list[FactorOut]
    insight: str
    mock: bool = True
    # Profile data (previously missing)
    followers: Optional[int] = None
    name: Optional[str] = None
    # Decision layer
    verdict: Optional[VerdictOut] = None
    roi_estimate: Optional[RoiEstimateOut] = None


class CheckoutRequest(BaseModel):
    plan: str
    user_email: str


class ReferralRequest(BaseModel):
    referrer_code: str   # btoa(referrer_email) from frontend
    new_email: str


REFERRAL_BONUS_REFERRER = 5
REFERRAL_BONUS_NEW      = 2


def get_user_usage(sb, email):
    r = sb.table("users").select("analyses_used,analyses_limit,plan").eq("email", email).execute()
    return r.data[0] if r.data else None


def increment_limit(sb, email, amount: int):
    u = sb.table("users").select("analyses_limit").eq("email", email).execute()
    if u.data:
        sb.table("users").update({"analyses_limit": u.data[0]["analyses_limit"] + amount}).eq("email", email).execute()


def increment_usage(sb, email):
    u = sb.table("users").select("analyses_used").eq("email", email).execute()
    if u.data:
        sb.table("users").update({"analyses_used": u.data[0]["analyses_used"] + 1}).eq("email", email).execute()


class OutreachRequest(BaseModel):
    handle: str
    name: Optional[str] = None
    followers: Optional[int] = None
    score: int
    niche: str = "beauty"
    collab_type: str = "gifted"  # "gifted" or "paid"
    brand_name: str = "[Brand name]"


@app.post("/outreach")
def generate_outreach(req: OutreachRequest, authorization: str = Header(default=None)):
    verify_token(authorization)
    claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    name = req.name or req.handle.lstrip("@").replace(".", " ").title()
    followers_str = f"{req.followers:,}" if req.followers else "unknown"
    collab_desc = "a paid sponsorship" if req.collab_type == "paid" else "a gifted product collaboration (no obligation to post)"
    tone = "professional and confident" if req.score >= 70 else "friendly and low-pressure"
    prompt = f"""Write a short Instagram DM outreach message from a beauty brand to an influencer.

Influencer details:
- Name: {name}
- Handle: {req.handle}
- Niche: {req.niche}
- Followers: {followers_str}
- Inflaid score: {req.score}/100
- Collaboration type: {collab_desc}
- Brand: {req.brand_name}

Requirements:
- Tone: {tone}
- Max 4 short paragraphs
- Start with "Hi {name},"
- Mention their specific niche naturally
- End with a clear, low-friction call to action
- Do NOT use generic phrases like "I came across your profile"
- Sound like a real human brand owner, not a template
- Return ONLY the message text, no subject line, no explanation"""

    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.strip()
    return {"message": text, "collab_type": req.collab_type}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/referral/apply")
def apply_referral(req: ReferralRequest):
    import base64
    from auth import get_supabase

    # Decode referrer email from code
    try:
        referrer_email = base64.b64decode(req.referrer_code.encode()).decode()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid referral code")

    if referrer_email == req.new_email:
        raise HTTPException(status_code=400, detail="Cannot refer yourself")

    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="DB unavailable")

    # Dedup check — stored as a special record in analyses table (no schema change needed)
    ref_handle = f"_ref:{req.new_email}"
    existing = sb.table("analyses").select("id").eq("handle", ref_handle).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Referral already applied")

    # Check referrer exists
    referrer = sb.table("users").select("email,analyses_limit").eq("email", referrer_email).execute()
    if not referrer.data:
        raise HTTPException(status_code=404, detail="Referrer not found")

    # Apply bonuses
    increment_limit(sb, referrer_email, REFERRAL_BONUS_REFERRER)
    increment_limit(sb, req.new_email, REFERRAL_BONUS_NEW)

    # Record referral in analyses table (handle=_ref:{email}, score=0, label=referral)
    sb.table("analyses").insert({
        "handle": ref_handle,
        "score": 0,
        "label": "referral",
        "result": {"referrer_email": referrer_email, "new_email": req.new_email},
    }).execute()

    return {"status": "applied", "referrer_bonus": REFERRAL_BONUS_REFERRER, "new_user_bonus": REFERRAL_BONUS_NEW}


@app.get("/public/profile/{handle}")
def public_profile(handle: str):
    """Public endpoint — returns cached score for a handle. No auth required."""
    from auth import get_supabase
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="DB unavailable")
    try:
        result = sb.table("analyses").select("result,created_at").eq("handle", handle).order("created_at", desc=True).limit(1).execute()
        if result.data:
            r = result.data[0]["result"]
            # Return only public-safe fields (no user data)
            return {
                "handle": r.get("handle"),
                "score": r.get("score"),
                "label": r.get("label"),
                "name": r.get("name"),
                "followers": r.get("followers"),
                "breakdown": r.get("breakdown", []),
                "insight": r.get("insight"),
                "verdict": r.get("verdict"),
                "roi_estimate": r.get("roi_estimate"),
                "cached_at": result.data[0]["created_at"],
            }
    except Exception as e:
        print(f"Public profile error: {e}")
    raise HTTPException(status_code=404, detail="Profile not found")



@app.post("/create-checkout")
def create_checkout(req: CheckoutRequest, authorization: str = Header(default=None)):
    email = verify_token(authorization)
    price_id = PLAN_PRICE_IDS.get(req.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {req.plan}")
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=email,
        metadata={"plan": req.plan},
        success_url=f"{FRONTEND_URL}/dashboard.html?upgraded=1",
        cancel_url=f"{FRONTEND_URL}/dashboard.html",
    )
    return {"url": session.url}


@app.post("/customer-portal")
def customer_portal(authorization: str = Header(default=None)):
    email = verify_token(authorization)
    customers = stripe.Customer.list(email=email, limit=1)
    if not customers.data:
        raise HTTPException(status_code=404, detail="no_subscription")
    portal = stripe.billing_portal.Session.create(
        customer=customers.data[0].id,
        return_url=f"{FRONTEND_URL}/dashboard.html",
    )
    return {"url": portal.url}


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest, authorization: str = Header(default=None)):
    from auth import get_cached, save_analysis, get_supabase

    email = verify_token(authorization)

    sb = get_supabase()

    # Get user record; create on first use (post-signup)
    u = get_user_usage(sb, email)
    if not u:
        sb.table("users").insert({
            "email": email,
            "plan": "free",
            "analyses_used": 0,
            "analyses_limit": PLAN_LIMITS["free"]
        }).execute()
        u = {"plan": "free", "analyses_used": 0, "analyses_limit": PLAN_LIMITS["free"]}

    # Enforce plan limit
    if u["analyses_limit"] > 0 and u["analyses_used"] >= u["analyses_limit"]:
        raise HTTPException(status_code=429, detail=f"limit_reached:{u['plan']}")

    # Cache check — still counts against usage
    cached = get_cached(req.handle)
    if cached:
        try:
            increment_usage(sb, email)
        except Exception as e:
            print(f"Usage increment error: {e}")
        return ScoreResponse(**cached)

    # Scrape + score
    try:
        raw = fetch_profile(req.handle, req.category)
    except PrivateAccountError:
        raise HTTPException(status_code=422, detail="private_account")
    except Exception as e:
        from scraper import ScraperError
        if isinstance(e, ScraperError):
            msg = str(e)
            if "timed out" in msg.lower():
                raise HTTPException(status_code=504, detail="scraper_timeout")
            if "no data" in msg.lower() or "incorrect" in msg.lower():
                raise HTTPException(status_code=404, detail="profile_not_found")
            raise HTTPException(status_code=502, detail=f"scraper_error:{msg}")
        raise HTTPException(status_code=502, detail=f"scraper_error:{e}")

    raw["handle"] = req.handle
    result = compute_score(raw)

    response = ScoreResponse(
        handle=result.handle,
        score=result.score,
        label=result.label,
        breakdown=[
            FactorOut(key=f["key"], label=f["label"], description=f["description"],
                      value=f["value"], weight=f["weight"], contribution=f["contribution"])
            for f in result.breakdown
        ],
        insight=result.insight,
        mock=raw.get("mock", True),
        followers=raw.get("followers") or None,
        name=raw.get("name") or None,
        verdict=VerdictOut(**result.verdict) if result.verdict else None,
        roi_estimate=RoiEstimateOut(**result.roi_estimate) if result.roi_estimate else None,
    )

    try:
        save_analysis(result.handle, result.score, result.label, response.model_dump(), email)
    except Exception as e:
        print(f"Cache save error: {e}")

    try:
        increment_usage(sb, email)
    except Exception as e:
        print(f"Usage increment error: {e}")

    return response


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email")
        plan = session.get("metadata", {}).get("plan", "starter")
        limit = PLAN_LIMITS.get(plan, 20)

        from auth import get_supabase
        sb = get_supabase()
        if sb and email:
            sb.table("users").upsert({
                "email": email,
                "plan": plan,
                "analyses_limit": limit
            }, on_conflict="email").execute()

    return {"status": "ok"}


# ── CAMPAIGN TRACKER ──────────────────────────────────────────────────────────

SPEND_MIDPOINTS = {
    "gifted": 0, "under100": 50,
    "100-500": 300, "500-2k": 1250, "2k+": 3000
}


class CampaignCreate(BaseModel):
    handle: str
    spend_tier: str   # gifted | under100 | 100-500 | 500-2k | 2k+
    outcome: str      # worth_it | meh | waste
    campaign_date: Optional[str] = None  # YYYY-MM-DD, defaults to today


class CampaignResult(BaseModel):
    campaign_id: str
    orders_range: Optional[str] = None   # 0 | 1-5 | 5-20 | 20+
    notes: Optional[str] = None


@app.post("/campaign/create")
def campaign_create(req: CampaignCreate, authorization: str = Header(default=None)):
    email = verify_token(authorization)
    from auth import get_supabase
    import datetime

    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="DB unavailable")

    record = {
        "user_email": email,
        "handle": req.handle if req.handle.startswith("@") else f"@{req.handle}",
        "spend_tier": req.spend_tier,
        "outcome": req.outcome,
        "campaign_date": req.campaign_date or datetime.date.today().isoformat(),
        "status": "logged",
    }
    result = sb.table("campaigns").insert(record).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save campaign")
    return {"status": "created", "id": result.data[0]["id"]}


@app.get("/campaigns")
def list_campaigns(authorization: str = Header(default=None)):
    email = verify_token(authorization)
    from auth import get_supabase

    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="DB unavailable")

    result = sb.table("campaigns").select("*").eq("user_email", email).order("campaign_date", desc=True).limit(50).execute()
    return {"campaigns": result.data or []}


@app.delete("/campaign/{campaign_id}")
def delete_campaign(campaign_id: str, authorization: str = Header(default=None)):
    email = verify_token(authorization)
    from auth import get_supabase

    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="DB unavailable")

    existing = sb.table("campaigns").select("id,user_email").eq("id", campaign_id).execute()
    if not existing.data or existing.data[0]["user_email"] != email:
        raise HTTPException(status_code=404, detail="Campaign not found")

    sb.table("campaigns").delete().eq("id", campaign_id).execute()
    return {"status": "deleted"}


@app.post("/campaign/{campaign_id}/result")
def campaign_result(campaign_id: str, req: CampaignResult, authorization: str = Header(default=None)):
    email = verify_token(authorization)
    from auth import get_supabase

    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="DB unavailable")

    # Verify ownership
    existing = sb.table("campaigns").select("id,user_email").eq("id", campaign_id).execute()
    if not existing.data or existing.data[0]["user_email"] != email:
        raise HTTPException(status_code=404, detail="Campaign not found")

    update = {"status": "completed"}
    if req.orders_range:
        update["orders_range"] = req.orders_range
    if req.notes:
        update["notes"] = req.notes

    sb.table("campaigns").update(update).eq("id", campaign_id).execute()
    return {"status": "updated"}
