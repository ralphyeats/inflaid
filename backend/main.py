import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from scraper import fetch_profile
from scorer import compute_score, FactorResult

app = FastAPI(title="Vettly API", version="0.1.0")

# ALLOWED_ORIGINS env var: comma-separated list, e.g.
# "https://vettly.vercel.app,https://vettly-git-main-xyz.vercel.app"
# Defaults to "*" for local development.
ALLOWED_ORIGINS = [
    "*",
    "https://vettly-eight.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────────────────────

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


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest):
    try:
        raw = fetch_profile(req.handle)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scraper error: {e}")

    raw["handle"] = req.handle
    result = compute_score(raw)

    return ScoreResponse(
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

@app.post("/test")
def test_post():
    return {"status": "ok", "method": "POST"}

@app.post("/debug")
def debug(req: ScoreRequest):
    import os
    from apify_client import ApifyClient
    token = os.getenv("APIFY_TOKEN")
    client = ApifyClient(token)
    run = client.actor("apify/instagram-scraper").call(
        run_input={"usernames": [req.handle.lstrip("@")], "resultsLimit": 3}
    )
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if items:
        return {"keys": list(items[0].keys()), "sample": items[0]}
    return {"error": "no items"}
