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
    # recent avg = (1300+10) = 1310, old avg = (1000+10) = 1010, ratio ~1.297 < 1.3? use 1320 likes
    # (1320+10)/(1000+10) = 1330/1010 ~1.317 >= 1.3 -> 100
    raw = {"posts": make_posts(recent_likes=1320, old_likes=1000)}
    assert score_momentum(raw) == 100


def test_slight_growth_returns_75():
    # (1100+10)/(1000+10) = 1110/1010 ~1.099 < 1.1; use 1105: 1115/1010 ~1.104 >= 1.1 -> 75
    raw = {"posts": make_posts(recent_likes=1105, old_likes=1000)}
    assert score_momentum(raw) == 75


def test_stable_returns_50():
    raw = {"posts": make_posts(recent_likes=1000, old_likes=1000)}
    assert score_momentum(raw) == 50


def test_declining_returns_25():
    # (750+10)/(1000+10) = 760/1010 ~0.752 >= 0.7 -> 25
    raw = {"posts": make_posts(recent_likes=750, old_likes=1000)}
    assert score_momentum(raw) == 25


def test_severe_decline_returns_0():
    raw = {"posts": make_posts(recent_likes=100, old_likes=1000)}
    assert score_momentum(raw) == 0


def test_fewer_than_13_posts_returns_50():
    raw = {"posts": make_posts(recent_likes=500, old_likes=200, n_recent=6, n_old=6)}
    assert score_momentum(raw) == 50


def test_empty_posts_returns_50():
    assert score_momentum({"posts": []}) == 50
