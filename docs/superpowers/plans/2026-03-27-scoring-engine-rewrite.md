# Scoring Engine Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 5-factor step-function scoring system with a 7-factor modular system featuring continuous signals, a fraud multiplier, and Claude Sonnet 4.6 comment sentiment analysis.

**Architecture:** Modular `factors/` package where each factor is an independent function `score_X(raw: dict) -> int`. A rewritten `scorer.py` orchestrates all factors, applies the fraud multiplier, and returns a `ScoreResult`. `scraper.py` is stripped of all scoring logic and returns raw Apify data only.

**Tech Stack:** Python 3.11, FastAPI, pytest, anthropic SDK, Apify, Supabase

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/requirements.txt` | Modify | Add `anthropic>=0.25.0` |
| `backend/scraper.py` | Modify | Remove factor calculations; return raw profile dict |
| `backend/scorer.py` | Rewrite | Orchestrate all factor modules, apply fraud multiplier |
| `backend/factors/__init__.py` | Create | Empty package marker |
| `backend/factors/engagement.py` | Create | Engagement quality score (30%) |
| `backend/factors/rhythm.py` | Create | Content rhythm score (20%) |
| `backend/factors/audience.py` | Create | Audience reliability score (20%) |
| `backend/factors/niche.py` | Create | Niche depth score (15%) |
| `backend/factors/authenticity.py` | Create | Authenticity / red flags score (10%) |
| `backend/factors/momentum.py` | Create | Growth momentum score (5%) |
| `backend/factors/fraud.py` | Create | Fraud multiplier (0.40–1.0) |
| `backend/factors/sentiment.py` | Create | Claude Sonnet 4.6 comment sentiment, daily cap 50 |
| `backend/main.py` | Modify | Add `category` field to `ScoreRequest` |
| `backend/tests/__init__.py` | Create | Empty test package marker |
| `backend/tests/conftest.py` | Create | Shared pytest fixtures |
| `backend/tests/test_engagement.py` | Create | Unit tests for engagement factor |
| `backend/tests/test_rhythm.py` | Create | Unit tests for rhythm factor |
| `backend/tests/test_audience.py` | Create | Unit tests for audience factor |
| `backend/tests/test_niche.py` | Create | Unit tests for niche factor |
| `backend/tests/test_authenticity.py` | Create | Unit tests for authenticity factor |
| `backend/tests/test_momentum.py` | Create | Unit tests for momentum factor |
| `backend/tests/test_fraud.py` | Create | Unit tests for fraud multiplier |
| `backend/tests/test_sentiment.py` | Create | Unit tests for sentiment (no API calls) |
| `backend/tests/test_scorer.py` | Create | Integration tests for scorer orchestrator |
| `dashboard.html` | Modify | Fix duplicate analyzeHandle, update LBL to 5 labels |

---

## Task 1: Add anthropic dependency and test infrastructure

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Add anthropic to requirements.txt**

Replace the contents of `backend/requirements.txt`:
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
pydantic>=2.7.0
apify-client>=1.7.0
supabase>=2.0.0
stripe>=7.0.0
anthropic>=0.25.0
pytest>=8.0.0
```

- [ ] **Step 2: Install dependencies**

```bash
cd backend
pip install anthropic pytest
```

Expected: no errors.

- [ ] **Step 3: Create test package marker**

Create `backend/tests/__init__.py` — empty file.

- [ ] **Step 4: Create shared fixtures**

Create `backend/tests/conftest.py`:
```python
import pytest
from datetime import datetime, timedelta


def make_posts(n=20, likes=500, comments=25, days_apart=3, hashtags=None, captions=None):
    """Generate n fake posts with consistent timestamps."""
    posts = []
    base = datetime(2025, 1, 1, 12, 0, 0)
    for i in range(n):
        ts = base - timedelta(days=i * days_apart)
        posts.append({
            "likesCount": likes,
            "commentsCount": comments,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "caption": captions[i] if captions and i < len(captions) else "skincare routine #skincare",
            "hashtags": hashtags[i] if hashtags and i < len(hashtags) else ["skincare", "beauty"],
            "latestComments": [
                {"text": "Love this product!", "ownerUsername": "user1"},
                {"text": "Where can I buy this?", "ownerUsername": "user2"},
            ],
        })
    return posts


@pytest.fixture
def clean_profile():
    """A healthy beauty influencer profile."""
    return {
        "handle": "@testuser",
        "name": "Test User",
        "followers": 50000,
        "following": 500,
        "posts": make_posts(n=24, likes=1500, comments=75, days_apart=3),
        "is_business": False,
        "verified": False,
        "bio_url": "",
        "platform": "instagram",
        "mock": True,
    }


@pytest.fixture
def ghost_profile():
    """A profile with ghost followers (very low engagement for follower count)."""
    return {
        "handle": "@ghostuser",
        "name": "Ghost User",
        "followers": 500000,
        "following": 300,
        "posts": make_posts(n=24, likes=50, comments=2, days_apart=3),
        "is_business": False,
        "verified": False,
        "bio_url": "",
        "platform": "instagram",
        "mock": True,
    }
```

- [ ] **Step 5: Verify pytest works**

```bash
cd backend
pytest tests/ -v
```

Expected: "no tests ran" or 0 items collected — no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/tests/
git commit -m "chore: add anthropic dependency and test infrastructure"
```

---

## Task 2: factors/engagement.py

**Files:**
- Create: `backend/factors/__init__.py`
- Create: `backend/factors/engagement.py`
- Create: `backend/tests/test_engagement.py`

- [ ] **Step 1: Create factors package**

Create `backend/factors/__init__.py` — empty file.

- [ ] **Step 2: Write failing tests**

Create `backend/tests/test_engagement.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factors.engagement import score_engagement


def make_raw(followers=10000, n=20, likes=300, comments=15, variable_likes=None):
    posts = []
    for i in range(n):
        posts.append({
            "likesCount": variable_likes[i] if variable_likes else likes,
            "commentsCount": comments,
        })
    return {"followers": followers, "posts": posts}


def test_high_engagement_rate():
    # 315/10000 * 100 = 3.15% → raw_score = 3.15 * 12 = 37.8 → + comment bonus
    raw = make_raw(followers=10000, likes=300, comments=15, n=20)
    score = score_engagement(raw)
    assert score > 40


