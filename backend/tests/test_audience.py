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
    raw = make_raw(followers=50000, following=500, likes=1500, comments=75)
    assert score_audience(raw) == 95


def test_low_fulfillment_returns_20():
    raw = make_raw(followers=500000, following=300, likes=50, comments=2, n=20)
    assert score_audience(raw) == 20


def test_moderate_returns_mid_score():
    raw = make_raw(followers=10000, following=2000, likes=225, comments=10, n=20)
    score = score_audience(raw)
    assert 50 <= score <= 95


def test_no_posts_returns_20():
    raw = {"followers": 50000, "following": 1000, "posts": []}
    assert score_audience(raw) == 20


def test_zero_following_no_crash():
    raw = make_raw(followers=50000, following=0)
    assert 0 <= score_audience(raw) <= 100
