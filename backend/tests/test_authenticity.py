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
        "likesCount": 300, "commentsCount": 10,
        "caption": "use my discount code #ad #sponsored",
        "hashtags": ["ad", "sponsored"],
    }
    clean_post = {"likesCount": 300, "commentsCount": 10, "caption": "my routine", "hashtags": []}
    posts = [sponsored_post] * 11 + [clean_post] * 9
    raw = make_raw(posts=posts)
    assert score_authenticity(raw) == 80


def test_moderate_sponsored_deducts_10():
    sponsored_post = {
        "likesCount": 300, "commentsCount": 10,
        "caption": "use my discount code #ad",
        "hashtags": ["ad"],
    }
    clean_post = {"likesCount": 300, "commentsCount": 10, "caption": "my routine", "hashtags": []}
    posts = [sponsored_post] * 7 + [clean_post] * 13
    raw = make_raw(posts=posts)
    assert score_authenticity(raw) == 90


def test_multiple_red_flags_cumulative():
    posts = [{"likesCount": 100, "commentsCount": 5, "caption": "", "hashtags": []}] * 19
    posts.append({"likesCount": 2000, "commentsCount": 5, "caption": "", "hashtags": []})
    raw = make_raw(followers=1000, following=5000, posts=posts)
    assert score_authenticity(raw) == 60


def test_score_never_negative():
    sponsored = {"likesCount": 50, "commentsCount": 2, "caption": "#ad #sponsored gifted",
                 "hashtags": ["ad", "sponsored"]}
    spiky = [{"likesCount": 50, "commentsCount": 2, "caption": "", "hashtags": []}] * 19
    spiky.append({"likesCount": 5000, "commentsCount": 2, "caption": "", "hashtags": []})
    posts = [sponsored] * 11 + spiky[:9]
    raw = make_raw(followers=500, following=10000, posts=posts)
    assert score_authenticity(raw) >= 0
