import os
import random
from datetime import datetime, timedelta
from apify_client import ApifyClient


class PrivateAccountError(Exception):
    pass


class ScraperError(Exception):
    """Raised when Apify fails and no fallback is appropriate."""
    def __init__(self, message: str, retriable: bool = True):
        super().__init__(message)
        self.retriable = retriable


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


def _fetch_apify(handle: str, timeout_secs: int = 90) -> dict:
    """
    Fetch live profile from Apify.
    Raises:
        PrivateAccountError — account is private, will not retry
        ScraperError        — retriable failure (timeout, rate limit, empty result)
    Returns None only when APIFY_TOKEN is missing (dev mode).
    """
    token = os.getenv("APIFY_TOKEN")
    if not token:
        return None  # type: ignore[return-value]  — dev mode, caller handles None

    client = ApifyClient(token)
    try:
        run = client.actor("apify/instagram-profile-scraper").call(
            run_input={"usernames": [handle.lstrip("@")], "resultsLimit": 24},
            timeout_secs=timeout_secs,
        )
    except Exception as e:
        msg = str(e).lower()
        if "timeout" in msg or "timed out" in msg:
            raise ScraperError(f"Apify timed out after {timeout_secs}s", retriable=True)
        raise ScraperError(f"Apify actor failed: {e}", retriable=True)

    try:
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    except Exception as e:
        raise ScraperError(f"Could not read Apify dataset: {e}", retriable=True)

    if not items:
        raise ScraperError("Apify returned no data for this handle", retriable=False)

    p = items[0]

    # Private account — never retriable
    if p.get("private"):
        raise PrivateAccountError(handle)

    # Empty / blocked profile (Apify sometimes returns a skeleton)
    followers = p.get("followersCount")
    if followers is None and not p.get("fullName"):
        raise ScraperError(
            "Profile data is empty — account may be restricted or the handle is incorrect",
            retriable=False,
        )

    following = p.get("followsCount") or 0
    posts = p.get("latestPosts") or []
    is_business = p.get("isBusinessAccount") or False
    bio_links = p.get("bioLinks") or []
    bio_url = bio_links[0].get("url", "") if bio_links else (p.get("externalUrl") or "")

    return {
        "handle": f'@{handle.lstrip("@")}',
        "name": p.get("fullName") or handle,
        "followers": followers or 0,
        "following": following,
        "posts": posts,
        "is_business": is_business,
        "verified": p.get("verified") or False,
        "bio_url": bio_url,
        "platform": "instagram",
        "mock": False,
        "data_source": "live",
    }


def _fetch_apify_with_retry(handle: str, retries: int = 1) -> dict:
    """Retry once on retriable ScraperErrors."""
    last_err: ScraperError = ScraperError("Scraper failed after retries")
    for attempt in range(retries + 1):
        try:
            return _fetch_apify(handle)
        except PrivateAccountError:
            raise  # never retry private accounts
        except ScraperError as e:
            last_err = e
            if not e.retriable:
                raise
            if attempt < retries:
                print(f"Scraper attempt {attempt + 1} failed ({e}), retrying...")
    raise last_err


def fetch_profile(handle: str, category: str = "beauty") -> dict:
    """
    Fetch profile data. Priority:
      1. Live Apify data
      2. Named mock profile (dev/demo handles)
      3. Raise — do NOT silently generate random fake data for unknown handles

    Callers must handle PrivateAccountError and ScraperError.
    """
    key = _normalize_handle(handle)

    # Try live first
    try:
        real = _fetch_apify_with_retry(key)
        if real:
            real["category"] = category
            return real
    except (PrivateAccountError, ScraperError):
        raise  # propagate to main.py for proper HTTP error responses

    # APIFY_TOKEN not set — dev mode, fall through to mocks
    if key in MOCK_PROFILES:
        profile = {**MOCK_PROFILES[key], "handle": f"@{key}", "mock": True,
                   "data_source": "mock_named", "category": category}
        return profile

    # Unknown handle in dev mode — generate deterministic mock
    profile = _generate_random_profile(handle)
    profile["category"] = category
    profile["data_source"] = "mock_random"
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
