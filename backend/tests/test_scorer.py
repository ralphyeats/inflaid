import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from scorer import compute_score, WEIGHTS


def make_profile(followers=50000, following=500, likes=1500, comments=75,
                 n=24, days_apart=3):
    base = datetime(2025, 1, 1, 12, 0, 0)
    posts = []
    for i in range(n):
        ts = base - timedelta(days=i * days_apart)
        posts.append({
            "likesCount": likes,
            "commentsCount": comments,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "caption": "skincare routine",
            "hashtags": ["skincare", "beauty"],
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
    result = compute_score(make_profile())
    assert result.score >= 50


def test_ghost_profile_scores_low(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    base = datetime(2025, 1, 1, 12, 0, 0)
    posts = []
    for i in range(24):
        ts = base - timedelta(days=i * 25)
        posts.append({
            "likesCount": 50,
            "commentsCount": 2,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "caption": "just chilling",
            "hashtags": ["life", "random"],
            "latestComments": [{"text": "nice", "ownerUsername": "bot1"}],
        })
    ghost = {
        "handle": "@ghostuser",
        "followers": 500000,
        "following": 300,
        "posts": posts,
        "is_business": False,
        "verified": False,
        "bio_url": "",
        "platform": "instagram",
        "mock": True,
    }
    result = compute_score(ghost)
    assert result.score < 40


def test_result_shape(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = compute_score(make_profile())
    assert hasattr(result, "handle")
    assert hasattr(result, "score")
    assert hasattr(result, "label")
    assert hasattr(result, "breakdown")
    assert hasattr(result, "insight")
    assert 0 <= result.score <= 100


def test_label_matches_score(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = compute_score(make_profile())
    if result.score >= 85:   assert result.label == "elite"
    elif result.score >= 70: assert result.label == "high"
    elif result.score >= 50: assert result.label == "mid"
    elif result.score >= 30: assert result.label == "risky"
    else:                    assert result.label == "avoid"


def test_breakdown_has_6_factors(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = compute_score(make_profile())
    keys = {f["key"] for f in result.breakdown}
    assert keys == {"engagement", "rhythm", "audience", "niche", "authenticity", "momentum"}


def test_weights_sum_to_1():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001


def test_fraud_multiplier_reduces_score(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    clean = compute_score(make_profile(followers=50000, following=500))
    ghost = compute_score(make_profile(followers=500000, following=300, likes=50, comments=2))
    assert ghost.score < clean.score
