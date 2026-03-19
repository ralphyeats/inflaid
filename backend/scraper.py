import os
import random
from apify_client import ApifyClient

MOCK_PROFILES: dict[str, dict] = {
    "sophiareeves": {"handle": "@sophiareeves", "name": "Sophia Reeves", "followers": 15100, "platform": "instagram", "category": "skincare", "comment_quality": 92, "before_after_ratio": 88, "audience_fit": 85, "niche_consistency": 95, "authenticity_penalty": 100},
    "chloepark": {"handle": "@chloepark", "name": "Chloe Park", "followers": 44800, "platform": "instagram", "category": "skincare", "comment_quality": 88, "before_after_ratio": 79, "audience_fit": 75, "niche_consistency": 90, "authenticity_penalty": 100},
    "mayachen": {"handle": "@mayachen", "name": "Maya Chen", "followers": 118000, "platform": "instagram", "category": "makeup", "comment_quality": 72, "before_after_ratio": 85, "audience_fit": 70, "niche_consistency": 68, "authenticity_penalty": 95},
    "zaraokafor": {"handle": "@zaraokafor", "name": "Zara Okafor", "followers": 67000, "platform": "instagram", "category": "makeup", "comment_quality": 35, "before_after_ratio": 62, "audience_fit": 60, "niche_consistency": 58, "authenticity_penalty": 95},
    "lilysantos": {"handle": "@lilysantos", "name": "Lily Santos", "followers": 28300, "platform": "instagram", "category": "skincare", "comment_quality": 42, "before_after_ratio": 55, "audience_fit": 80, "niche_consistency": 75, "authenticity_penalty": 100},
    "ninavoss": {"handle": "@ninavoss", "name": "Nina Voss", "followers": 89000, "platform": "instagram", "category": "fragrance", "comment_quality": 22, "before_after_ratio": 18, "audience_fit": 65, "niche_consistency": 55, "authenticity_penalty": 95},
    "miatorres": {"handle": "@miatorres", "name": "Mia Torres", "followers": 203000, "platform": "tiktok", "category": "makeup", "comment_quality": 15, "before_after_ratio": 40, "audience_fit": 30, "niche_consistency": 45, "authenticity_penalty": 20},
    "evakim": {"handle": "@evakim", "name": "Eva Kim", "followers": 312000, "platform": "instagram", "category": "makeup", "comment_quality": 8, "before_after_ratio": 25, "audience_fit": 40, "niche_consistency": 30, "authenticity_penalty": 10},
}

def _normalize_handle(handle: str) -> str:
    return handle.lstrip("@").lower().strip()

def _fetch_apify(handle: str) -> dict | None:
    token = os.getenv("APIFY_TOKEN")
    if not token:
        return None
    try:
        client = ApifyClient(token)
        run = client.actor("apify/instagram-scraper").call(
            run_input={"usernames": [handle.lstrip("@")], "resultsLimit": 30}
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return None
        profile = items[0]
        posts = items[1:] if len(items) > 1 else []

        followers = profile.get("followersCount", 10000)
        
        # comment quality: ratio of comments with "?" or product keywords
        product_keywords = ["where", "link", "buy", "price", "how much", "shop", "use", "work", "worth"]
        total_comments = 0
        product_comments = 0
        for post in posts:
            for c in post.get("latestComments", []):
                text = c.get("text", "").lower()
                total_comments += 1
                if any(k in text for k in product_keywords) or "?" in text:
                    product_comments += 1
        comment_quality = int((product_comments / total_comments * 100)) if total_comments > 0 else 50

        # before/after ratio
        ba_keywords = ["before", "after", "results", "transformation", "progress", "difference"]
        ba_count = sum(1 for p in posts if any(k in (p.get("caption") or "").lower() for k in ba_keywords))
        before_after_ratio = int(ba_count / len(posts) * 100) if posts else 50

        # niche consistency
        beauty_keywords = ["skincare", "makeup", "beauty", "skin", "glow", "routine", "serum", "moisturizer", "foundation", "lipstick", "hair"]
        niche_count = sum(1 for p in posts if any(k in (p.get("caption") or "").lower() for k in beauty_keywords))
        niche_consistency = int(niche_count / len(posts) * 100) if posts else 50

        # audience fit: use engagement rate as proxy
        avg_likes = sum(p.get("likesCount", 0) for p in posts) / len(posts) if posts else 0
        engagement_rate = (avg_likes / followers * 100) if followers > 0 else 0
        audience_fit = min(100, int(engagement_rate * 10))

        # authenticity: check for sudden follower spikes (simplified)
        authenticity_penalty = 85  # default neutral

        return {
            "handle": f"@{handle.lstrip('@')}",
            "name": profile.get("fullName", handle),
            "followers": followers,
            "platform": "instagram",
            "category": "beauty",
            "comment_quality": comment_quality,
            "before_after_ratio": before_after_ratio,
            "audience_fit": audience_fit,
            "niche_consistency": niche_consistency,
            "authenticity_penalty": authenticity_penalty,
            "mock": False,
        }
    except Exception as e:
        print(f"Apify error: {e}")
        return None

def fetch_profile(handle: str) -> dict:
    key = _normalize_handle(handle)
    
    # Try real Apify data first
    real = _fetch_apify(key)
    if real:
        return real
    
    # Fall back to mock
    if key in MOCK_PROFILES:
        return {**MOCK_PROFILES[key], "handle": f"@{key}", "mock": True}
    
    return _generate_random_profile(handle)

def _generate_random_profile(handle: str) -> dict:
    rng = random.Random(handle)
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