def test_very_high_engagement_rate():
    # 600/10000 * 100 = 6% → raw_score capped at 100
    raw = make_raw(followers=10000, likes=590, comments=10, n=20)
    score = score_engagement(raw)
    assert score >= 95


def test_low_engagement_rate():
    # 5/100000 * 100 = 0.005% → raw_score near 0
    raw = make_raw(followers=100000, likes=4, comments=1, n=20)
    score = score_engagement(raw)
    assert score < 25


def test_high_comment_ratio_gives_bonus():
    # comment_ratio = 60/300 = 0.2 >= 0.05 → +15 bonus
    low_comment = make_raw(followers=10000, likes=300, comments=6, n=20)   # ratio=0.02
    high_comment = make_raw(followers=10000, likes=300, comments=60, n=20) # ratio=0.2
    assert score_engagement(high_comment) > score_engagement(low_comment)


def test_high_variance_gives_penalty():
    # One post has 10x average → spike detected
    normal_likes = [100] * 19 + [1000]
    raw_spiky = make_raw(followers=10000, n=20, variable_likes=normal_likes, comments=5)
    raw_stable = make_raw(followers=10000, n=20, likes=100, comments=5)
    assert score_engagement(raw_spiky) < score_engagement(raw_stable)


def test_empty_posts_returns_50():
    raw = {"followers": 10000, "posts": []}
    assert score_engagement(raw) == 50


def test_score_bounded_0_to_100():
    raw_extreme = make_raw(followers=100, likes=10000, comments=5000, n=20)
    score = score_engagement(raw_extreme)
    assert 0 <= score <= 100
```

- [ ] **Step 3: Run to confirm failure**

```bash
cd backend
pytest tests/test_engagement.py -v
```

Expected: `ModuleNotFoundError: No module named 'factors'`

- [ ] **Step 4: Implement engagement.py**

Create `backend/factors/engagement.py`:
```python
def score_engagement(raw: dict) -> int:
    posts = raw.get("posts", [])
    followers = raw.get("followers", 1)

    if not posts:
        return 50

    n = len(posts)
    avg_likes = sum(p.get("likesCount", 0) for p in posts) / n
    avg_comments = sum(p.get("commentsCount", 0) for p in posts) / n

    engagement_rate = (avg_likes + avg_comments) / max(followers, 1) * 100
    raw_score = min(100, engagement_rate * 12)

    comment_ratio = avg_comments / (avg_likes + 1)
    if comment_ratio >= 0.05:
        quality_bonus = 15
    elif comment_ratio >= 0.02:
        quality_bonus = 8
    else:
        quality_bonus = 0

    engagements = [p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts]
    if len(engagements) > 1:
        mean_e = sum(engagements) / len(engagements)
        std_e = (sum((e - mean_e) ** 2 for e in engagements) / len(engagements)) ** 0.5
        variance_ratio = std_e / (mean_e + 1)
        if variance_ratio > 2.0:
            variance_penalty = -15
        elif variance_ratio > 1.0:
            variance_penalty = -7
        else:
            variance_penalty = 0
    else:
        variance_penalty = 0

    return min(100, max(0, int(raw_score + quality_bonus + variance_penalty)))
```

- [ ] **Step 5: Run tests — confirm pass**

```bash
cd backend
pytest tests/test_engagement.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/factors/ backend/tests/test_engagement.py
git commit -m "feat: add engagement factor module (30%)"
```

---

## Task 3: factors/rhythm.py

**Files:**
- Create: `backend/factors/rhythm.py`
- Create: `backend/tests/test_rhythm.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_rhythm.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from factors.rhythm import score_rhythm


def make_posts_with_interval(n=20, days_apart=3):
    posts = []
    base = datetime(2025, 1, 1, 12, 0, 0)
    for i in range(n):
        ts = base - timedelta(days=i * days_apart)
        posts.append({"timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")})
    return posts


def test_daily_posts_high_score():
    raw = {"posts": make_posts_with_interval(n=20, days_apart=1)}
    assert score_rhythm(raw) >= 85


def test_weekly_posts_mid_score():
    raw = {"posts": make_posts_with_interval(n=20, days_apart=7)}
    score = score_rhythm(raw)
    assert 60 <= score <= 80


def test_monthly_posts_low_score():
    raw = {"posts": make_posts_with_interval(n=10, days_apart=30)}
    assert score_rhythm(raw) <= 25


def test_consistent_interval_bonus():
    consistent = {"posts": make_posts_with_interval(n=20, days_apart=3)}
    # Irregular: alternate 1 day and 9 days = avg ~5 but high std dev
    posts_irregular = []
    base = datetime(2025, 1, 1)
    t = base
    for i in range(20):
        posts_irregular.append({"timestamp": t.strftime("%Y-%m-%dT%H:%M:%S.000Z")})
        t -= timedelta(days=1 if i % 2 == 0 else 9)
    irregular = {"posts": posts_irregular}
    assert score_rhythm(consistent) > score_rhythm(irregular)


def test_single_post_returns_50():
    raw = {"posts": [{"timestamp": "2025-01-01T12:00:00.000Z"}]}
    assert score_rhythm(raw) == 50


def test_no_posts_returns_50():
    assert score_rhythm({"posts": []}) == 50


def test_score_bounded():
    raw = {"posts": make_posts_with_interval(n=30, days_apart=1)}
    assert 0 <= score_rhythm(raw) <= 100
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
pytest tests/test_rhythm.py -v
```

Expected: `ModuleNotFoundError: No module named 'factors.rhythm'`

- [ ] **Step 3: Implement rhythm.py**

Create `backend/factors/rhythm.py`:
```python
from datetime import datetime


def _parse_ts(ts_str: str):
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def score_rhythm(raw: dict) -> int:
    posts = raw.get("posts", [])
    timestamps = sorted(
        [t for t in (_parse_ts(p.get("timestamp")) for p in posts) if t],
        reverse=True,
    )

    if len(timestamps) < 2:
        return 50

    intervals = [(timestamps[i] - timestamps[i + 1]).days for i in range(len(timestamps) - 1)]
    intervals = [max(0, d) for d in intervals]

    avg_interval = sum(intervals) / len(intervals)
    std_interval = (sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)) ** 0.5

    if avg_interval <= 3:
        base = 90
    elif avg_interval <= 7:
        base = 70
    elif avg_interval <= 14:
        base = 45
    else:
        base = 20

    consistency_bonus = max(0, 15 - int(std_interval * 2))
    return min(100, max(0, base + consistency_bonus))
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
cd backend
pytest tests/test_rhythm.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/factors/rhythm.py backend/tests/test_rhythm.py
git commit -m "feat: add rhythm factor module (20%)"
```

---

## Task 4: factors/audience.py

**Files:**
- Create: `backend/factors/audience.py`
- Create: `backend/tests/test_audience.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_audience.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factors.audience import score_audience


