"""
Instagram scraper — Apify placeholder.

Real implementation will call the Apify Instagram Scraper actor
and return structured profile + post data.

Until then, mock data keyed by handle is returned so the rest of
the pipeline can be developed and tested end-to-end.
"""

import random

# ---------------------------------------------------------------------------
# Mock dataset
# Mirrors the 8 profiles used in the frontend.
# Keys are lowercase handles without @.
# ---------------------------------------------------------------------------
MOCK_PROFILES: dict[str, dict] = {
    "sophiareeves": {
        "handle": "@sophiareeves",
        "name": "Sophia Reeves",
        "followers": 15100,
        "platform": "instagram",
        "category": "skincare",
        "comment_quality": 92,
        "before_after_ratio": 88,
        "audience_fit": 85,
        "niche_consistency": 95,
        "authenticity_penalty": 100,
    },
    "chloepark": {
        "handle": "@chloepark",
        "name": "Chloe Park",
        "followers": 44800,
        "platform": "instagram",
        "category": "skincare",
        "comment_quality": 88,
        "before_after_ratio": 79,
        "audience_fit": 75,
        "niche_consistency": 90,
        "authenticity_penalty": 100,
    },
    "mayachen": {
        "handle": "@mayachen",
        "name": "Maya Chen",
        "followers": 118000,
        "platform": "instagram",
        "category": "makeup",
        "comment_quality": 72,
        "before_after_ratio": 85,
        "audience_fit": 70,
        "niche_consistency": 68,
        "authenticity_penalty": 95,
    },
    "zaraokafor": {
        "handle": "@zaraokafor",
        "name": "Zara Okafor",
        "followers": 67000,
        "platform": "instagram",
        "category": "makeup",
        "comment_quality": 35,
        "before_after_ratio": 62,
        "audience_fit": 60,
        "niche_consistency": 58,
        "authenticity_penalty": 95,
    },
    "lilysantos": {
        "handle": "@lilysantos",
        "name": "Lily Santos",
        "followers": 28300,
        "platform": "instagram",
        "category": "skincare",
        "comment_quality": 42,
        "before_after_ratio": 55,
        "audience_fit": 80,
        "niche_consistency": 75,
        "authenticity_penalty": 100,
    },
    "ninavoss": {
        "handle": "@ninavoss",
        "name": "Nina Voss",
        "followers": 89000,
        "platform": "instagram",
        "category": "fragrance",
        "comment_quality": 22,
        "before_after_ratio": 18,
        "audience_fit": 65,
        "niche_consistency": 55,
        "authenticity_penalty": 95,
    },
    "miatorres": {
        "handle": "@miatorres",
        "name": "Mia Torres",
        "followers": 203000,
        "platform": "tiktok",
        "category": "makeup",
        "comment_quality": 15,
        "before_after_ratio": 40,
        "audience_fit": 30,
        "niche_consistency": 45,
        "authenticity_penalty": 20,
    },
    "evakim": {
        "handle": "@evakim",
        "name": "Eva Kim",
        "followers": 312000,
        "platform": "instagram",
        "category": "makeup",
        "comment_quality": 8,
        "before_after_ratio": 25,
        "audience_fit": 40,
        "niche_consistency": 30,
        "authenticity_penalty": 10,
    },
}


def _normalize_handle(handle: str) -> str:
    return handle.lstrip("@").lower().strip()


def fetch_profile(handle: str) -> dict:
    """
    Fetch profile data for the given Instagram handle.

    Returns a dict with raw factor scores ready for scorer.compute_score().

    TODO: Replace mock lookup with real Apify actor call:
        client = ApifyClient(token=APIFY_TOKEN)
        run = client.actor("apify/instagram-scraper").call(
            run_input={"usernames": [handle], "resultsLimit": 50}
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return _parse_apify_response(items, handle)
    """
    key = _normalize_handle(handle)

    if key in MOCK_PROFILES:
        return {**MOCK_PROFILES[key], "handle": f"@{key}", "mock": True}

    # Unknown handle — generate plausible random data so the API never errors
    return _generate_random_profile(handle)


def _generate_random_profile(handle: str) -> dict:
    """Fallback for handles not in the mock dataset."""
    rng = random.Random(handle)  # deterministic per handle
    return {
        "handle": handle if handle.startswith("@") else f"@{handle}",
        "name": handle.lstrip("@").replace(".", " ").title(),
        "followers": rng.randint(10_000, 500_000),
        "platform": "instagram",
        "category": rng.choice(["skincare", "makeup", "haircare", "fragrance"]),
        "comment_quality": rng.randint(20, 90),
        "before_after_ratio": rng.randint(15, 85),
        "audience_fit": rng.randint(30, 90),
        "niche_consistency": rng.randint(30, 95),
        "authenticity_penalty": rng.randint(40, 100),
        "mock": True,
    }
