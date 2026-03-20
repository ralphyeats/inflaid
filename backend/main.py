import os

import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRICE_IDS = {
    "pro": os.getenv("STRIPE_PRO_PRICE"),
    "growth": os.getenv("STRIPE_GROWTH_PRICE"),
}

class CheckoutRequest(BaseModel):
    plan: str
    user_email: str

@app.post("/create-checkout")
def create_checkout(req: CheckoutRequest):
    price_id = PRICE_IDS.get(req.plan)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid plan")
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=req.user_email,
        success_url="https://vettly-eight.vercel.app/dashboard.html?upgraded=1",
        cancel_url="https://vettly-eight.vercel.app/dashboard.html",
    )
    return {"url": session.url}
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from scraper import fetch_profile
from scorer import compute_score, FactorResult

app = FastAPI(title="Vettly API", version="0.1.0")

ALLOWED_ORIGINS = ["*", "https://vettly-eight.vercel.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScoreRequest(BaseModel):
    handle: str
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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest):
    from auth import get_cached, save_analysis
    cached = get_cached(req.handle)
    if cached:
        return ScoreResponse(**cached)

    try:
        raw = fetch_profile(req.handle)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scraper error: {e}")

    raw["handle"] = req.handle
    result = compute_score(raw)

    response = ScoreResponse(
        handle=result.handle,
        score=result.score,
        label=result.label,
        breakdown=[
            FactorOut(
                key=f.key,
                label=f.label,
                description=f.description,
                value=f.value,
                weight=f.weight,
                contribution=f.contribution,
            )
            for f in result.breakdown
        ],
        insight=result.insight,
        mock=raw.get("mock", True),
    )

    try:
        save_analysis(result.handle, result.score, result.label, response.model_dump())
    except Exception as e:
        print(f"Cache save error: {e}")

    return response