def make_raw(followers=50000, following=1000, likes=1500, comments=75, n=20):
    return {
        "followers": followers,
        "following": following,
        "posts": [{"likesCount": likes, "commentsCount": comments} for _ in range(n)],
    }


def test_high_ratio_and_high_fulfillment_returns_95():
    # ff_ratio=100, fulfillment=(1575/20)/(50000*0.03)=2.625 >= 1.0
    raw = make_raw(followers=50000, following=500, likes=1500, comments=75)
    assert score_audience(raw) == 95


def test_low_fulfillment_returns_20():
    # followers=500000, following=300, avg_eng=52, expected=15000, fulfillment=0.003
    raw = make_raw(followers=500000, following=300, likes=50, comments=2, n=20)
    assert score_audience(raw) == 20


def test_moderate_returns_mid_score():
    # ff_ratio=5, fulfillment ~0.75 → 75
    raw = make_raw(followers=10000, following=2000, likes=225, comments=10, n=20)
    score = score_audience(raw)
    assert 50 <= score <= 95


def test_no_posts_returns_20():
    raw = {"followers": 50000, "following": 1000, "posts": []}
    assert score_audience(raw) == 20


def test_zero_following_no_crash():
    raw = make_raw(followers=50000, following=0)
    assert 0 <= score_audience(raw) <= 100
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
pytest tests/test_audience.py -v
```

Expected: `ModuleNotFoundError: No module named 'factors.audience'`

- [ ] **Step 3: Implement audience.py**

Create `backend/factors/audience.py`:
```python
def score_audience(raw: dict) -> int:
    followers = raw.get("followers", 1)
    following = raw.get("following", 1)
    posts = raw.get("posts", [])

    ff_ratio = followers / max(following, 1)

    if not posts:
        return 20

    n = len(posts)
    avg_engagement = sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts) / n
    expected = followers * 0.03
    fulfillment = avg_engagement / max(expected, 1)

    if fulfillment >= 1.0 and ff_ratio >= 5:
        return 95
    elif fulfillment >= 0.7 and ff_ratio >= 2:
        return 75
    elif fulfillment >= 0.4:
        return 50
    else:
        return 20
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
cd backend
pytest tests/test_audience.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/factors/audience.py backend/tests/test_audience.py
git commit -m "feat: add audience factor module (20%)"
```

---

## Task 5: factors/niche.py

**Files:**
- Create: `backend/factors/niche.py`
- Create: `backend/tests/test_niche.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_niche.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factors.niche import score_niche


def make_raw(captions=None, hashtag_lists=None, n=10):
    posts = []
    for i in range(n):
        posts.append({
            "caption": captions[i] if captions and i < len(captions) else "",
            "hashtags": hashtag_lists[i] if hashtag_lists and i < len(hashtag_lists) else [],
        })
    return {"posts": posts}


def test_all_beauty_posts_high_score():
    raw = make_raw(
        captions=["my skincare routine"] * 10,
        hashtag_lists=[["skincare", "beauty"]] * 10,
    )
    assert score_niche(raw) >= 70


def test_no_niche_posts_low_score():
    raw = make_raw(
        captions=["eating pizza today"] * 10,
        hashtag_lists=[["food", "travel"]] * 10,
    )
    assert score_niche(raw) <= 20


def test_mixed_posts_mid_score():
    captions = ["skincare routine"] * 5 + ["gym workout"] * 5
    hashtags = [["skincare"]] * 5 + [["fitness"]] * 5
    raw = make_raw(captions=captions, hashtag_lists=hashtags, n=10)
    score = score_niche(raw)
    assert 20 <= score <= 60


def test_recent_posts_weighted():
    # Last 6 posts (first in list = most recent) are beauty, rest not
    captions = ["skincare routine"] * 6 + ["just vibes"] * 14
    hashtags = [["skincare"]] * 6 + [["random"]] * 14
    raw = make_raw(captions=captions, hashtag_lists=hashtags, n=20)
    score = score_niche(raw)
    assert score >= 30  # recency bonus should lift the score


def test_empty_posts_returns_50():
    assert score_niche({"posts": []}) == 50


def test_multilingual_keywords():
    raw = make_raw(
        captions=["makyaj rutini her gün"] * 10,
        hashtag_lists=[["makyaj", "guzellik"]] * 10,
    )
    assert score_niche(raw) >= 60
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
pytest tests/test_niche.py -v
```

Expected: `ModuleNotFoundError: No module named 'factors.niche'`

- [ ] **Step 3: Implement niche.py**

Create `backend/factors/niche.py`:
```python
BEAUTY_KEYWORDS = [
    "skincare", "makeup", "beauty", "skin", "glow", "routine", "serum",
    "moisturizer", "foundation", "lipstick", "hair", "cosmetic", "fashion",
    "style", "makyaj", "guzellik", "cilt", "ruj", "fondoten", "kirpik",
    "макияж", "красота", "уход", "косметика", "beaute", "maquillage",
    "belleza", "maquillaje",
]


def _has_keyword(post: dict) -> bool:
    text = (post.get("caption") or "").lower()
    tags = " ".join(h.lower() for h in (post.get("hashtags") or []))
    combined = text + " " + tags
    return any(k in combined for k in BEAUTY_KEYWORDS)


def _keyword_count(post: dict) -> int:
    text = (post.get("caption") or "").lower()
    tags = " ".join(h.lower() for h in (post.get("hashtags") or []))
    combined = text + " " + tags
    return sum(1 for k in BEAUTY_KEYWORDS if k in combined)


