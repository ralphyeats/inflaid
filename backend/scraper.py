import os
import random
from apify_client import ApifyClient

MOCK_PROFILES = {
    "sophiareeves": {"handle": "@sophiareeves", "name": "Sophia Reeves", "followers": 15100, "platform": "instagram", "category": "skincare", "comment_quality": 92, "before_after_ratio": 88, "audience_fit": 85, "niche_consistency": 95, "authenticity_penalty": 100},
    "chloepark": {"handle": "@chloepark", "name": "Chloe Park", "followers": 44800, "platform": "instagram", "category": "skincare", "comment_quality": 88, "before_after_ratio": 79, "audience_fit": 75, "niche_consistency": 90, "authenticity_penalty": 100},
    "mayachen": {"handle": "@mayachen", "name": "Maya Chen", "followers": 118000, "platform": "instagram", "category": "makeup", "comment_quality": 72, "before_after_ratio": 85, "audience_fit": 70, "niche_consistency": 68, "authenticity_penalty": 95},
    "zaraokafor": {"handle": "@zaraokafor", "name": "Zara Okafor", "followers": 67000, "platform": "instagram", "category": "makeup", "comment_quality": 35, "before_after_ratio": 62, "audience_fit": 60, "niche_consistency": 58, "authenticity_penalty": 95},
    "lilysantos": {"handle": "@lilysantos", "name": "Lily Santos", "followers": 28300, "platform": "instagram", "category": "skincare", "comment_quality": 42, "before_after_ratio": 55, "audience_fit": 80, "niche_consistency": 75, "authenticity_penalty": 100},
    "ninavoss": {"handle": "@ninavoss", "name": "Nina Voss", "followers": 89000, "platform": "instagram", "category": "fragrance", "comment_quality": 22, "before_after_ratio": 18, "audience_fit": 65, "niche_consistency": 55, "authenticity_penalty": 95},
    "miatorres": {"handle": "@miatorres", "name": "Mia Torres", "followers": 203000, "platform": "tiktok", "category": "makeup", "comment_quality": 15, "before_after_ratio": 40, "audience_fit": 30, "niche_consistency": 45, "authenticity_penalty": 20},
    "evakim": {"handle": "@evakim", "name": "Eva Kim", "followers": 312000, "platform": "instagram", "category": "makeup", "comment_quality": 8, "before_after_ratio": 25, "audience_fit": 40, "niche_consistency": 30, "authenticity_penalty": 10},
}

def _normalize_handle(handle):
    return handle.lstrip("@").lower().strip()

def _fetch_apify(handle):
    token = os.getenv("APIFY_TOKEN")
    if not token:
        return None
    try:
        client = ApifyClient(token)
        run = client.actor("apify/instagram-profile-scraper").call(
            run_input={"usernames": [handle.lstrip("@")]}
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return None

        p = items[0]
        followers = p.get("followersCount") or 1
        following = p.get("followsCount") or 1
        posts_count = p.get("postsCount") or 0
        posts = p.get("latestPosts") or []
        is_business = p.get("isBusinessAccount") or False

        # 1. ENGAGEMENT RATE (35%)
        # Micro-influencer benchmark: 3-6% good, >6% excellent, <2% poor
        total_likes = sum(post.get("likesCount") or 0 for post in posts)
        total_comments = sum(post.get("commentsCount") or 0 for post in posts)
        total_views = sum(post.get("videoViewCount") or 0 for post in posts)
        n = len(posts) if posts else 1
        avg_engagement = (total_likes + total_comments) / n
        engagement_rate = (avg_engagement / followers * 100) if followers > 0 else 0
        # Score: 0-1% = 20, 1-2% = 40, 2-4% = 60, 4-6% = 80, 6%+ = 100
        if engagement_rate >= 6:
            comment_quality = 100
        elif engagement_rate >= 4:
            comment_quality = 80
        elif engagement_rate >= 2:
            comment_quality = 60
        elif engagement_rate >= 1:
            comment_quality = 40
        else:
            comment_quality = 20

        # 2. CONTENT CONSISTENCY - posts per week (25%)
        # Check how recently they posted
        recent_posts = len(posts)
        if recent_posts >= 20:
            before_after_ratio = 90
        elif recent_posts >= 12:
            before_after_ratio = 70
        elif recent_posts >= 6:
            before_after_ratio = 50
        else:
            before_after_ratio = 30

        # 3. AUDIENCE QUALITY - follower/following ratio (20%)
        ff_ratio = followers / following if following > 0 else 1
        if ff_ratio >= 10:
            audience_fit = 95
        elif ff_ratio >= 5:
            audience_fit = 80
        elif ff_ratio >= 2:
            audience_fit = 65
        elif ff_ratio >= 1:
            audience_fit = 50
        else:
            audience_fit = 30

        # 4. NICHE CONSISTENCY - hashtag analysis (15%)
        beauty_keywords = [
            "skincare", "makeup", "beauty", "skin", "glow", "routine", "serum",
            "moisturizer", "foundation", "lipstick", "hair", "cosmetic", "fashion", "style",
            "makyaj", "guzellik", "cilt", "ruj", "fondoten", "kirpik", "kas", "sac",
            "макияж", "красота", "уход", "косметика", "кожа", "помада",
            "beaute", "maquillage", "soin", "cheveux",
            "belleza", "maquillaje", "cabello"
        ]
        niche_count = 0
        for post in posts:
            caption = (post.get("caption") or "").lower()
            hashtags = [h.lower() for h in (post.get("hashtags") or [])]
            all_text = caption + " " + " ".join(hashtags)
            if any(k in all_text for k in beauty_keywords):
                niche_count += 1
        niche_consistency = int(niche_count / len(posts) * 100) if posts else 50

        # 5. AUTHENTICITY (penalty -5%)
        # Business account + verified + good follower ratio = authentic
        auth_score = 85
        if is_business:
            auth_score += 5
        if p.get("verified"):
            auth_score += 5
        if ff_ratio >= 5:
            auth_score += 5
        auth_score = min(100, auth_score)

        return {
            "handle": f'@{handle.lstrip("@")}',
            "name": p.get("fullName") or handle,
            "followers": followers,
            "platform": "instagram",
            "category": "beauty",
            "comment_quality": comment_quality,
            "before_after_ratio": before_after_ratio,
            "audience_fit": audience_fit,
            "niche_consistency": niche_consistency,
            "authenticity_penalty": auth_score,
            "mock": False,
        }
    except Exception as e:
        print(f"Apify error: {e}")
        return None

def fetch_profile(handle):
    key = _normalize_handle(handle)
    real = _fetch_apify(key)
    if real:
        return real
    if key in MOCK_PROFILES:
        return {**MOCK_PROFILES[key], "handle": f"@{key}", "mock": True}
    return _generate_random_profile(handle)

def _generate_random_profile(handle):
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
