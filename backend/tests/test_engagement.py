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
    # 750/10000 * 100 = 7.5% → raw_score=90 + comment_bonus=15 → capped at 100
    raw = make_raw(followers=10000, likes=700, comments=50, n=20)
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