def score_niche(raw: dict) -> int:
    posts = raw.get("posts", [])
    if not posts:
        return 50

    niche_count = sum(1 for p in posts if _has_keyword(p))
    coverage = niche_count / len(posts)

    total_keywords = sum(_keyword_count(p) for p in posts)
    depth_score = min(1.0, (total_keywords / len(posts)) / 5)

    recent_posts = posts[:6]
    recent_niche = sum(1 for p in recent_posts if _has_keyword(p)) / len(recent_posts)

    return int((coverage * 0.4 + depth_score * 0.3 + recent_niche * 0.3) * 100)
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
cd backend
pytest tests/test_niche.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/factors/niche.py backend/tests/test_niche.py
git commit -m "feat: add niche depth factor module (15%)"
```

---

## Task 6: factors/authenticity.py

**Files:**
- Create: `backend/factors/authenticity.py`
- Create: `backend/tests/test_authenticity.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_authenticity.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factors.authenticity import score_authenticity


def make_raw(followers=50000, following=500, posts=None):
    if posts is None:
        posts = [{"likesCount": 500, "commentsCount": 25,
                  "caption": "great product", "hashtags": ["skincare"]} for _ in range(20)]
    return {"followers": followers, "following": following, "posts": posts}


def test_clean_account_returns_100():
    raw = make_raw()
    assert score_authenticity(raw) == 100


def test_engagement_spike_deducts_25():
    posts = [{"likesCount": 100, "commentsCount": 5, "caption": "", "hashtags": []}] * 19
    posts.append({"likesCount": 2000, "commentsCount": 5, "caption": "", "hashtags": []})
    raw = make_raw(posts=posts)
    assert score_authenticity(raw) == 75


def test_following_greater_than_followers_deducts_15():
    raw = make_raw(followers=1000, following=5000)
    assert score_authenticity(raw) == 85


def test_heavy_sponsored_deducts_20():
    sponsored_post = {
        "likesCount": 300,
        "commentsCount": 10,
        "caption": "use my discount code #ad #sponsored",
        "hashtags": ["ad", "sponsored"],
    }
    clean_post = {"likesCount": 300, "commentsCount": 10, "caption": "my routine", "hashtags": []}
    # >50% sponsored
    posts = [sponsored_post] * 11 + [clean_post] * 9
    raw = make_raw(posts=posts)
    assert score_authenticity(raw) == 80


def test_moderate_sponsored_deducts_10():
    sponsored_post = {
        "likesCount": 300,
        "commentsCount": 10,
        "caption": "use my discount code #ad",
        "hashtags": ["ad"],
    }
    clean_post = {"likesCount": 300, "commentsCount": 10, "caption": "my routine", "hashtags": []}
    # ~35% sponsored
    posts = [sponsored_post] * 7 + [clean_post] * 13
    raw = make_raw(posts=posts)
    assert score_authenticity(raw) == 90


def test_multiple_red_flags_cumulative():
    posts = [{"likesCount": 100, "commentsCount": 5, "caption": "", "hashtags": []}] * 19
    posts.append({"likesCount": 2000, "commentsCount": 5, "caption": "", "hashtags": []})
    raw = make_raw(followers=1000, following=5000, posts=posts)
    # spike (-25) + following > followers (-15) = 60
    assert score_authenticity(raw) == 60


def test_score_never_negative():
    sponsored = {"likesCount": 50, "commentsCount": 2, "caption": "#ad #sponsored gifted",
                 "hashtags": ["ad", "sponsored"]}
    spiky = [{"likesCount": 50, "commentsCount": 2, "caption": "", "hashtags": []}] * 19
    spiky.append({"likesCount": 5000, "commentsCount": 2, "caption": "", "hashtags": []})
    posts = [sponsored] * 11 + spiky[:9]
    raw = make_raw(followers=500, following=10000, posts=posts)
    assert score_authenticity(raw) >= 0
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
pytest tests/test_authenticity.py -v
```

Expected: `ModuleNotFoundError: No module named 'factors.authenticity'`

- [ ] **Step 3: Implement authenticity.py**

Create `backend/factors/authenticity.py`:
```python
SPONSORED_SIGNALS = [
    "#ad", "#sponsored", "#paid", "#partnership", "#collab",
    "#reklam", "#işbirliği", "#tanıtım",
    "gifted", "in partnership with", "use my code",
    "discount code", "link in bio",
]


def _is_sponsored(post: dict) -> bool:
    text = (post.get("caption") or "").lower()
    tags = " ".join(h.lower() for h in (post.get("hashtags") or []))
    combined = text + " " + tags
    return any(s in combined for s in SPONSORED_SIGNALS)


def score_authenticity(raw: dict) -> int:
    posts = raw.get("posts", [])
    followers = raw.get("followers", 1)
    following = raw.get("following", 0)
    score = 100

    if posts:
        engagements = [p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts]
        mean_e = sum(engagements) / len(engagements)
        if any(e > mean_e * 4 for e in engagements):
            score -= 25

    if posts:
        sponsored_ratio = sum(1 for p in posts if _is_sponsored(p)) / len(posts)
        if sponsored_ratio > 0.5:
            score -= 20
        elif sponsored_ratio > 0.3:
            score -= 10

    if following > followers:
        score -= 15

    return max(0, min(100, score))
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
cd backend
pytest tests/test_authenticity.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/factors/authenticity.py backend/tests/test_authenticity.py
git commit -m "feat: add authenticity red-flag factor module (10%)"
```

---

## Task 7: factors/momentum.py

**Files:**
- Create: `backend/factors/momentum.py`
- Create: `backend/tests/test_momentum.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_momentum.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factors.momentum import score_momentum


def make_posts(recent_likes, old_likes, n_recent=12, n_old=12):
    posts = []
    for _ in range(n_recent):
        posts.append({"likesCount": recent_likes, "commentsCount": 10})
    for _ in range(n_old):
        posts.append({"likesCount": old_likes, "commentsCount": 10})
    return posts


def test_growing_engagement_returns_100():
    # recent avg = 1300, older avg = 1000 → ratio = 1.3 → 100
    raw = {"posts": make_posts(recent_likes=1290, old_likes=1000)}
    assert score_momentum(raw) == 100


def test_slight_growth_returns_75():
    # recent avg = 1100, older avg = 1000 → ratio = 1.1 → 75
    raw = {"posts": make_posts(recent_likes=1090, old_likes=1000)}
    assert score_momentum(raw) == 75


def test_stable_returns_50():
    # ratio ≈ 1.0 → 50
    raw = {"posts": make_posts(recent_likes=1000, old_likes=1000)}
    assert score_momentum(raw) == 50


