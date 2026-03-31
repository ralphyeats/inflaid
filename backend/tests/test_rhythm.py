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
    # avg_interval=7 -> base=70, std=0 -> bonus=15, score=85
    raw = {"posts": make_posts_with_interval(n=20, days_apart=7)}
    score = score_rhythm(raw)
    assert 60 <= score <= 90


def test_monthly_posts_low_score():
    # avg_interval=30 -> base=20, std=0 -> bonus=15, score=35
    raw = {"posts": make_posts_with_interval(n=10, days_apart=30)}
    assert score_rhythm(raw) <= 40


def test_consistent_interval_bonus():
    consistent = {"posts": make_posts_with_interval(n=20, days_apart=3)}
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
