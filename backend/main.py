import os
import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from scraper import fetch_profile
from scorer import compute_score

app = FastAPI(title="Vettly API", version="0.1.0")

ALLOWED_ORIGINS = ["*", "https://vettly-eight.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class ScoreRequest(BaseModel):
    handle: str
    user_email: str = None
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


class ScoreResponse(BaseModel):
    handle: str
    score: int
    label: str
    breakdown: list[FactorOut]
    insight: str
    mock: bool = True


class CheckoutRequest(BaseModel):
    plan: str
    user_email: str


def get_user_usage(sb, email):
    r = sb.table("users").select("analyses_used,analyses_limit,plan").eq("email", email).execute()
    return r.data[0] if r.data else None


def increment_usage(sb, email):
    u = sb.table("users").select("analyses_used").eq("email", email).execute()
    if u.data:
        sb.table("users").update({"analyses_used": u.data[0]["analyses_used"] + 1}).eq("email", email).execute()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug-raw/{handle}")
def debug_raw(handle: str):
    import os
    from apify_client import ApifyClient
    token = os.getenv("APIFY_TOKEN")
    if not token:
        return {"error": "no APIFY_TOKEN"}
    client = ApifyClient(token)
    run = client.actor("apify/instagram-profile-scraper").call(
        run_input={"usernames": [handle.lstrip("@")]}
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if not items:
        return {"error": "no items"}
    p = items[0]
    posts = p.get("latestPosts") or []
    return {
        "private": p.get("private"),
        "followersCount": p.get("followersCount"),
        "followsCount": p.get("followsCount"),
        "latestPosts_count": len(posts),
        "latestPosts_sample": posts[:2],
    }


@app.post("/create-checkout")
def create_checkout(req: CheckoutRequest):
    PRICE_IDS = {
        "pro": os.getenv("STRIPE_PRO_PRICE"),
        "growth": os.getenv("STRIPE_GROWTH_PRICE"),
    }
    price_id = PRICE_IDS.get(req.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {req.plan}")
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=req.user_email,
        success_url="https://vettly-eight.vercel.app/dashboard.html?upgraded=1",
        cancel_url="https://vettly-eight.vercel.app/dashboard.html",
    )
    return {"url": session.url}


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest):
    from auth import get_cached, save_analysis, get_supabase

    sb = get_supabase() if req.user_email else None

    # Check limit
    if sb and req.user_email:
        u = get_user_usage(sb, req.user_email)
        if u:
            if u["analyses_used"] >= u["analyses_limit"]:
                raise HTTPException(status_code=429, detail=f"limit_reached:{u['plan']}")
        else:
            sb.table("users").insert({"email": req.user_email, "plan": "free", "analyses_used": 0, "analyses_limit": 2}).execute()

    # Cache check
    cached = get_cached(req.handle)
    if cached:
        if sb and req.user_email:
            try:
                increment_usage(sb, req.user_email)
            except Exception as e:
                print(f"Usage increment error: {e}")
        return ScoreResponse(**cached)

    # Scrape + score
    try:
        raw = fetch_profile(req.handle, req.category)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scraper error: {e}")

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
    )

    try:
        save_analysis(result.handle, result.score, result.label, response.model_dump())
    except Exception as e:
        print(f"Cache save error: {e}")

    if sb and req.user_email:
        try:
            increment_usage(sb, req.user_email)
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

        pro_price = os.getenv("STRIPE_PRO_PRICE")
        plan = "growth" if session.get("amount_total") == 4900 else "pro"
        limit = 999999 if plan == "growth" else 50

        from auth import get_supabase
        sb = get_supabase()
        if sb and email:
            sb.table("users").upsert({
                "email": email,
                "plan": plan,
                "analyses_limit": limit
            }, on_conflict="email").execute()

    return {"status": "ok"}