def test_declining_returns_25():
    # recent = 700, older = 1000 → ratio = 0.7 → 25
    raw = {"posts": make_posts(recent_likes=690, old_likes=1000)}
    assert score_momentum(raw) == 25


def test_severe_decline_returns_0():
    # recent = 100, older = 1000 → ratio = 0.1 → 0
    raw = {"posts": make_posts(recent_likes=100, old_likes=1000)}
    assert score_momentum(raw) == 0


def test_fewer_than_13_posts_returns_50():
    raw = {"posts": make_posts(recent_likes=500, old_likes=200, n_recent=6, n_old=6)}
    assert score_momentum(raw) == 50


def test_empty_posts_returns_50():
    assert score_momentum({"posts": []}) == 50
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
pytest tests/test_momentum.py -v
```

Expected: `ModuleNotFoundError: No module named 'factors.momentum'`

- [ ] **Step 3: Implement momentum.py**

Create `backend/factors/momentum.py`:
```python
def score_momentum(raw: dict) -> int:
    posts = raw.get("posts", [])

    if len(posts) < 13:
        return 50

    def avg_eng(subset):
        if not subset:
            return 1
        return sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in subset) / len(subset)

    recent = avg_eng(posts[:12])
    older = avg_eng(posts[12:24])
    ratio = recent / max(older, 1)

    if ratio >= 1.3:
        return 100
    elif ratio >= 1.1:
        return 75
    elif ratio >= 0.9:
        return 50
    elif ratio >= 0.7:
        return 25
    else:
        return 0
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
cd backend
pytest tests/test_momentum.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/factors/momentum.py backend/tests/test_momentum.py
git commit -m "feat: add growth momentum factor module (5%)"
```

---

## Task 8: factors/fraud.py

**Files:**
- Create: `backend/factors/fraud.py`
- Create: `backend/tests/test_fraud.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_fraud.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factors.fraud import compute_fraud_multiplier

DUMMY_SCORES = {
    "engagement": 70, "rhythm": 70, "audience": 70,
    "niche": 70, "authenticity": 70, "momentum": 70,
}
CLEAN_SENTIMENT = {"spam_ratio": 0.1, "purchase_intent_ratio": 0.3, "fraud_risk": 0.1, "source": "fallback"}


def make_raw(followers=50000, following=500, n=24, likes=1500, comments=75, hashtags_per_post=5):
    posts = [{"likesCount": likes, "commentsCount": comments,
              "hashtags": ["skincare"] * hashtags_per_post} for _ in range(n)]
    return {"followers": followers, "following": following, "posts": posts}


def test_clean_account_returns_1():
    raw = make_raw()
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult == 1.0


def test_ghost_followers_returns_040():
    # followers=500000, avg_eng=52, expected_min=2500, 52 < 2500*0.3=750 → GHOST
    raw = make_raw(followers=500000, following=300, likes=50, comments=2)
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult == 0.40


def test_follow_unfollow_tactic_reduces_multiplier():
    # following > followers * 0.8
    raw = make_raw(followers=10000, following=9000)
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult < 1.0


def test_hashtag_spam_reduces_multiplier():
    raw = make_raw(hashtags_per_post=30)
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult < 1.0


def test_suspicious_comments_reduces_multiplier():
    raw = make_raw()
    bad_sentiment = {"spam_ratio": 0.8, "purchase_intent_ratio": 0.0, "fraud_risk": 0.8, "source": "claude"}
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, bad_sentiment)
    assert mult < 1.0


def test_multiplier_values_are_discrete():
    # multiplier must be one of the 4 defined values
    raw = make_raw()
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult in (1.0, 0.85, 0.65, 0.40)


def test_none_sentiment_no_crash():
    raw = make_raw()
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, None)
    assert mult == 1.0
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
pytest tests/test_fraud.py -v
```

Expected: `ModuleNotFoundError: No module named 'factors.fraud'`

- [ ] **Step 3: Implement fraud.py**

Create `backend/factors/fraud.py`:
```python
def compute_fraud_multiplier(raw: dict, scores: dict, sentiment_result) -> float:
    followers = raw.get("followers", 1)
    following = raw.get("following", 0)
    posts = raw.get("posts", [])
    fraud_score = 100

    # Signal 1: Ghost followers
    if posts:
        n = len(posts)
        avg_eng = sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts) / n
        expected_min = followers * 0.005
        if avg_eng < expected_min * 0.3:
            fraud_score -= 30

    # Signal 2: Suspicious growth (old posts much higher engagement)
    if len(posts) >= 24:
        early = sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts[18:24]) / 6
        recent = sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts[:6]) / 6
        if early / max(recent, 1) > 3:
            fraud_score -= 25

    # Signal 3: Follow/unfollow tactic
    if following > followers * 0.8:
        fraud_score -= 20

    # Signal 4: Hashtag spam
    if posts:
        avg_hashtags = sum(len(p.get("hashtags") or []) for p in posts) / len(posts)
        if avg_hashtags > 25:
            fraud_score -= 10

    # Signal 5: Suspicious comments from sentiment
    if sentiment_result and sentiment_result.get("fraud_risk", 0) > 0.6:
        fraud_score -= 15

    fraud_score = max(0, fraud_score)

    if fraud_score >= 80:
        return 1.0
    elif fraud_score >= 60:
        return 0.85
    elif fraud_score >= 40:
        return 0.65
    else:
        return 0.40
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
cd backend
pytest tests/test_fraud.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/factors/fraud.py backend/tests/test_fraud.py
git commit -m "feat: add fraud multiplier module"
```

---

## Task 9: factors/sentiment.py

**Files:**
- Create: `backend/factors/sentiment.py`
- Create: `backend/tests/test_sentiment.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_sentiment.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from factors.sentiment import score_sentiment, _keyword_fallback


def make_raw_with_comments(comments_per_post=3, n_posts=10, comment_texts=None):
    posts = []
    for i in range(n_posts):
        c_list = []
        for j in range(comments_per_post):
            text = comment_texts[i * comments_per_post + j] if comment_texts else "nice post"
            c_list.append({"text": text, "ownerUsername": f"user{j}"})
        posts.append({"latestComments": c_list})
    return {"posts": posts}


def test_no_api_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raw = make_raw_with_comments()
    result = score_sentiment(raw)
    assert result["source"] in ("fallback", "no_comments")
    assert "spam_ratio" in result
    assert "fraud_risk" in result


