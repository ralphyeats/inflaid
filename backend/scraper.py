import os
import random
from datetime import datetime, timedelta
from apify_client import ApifyClient


class PrivateAccountError(Exception):
    pass


def _make_mock_posts(n=20, likes=500, comments=25, days_apart=3):
    posts = []
    base = datetime(2025, 1, 1, 12, 0, 0)
    for i in range(n):
        ts = base - timedelta(days=i * days_apart)
        posts.append({
            "likesCount": likes,
            "commentsCount": comments,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "caption": "skincare routine #skincare #beauty",
            "hashtags": ["skincare", "beauty"],
            "latestComments": [
                {"text": "Love this!", "ownerUsername": "fan1"},
                {"text": "Where to buy?", "ownerUsername": "fan2"},
            ],
        })
    return posts


MOCK_PROFILES = {
    "sophiareeves": {
        "handle": "@sophiareeves", "name": "Sophia Reeves",
        "followers": 15100, "following": 200,
        "posts": _make_mock_posts(n=24, likes=900, comments=45, days_apart=2),
        "is_business": False, "verified": False, "bio_url": "", "platform": "instagram",
    },
    "chloepark": {
        "handle": "@chloepark", "name": "Chloe Park",
        "followers": 44800, "following": 800,
        "posts": _make_mock_posts(n=24, likes=1340, comments=90, days_apart=3),
        "is_business": True, "verified": False, "bio_url": "https://chloepark.com", "platform": "instagram",
    },
    "mayachen": {
        "handle": "@mayachen", "name": "Maya Chen",
        "followers": 118000, "following": 2000,
        "posts": _make_mock_posts(n=24, likes=2500, comments=85, days_apart=4),
        "is_business": True, "verified": False, "bio_url": "", "platform": "instagram",
    },
    "zaraokafor": {
        "handle": "@zaraokafor", "name": "Zara Okafor",
        "followers": 67000, "following": 55000,
        "posts": _make_mock_posts(n=24, likes=235, comments=15, days_apart=7),
        "is_business": False, "verified": False, "bio_url": "", "platform": "instagram",
    },
    "lilysantos": {
        "handle": "@lilysantos", "name": "Lily Santos",
        "followers": 28300, "following": 1200,
        "posts": _make_mock_posts(n=20, likes=850, comments=40, days_apart=5),
        "is_business": False, "verified": False, "bio_url": "", "platform": "instagram",
    },
    "ninavoss": {
        "handle": "@ninavoss", "name": "Nina Voss",
        "followers": 89000, "following": 500,
        "posts": _make_mock_posts(n=8, likes=180, comments=8, days_apart=30),
        "is_business": False, "verified": False, "bio_url": "", "platform": "instagram",
    },
    "miatorres": {
        "handle": "@miatorres", "name": "Mia Torres",
        "followers": 203000, "following": 180000,
        "posts": _make_mock_posts(n=24, likes=305, comments=12, days_apart=14),
        "is_business": True, "verified": False, "bio_url": "", "platform": "instagram",
    },
    "evakim": {
        "handle": "@evakim", "name": "Eva Kim",
        "followers": 312000, "following": 290000,
        "posts": _make_mock_posts(n=24, likes=25, comments=3, days_apart=3),
        "is_business": True, "verified": False, "bio_url": "", "platform": "instagram",
    },
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
            run_input={"usernames": [handle.lstrip("@")], "maxPosts": 24}
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        if not items:
            return None

        p = items[0]
        if p.get("private"):
            raise PrivateAccountError(handle)
        followers = p.get("followersCount") or 1
        following = p.get("followsCount") or 1
        posts = p.get("latestPosts") or []
        is_business = p.get("isBusinessAccount") or False

        bio_links = p.get("bioLinks") or []
        bio_url = bio_links[0].get("url", "") if bio_links else (p.get("externalUrl") or "")

        return {
            "handle": f'@{handle.lstrip("@")}',
            "name": p.get("fullName") or handle,
            "followers": followers,
            "following": following,
            "posts": posts,
            "is_business": is_business,
            "verified": p.get("verified") or False,
            "bio_url": bio_url,
            "platform": "instagram",
            "mock": False,
        }
    except Exception as e:
        print(f"Apify error: {e}")
        return None


def fetch_profile(handle, category="beauty"):
    key = _normalize_handle(handle)
    real = _fetch_apify(key)
    if real:
        real["category"] = category
        return real
    if key in MOCK_PROFILES:
        profile = {**MOCK_PROFILES[key], "handle": f"@{key}", "mock": True, "category": category}
        return profile
    profile = _generate_random_profile(handle)
    profile["category"] = category
    return profile


def _generate_random_profile(handle):
    rng = random.Random(handle)
    n_posts = rng.randint(12, 30)
    likes = rng.randint(100, 5000)
    comments = rng.randint(5, 200)
    days = rng.randint(2, 10)
    base = datetime(2025, 1, 1, 12, 0, 0)
    posts = []
    for i in range(n_posts):
        ts = base - timedelta(days=i * days)
        posts.append({
            "likesCount": likes + rng.randint(-likes // 3, likes // 3),
            "commentsCount": comments + rng.randint(-comments // 3, comments // 3),
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "caption": rng.choice(["skincare routine #skincare", "my beauty tips", "everyday makeup look"]),
            "hashtags": ["skincare", "beauty"],
            "latestComments": [{"text": "Love this!", "ownerUsername": "fan1"}],
        })
    return {
        "handle": handle if handle.startswith("@") else f"@{handle}",
        "name": handle.lstrip("@").replace(".", " ").title(),
        "followers": rng.randint(10_000, 500_000),
        "following": rng.randint(100, 5_000),
        "posts": posts,
        "is_business": rng.choice([True, False]),
        "verified": False,
        "bio_url": "",
        "platform": "instagram",
        "mock": True,
    }