def test_no_comments_returns_defaults(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raw = {"posts": [{"latestComments": []} for _ in range(5)]}
    result = score_sentiment(raw)
    assert result["source"] == "no_comments"
    assert result["spam_ratio"] == 0.1


def test_keyword_fallback_detects_spam():
    spam_comments = ["follow me back", "check my page", "nice 👍"] * 10
    result = _keyword_fallback(spam_comments)
    assert result["spam_ratio"] > 0
    assert result["source"] == "fallback"


def test_keyword_fallback_detects_purchase_intent():
    intent_comments = ["where can I buy this?", "what's the price?", "link please"] * 10
    result = _keyword_fallback(intent_comments)
    assert result["purchase_intent_ratio"] > 0
    assert result["source"] == "fallback"


def test_result_has_required_keys(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raw = make_raw_with_comments()
    result = score_sentiment(raw)
    assert all(k in result for k in ("spam_ratio", "purchase_intent_ratio", "fraud_risk", "source"))


def test_all_ratios_between_0_and_1(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raw = make_raw_with_comments()
    result = score_sentiment(raw)
    assert 0 <= result["spam_ratio"] <= 1
    assert 0 <= result["purchase_intent_ratio"] <= 1
    assert 0 <= result["fraud_risk"] <= 1
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
pytest tests/test_sentiment.py -v
```

Expected: `ModuleNotFoundError: No module named 'factors.sentiment'`

- [ ] **Step 3: Implement sentiment.py**

Create `backend/factors/sentiment.py`:
```python
import os
import json
from datetime import date

_client = None
_daily_count = {"date": None, "count": 0}
DAILY_CAP = 50


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _within_cap() -> bool:
    today = date.today().isoformat()
    if _daily_count["date"] != today:
        _daily_count["date"] = today
        _daily_count["count"] = 0
    return _daily_count["count"] < DAILY_CAP


def _extract_comments(raw: dict) -> list:
    comments = []
    for post in raw.get("posts", [])[:10]:
        for c in (post.get("latestComments") or [])[:3]:
            text = (c.get("text") or "").strip()
            if text:
                comments.append(text)
    return comments[:30]


def score_sentiment(raw: dict) -> dict:
    comments = _extract_comments(raw)

    if not comments:
        return {"spam_ratio": 0.1, "purchase_intent_ratio": 0.1, "fraud_risk": 0.1, "source": "no_comments"}

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not _within_cap():
        return _keyword_fallback(comments)

    try:
        client = _get_client()
        prompt = (
            f"Analyze these {len(comments)} Instagram comments and return ONLY valid JSON.\n\n"
            f"Comments:\n" + "\n".join(f"- {c}" for c in comments) +
            "\n\nReturn JSON with:\n"
            "- spam_ratio: float 0-1 (generic/emoji-only/bot-like)\n"
            "- purchase_intent_ratio: float 0-1 (buying interest, price questions)\n"
            "- fraud_risk: float 0-1 (bot patterns, suspiciously uniform)\n"
            "- summary: string (one sentence insight)"
        )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        _daily_count["count"] += 1

        text = response.content[0].text.strip()
        if "```" in text:
            parts = text.split("```")
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]

        result = json.loads(text.strip())
        result["source"] = "claude"
        return result

    except Exception as e:
        print(f"Sentiment error: {e}")
        return _keyword_fallback(comments)


def _keyword_fallback(comments: list) -> dict:
    spam_signals = ["nice", "great", "amazing", "follow me", "check my", "👍", "❤️", "🔥"]
    intent_signals = ["price", "where", "buy", "shop", "link", "how much", "available", "order"]

    total = len(comments)
    spam = sum(1 for c in comments if any(s in c.lower() for s in spam_signals)) / total
    intent = sum(1 for c in comments if any(s in c.lower() for s in intent_signals)) / total

    return {
        "spam_ratio": round(spam, 3),
        "purchase_intent_ratio": round(intent, 3),
        "fraud_risk": round(spam * 0.5, 3),
        "source": "fallback",
    }
```

- [ ] **Step 4: Run tests — confirm pass**

```bash
cd backend
pytest tests/test_sentiment.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/factors/sentiment.py backend/tests/test_sentiment.py
git commit -m "feat: add sentiment module with Claude Sonnet 4.6 and daily cap"
```

---

## Task 10: Rewrite scraper.py

**Files:**
- Modify: `backend/scraper.py`

- [ ] **Step 1: Replace the scoring calculations in `_fetch_apify`**

In `backend/scraper.py`, replace the entire return value block of `_fetch_apify` (lines 38–120 — everything from `# 1. ENGAGEMENT RATE` through `return {...}`) with the following. Keep the top of the function (token check, client init, actor call, items check, and the lines that extract `p`, `followers`, `following`, `posts`, `is_business`) unchanged.

The new return block:
```python
        bio_url = p.get("externalUrl") or p.get("bioLinks", [{}])[0].get("url", "") if p.get("bioLinks") else p.get("externalUrl") or ""

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
```

- [ ] **Step 2: Update MOCK_PROFILES to new structure**

Replace the `MOCK_PROFILES` dict with raw-data equivalents. Each mock profile must now use `followers`, `following`, `posts`, `is_business`, `verified`, `bio_url` instead of the old scoring fields:

```python
def _make_mock_posts(n=20, likes=500, comments=25, days_apart=3, captions=None, hashtags=None):
    from datetime import datetime, timedelta
    posts = []
    base = datetime(2025, 1, 1, 12, 0, 0)
    for i in range(n):
        ts = base - timedelta(days=i * days_apart)
        posts.append({
            "likesCount": likes,
            "commentsCount": comments,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "caption": captions[i] if captions and i < len(captions) else "skincare routine #skincare #beauty",
            "hashtags": hashtags[i] if hashtags and i < len(hashtags) else ["skincare", "beauty"],
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
```

- [ ] **Step 3: Update `_generate_random_profile` to new structure**

Replace `_generate_random_profile`:
```python
def _generate_random_profile(handle):
    from datetime import datetime, timedelta
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
```

- [ ] **Step 4: Verify scraper still imports cleanly**

```bash
cd backend
python -c "from scraper import fetch_profile; p = fetch_profile('sophiareeves'); print(p['followers'], len(p['posts']))"
```

Expected: `15100 24`

- [ ] **Step 5: Commit**

```bash
git add backend/scraper.py
git commit -m "refactor: scraper returns raw profile data, removes scoring calculations"
```

---

## Task 11: Rewrite scorer.py

**Files:**
- Modify: `backend/scorer.py`
- Create: `backend/tests/test_scorer.py`

- [ ] **Step 1: Write integration tests first**

Create `backend/tests/test_scorer.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from scorer import compute_score


def make_profile(followers=50000, following=500, likes=1500, comments=75,
                 n=24, days_apart=3, captions=None, hashtags=None):
    base = datetime(2025, 1, 1, 12, 0, 0)
    posts = []
    for i in range(n):
        ts = base - timedelta(days=i * days_apart)
        posts.append({
            "likesCount": likes,
            "commentsCount": comments,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "caption": captions[i] if captions and i < len(captions) else "skincare routine",
            "hashtags": hashtags[i] if hashtags and i < len(hashtags) else ["skincare", "beauty"],
            "latestComments": [{"text": "Where to buy?", "ownerUsername": "fan1"}],
        })
    return {
        "handle": "@testuser",
        "followers": followers,
        "following": following,
        "posts": posts,
        "is_business": False,
        "verified": False,
        "bio_url": "",
        "platform": "instagram",
        "mock": True,
    }


def test_healthy_profile_scores_high(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raw = make_profile(followers=50000, following=500, likes=1500, comments=75)
    result = compute_score(raw)
    assert result.score >= 60


def test_ghost_profile_scores_low(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raw = make_profile(followers=500000, following=300, likes=50, comments=2)
    result = compute_score(raw)
    assert result.score < 40


def test_result_has_correct_shape(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raw = make_profile()
    result = compute_score(raw)
    assert hasattr(result, "handle")
    assert hasattr(result, "score")
    assert hasattr(result, "label")
    assert hasattr(result, "breakdown")
    assert hasattr(result, "insight")
    assert 0 <= result.score <= 100


def test_label_matches_score(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raw = make_profile()
    result = compute_score(raw)
    if result.score >= 85:
        assert result.label == "elite"
    elif result.score >= 70:
        assert result.label == "high"
    elif result.score >= 50:
        assert result.label == "mid"
    elif result.score >= 30:
        assert result.label == "risky"
    else:
        assert result.label == "avoid"


def test_breakdown_has_7_factors(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raw = make_profile()
    result = compute_score(raw)
    factor_keys = {f["key"] for f in result.breakdown}
    assert "engagement" in factor_keys
    assert "rhythm" in factor_keys
    assert "audience" in factor_keys
    assert "niche" in factor_keys
    assert "authenticity" in factor_keys
    assert "momentum" in factor_keys


def test_weights_sum_to_1():
    from scorer import WEIGHTS
    assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend
pytest tests/test_scorer.py -v
```

Expected: failures — old scorer has wrong structure.

- [ ] **Step 3: Rewrite scorer.py**

Replace `backend/scorer.py` entirely:
```python
"""
Vettly ROI Scorer — 7-factor modular system with fraud multiplier.

Formula:
  score = (
      engagement   * 0.30 +
      rhythm       * 0.20 +
      audience     * 0.20 +
      niche        * 0.15 +
      authenticity * 0.10 +
      momentum     * 0.05
  ) * 100 * fraud_multiplier

Labels: elite(85+) | high(70+) | mid(50+) | risky(30+) | avoid(<30)
"""

from dataclasses import dataclass
from factors.engagement import score_engagement
from factors.rhythm import score_rhythm
from factors.audience import score_audience
from factors.niche import score_niche
from factors.authenticity import score_authenticity
from factors.momentum import score_momentum
from factors.fraud import compute_fraud_multiplier
from factors.sentiment import score_sentiment

WEIGHTS = {
    "engagement":   0.30,
    "rhythm":       0.20,
    "audience":     0.20,
    "niche":        0.15,
    "authenticity": 0.10,
    "momentum":     0.05,
}

FACTOR_LABELS = {
    "engagement":   "Engagement Quality",
    "rhythm":       "Content Rhythm",
    "audience":     "Audience Reliability",
    "niche":        "Niche Depth",
    "authenticity": "Authenticity",
    "momentum":     "Growth Momentum",
}


@dataclass
class ScoreResult:
    handle: str
    score: int
    label: str
    breakdown: list
    insight: str


def compute_score(raw: dict) -> ScoreResult:
    handle = raw.get("handle", "unknown")

    scores = {
        "engagement":   score_engagement(raw),
        "rhythm":       score_rhythm(raw),
        "audience":     score_audience(raw),
        "niche":        score_niche(raw),
        "authenticity": score_authenticity(raw),
        "momentum":     score_momentum(raw),
    }

    sentiment_result = score_sentiment(raw)
    fraud_multiplier = compute_fraud_multiplier(raw, scores, sentiment_result)

    weighted_sum = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    final_score = max(0, min(100, round(weighted_sum * 100 * fraud_multiplier)))

    label = _label(final_score)

    breakdown = [
        {
            "key": k,
            "label": FACTOR_LABELS[k],
            "description": f"{FACTOR_LABELS[k]} score: {scores[k]}/100.",
            "value": scores[k],
            "weight": WEIGHTS[k],
            "contribution": round(scores[k] * WEIGHTS[k], 2),
        }
        for k in WEIGHTS
    ]

    insight = _build_insight(handle, final_score, label, scores, fraud_multiplier, sentiment_result)

    return ScoreResult(handle=handle, score=final_score, label=label,
                       breakdown=breakdown, insight=insight)


def _label(score: int) -> str:
    if score >= 85:  return "elite"
    if score >= 70:  return "high"
    if score >= 50:  return "mid"
    if score >= 30:  return "risky"
    return "avoid"


def _build_insight(handle, score, label, scores, fraud_multiplier, sentiment_result) -> str:
    lines = []

    top = max(scores, key=scores.get)
    lines.append(f"{FACTOR_LABELS[top]} is the strongest signal at {scores[top]}/100.")

    if scores["engagement"] >= 75:
        lines.append("Engagement rate is well above average — strong buying signal.")
    elif scores["engagement"] < 40:
        lines.append("Engagement rate is low — weak conversion potential.")

    if fraud_multiplier < 1.0:
        penalty_pct = int((1 - fraud_multiplier) * 100)
        lines.append(f"Fraud signals detected — score reduced by {penalty_pct}%.")

    if sentiment_result and sentiment_result.get("purchase_intent_ratio", 0) > 0.3:
        lines.append("Comment analysis shows high purchase intent — strong ROI signal.")

    label_text = {
        "elite": f"Elite conversion candidate. ROI score {score}/100.",
        "high":  f"Strong ROI potential. Safe choice for paid partnerships. Score {score}/100.",
        "mid":   f"Better suited for brand awareness than direct conversion. Score {score}/100.",
        "risky": f"Risk signals present. Proceed with caution. Score {score}/100.",
        "avoid": f"Multiple red flags. Not recommended for paid partnerships. Score {score}/100.",
    }
    lines.append(label_text[label])

    return " ".join(lines)
```

- [ ] **Step 4: Run all tests**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests pass (35+ tests).

- [ ] **Step 5: Commit**

```bash
git add backend/scorer.py backend/tests/test_scorer.py
git commit -m "feat: rewrite scorer as 7-factor orchestrator with fraud multiplier"
```

---

## Task 12: Update main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add `category` field to ScoreRequest**

In `backend/main.py`, find the `ScoreRequest` class and add the `category` field:

```python
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
```

- [ ] **Step 2: Update breakdown construction in `/score` endpoint**

`result.breakdown` is now a list of dicts (not dataclass instances). Find lines 134–138 in `backend/main.py`:

```python
        breakdown=[
            FactorOut(key=f.key, label=f.label, description=f.description,
                      value=f.value, weight=f.weight, contribution=f.contribution)
            for f in result.breakdown
        ],
```

Replace with:
```python
        breakdown=[
            FactorOut(key=f["key"], label=f["label"], description=f["description"],
                      value=f["value"], weight=f["weight"], contribution=f["contribution"])
            for f in result.breakdown
        ],
```

- [ ] **Step 3: Pass category to fetch_profile**

In the `/score` endpoint, update the scraper call to pass category:

Find:
```python
    raw = fetch_profile(req.handle)
```

Replace with:
```python
    raw = fetch_profile(req.handle, category=req.category)
```

- [ ] **Step 4: Update fetch_profile signature in scraper.py**

In `backend/scraper.py`, update `fetch_profile` to accept `category`:

```python
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
```

- [ ] **Step 5: Verify import chain works**

```bash
cd backend
python -c "
from scraper import fetch_profile
from scorer import compute_score
raw = fetch_profile('sophiareeves')
result = compute_score(raw)
print(f'Score: {result.score}, Label: {result.label}')
"
```

Expected: prints a score between 0-100 and a valid label (elite/high/mid/risky/avoid). No errors.

- [ ] **Step 6: Run full test suite**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/scraper.py
git commit -m "feat: add category field to ScoreRequest and fetch_profile"
```

---

## Task 13: Fix dashboard.html

**Files:**
- Modify: `dashboard.html`

- [ ] **Step 1: Fix duplicate analyzeHandle**

In `dashboard.html` line 335, find this exact string:
```
function analyzeHandle(){var i=document.getElementById("handle-input");var r=i.value.trim();if(!r)return;doAnalyze(r.startsWith("@")?r:"@"+r);}function analyzeHandle(){var i=document.getElementById("handle-input");var r=i.value.trim();if(!r)return;doAnalyze(r.startsWith("@")?r:"@"+r);}async function doAnalyze(handle){
```

Replace with (one definition only):
```
function analyzeHandle(){var i=document.getElementById("handle-input");var r=i.value.trim();if(!r)return;doAnalyze(r.startsWith("@")?r:"@"+r);}
async function doAnalyze(handle){
```

- [ ] **Step 2: Update the LBL object (3-label → 5-label)**

Find the existing LBL object in `dashboard.html`:
```js
const LBL={
  high:{bg:"var(--green-lo)",col:"var(--green)",brd:"var(--green-mid)",txt:"High ROI"},
  mid:{bg:"var(--amber-lo)",col:"var(--amber)",brd:"var(--amber-mid)",txt:"Aesthetic"},
  low:{bg:"var(--red-lo)",col:"var(--red)",brd:"var(--red-mid)",txt:"Risk"}
};
```

Replace with:
```js
const LBL={
  elite:{bg:"var(--green-lo)",col:"var(--green)",brd:"var(--green-mid)",txt:"Elite"},
  high: {bg:"var(--green-lo)",col:"var(--green)",brd:"var(--green-mid)",txt:"High ROI"},
  mid:  {bg:"var(--amber-lo)",col:"var(--amber)",brd:"var(--amber-mid)",txt:"Mid Tier"},
  risky:{bg:"var(--red-lo)",  col:"var(--red)",  brd:"var(--red-mid)",  txt:"Risky"},
  avoid:{bg:"var(--red-lo)",  col:"var(--red)",  brd:"var(--red-mid)",  txt:"Avoid"},
};
```

- [ ] **Step 3: Verify in browser**

Open `dashboard.html` locally (or on Vercel preview). Type any handle in the search box, press Enter or click Analyze. Confirm:
- No JavaScript errors in browser console
- The button shows "…" while loading and "Analyze →" after
- Score card appears with one of the 5 labels

- [ ] **Step 4: Commit**

```bash
git add dashboard.html
git commit -m "fix: remove duplicate analyzeHandle, update to 5-label system"
```

---

## Task 14: Add ANTHROPIC_API_KEY to Railway and push

**Files:** None (environment variable + git push)

- [ ] **Step 1: Add env var to Railway**

In Railway dashboard → vettly backend service → Variables:
```
ANTHROPIC_API_KEY=<your key>
```

- [ ] **Step 2: Run final test suite locally**

```bash
cd backend
pytest tests/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 3: Push to GitHub (triggers Railway redeploy)**

```bash
git push origin main
```

- [ ] **Step 4: Smoke test production**

```bash
curl -s https://vettly-production-63d5.up.railway.app/health
```

Expected: `{"status":"ok"}`

```bash
curl -s -X POST https://vettly-production-63d5.up.railway.app/score \
  -H "Content-Type: application/json" \
  -d '{"handle":"sophiareeves"}' | python3 -m json.tool | grep -E '"score"|"label"'
```

Expected: a score integer and one of `elite|high|mid|risky|avoid`.
