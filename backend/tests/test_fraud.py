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


def make_raw_with_spike(followers=500000, following=300, recent_likes=50, recent_comments=2,
                        old_likes=500, old_comments=50, hashtags_per_post=5):
    # 24 posts: first 6 recent, posts[18:24] are old (early)
    posts = []
    for i in range(24):
        if i < 6:
            posts.append({"likesCount": recent_likes, "commentsCount": recent_comments,
                          "hashtags": ["skincare"] * hashtags_per_post})
        else:
            posts.append({"likesCount": old_likes, "commentsCount": old_comments,
                          "hashtags": ["skincare"] * hashtags_per_post})
    return {"followers": followers, "following": following, "posts": posts}


def test_clean_account_returns_1():
    raw = make_raw()
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult == 1.0


def test_ghost_followers_returns_040():
    # Signal 1 (ghost): avg_eng=52, expected_min=500000*0.005=2500, 0.3*2500=750, 52<750 -> -30
    # Signal 2 (spike): early(posts[18:24])=550, recent(posts[:6])=52, 550/52>3 -> -25
    # Signal 3 (follow/unfollow): following=450000 > 500000*0.8=400000 -> -20
    # Total: -75 -> fraud_score=25 -> 0.40
    raw = make_raw_with_spike(followers=500000, following=450000,
                              recent_likes=50, recent_comments=2,
                              old_likes=500, old_comments=50)
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult == 0.40


def test_ghost_followers_reduces_multiplier():
    # Signal 1 only: avg_eng=52, expected_min=750 -> -30 -> fraud_score=70 -> 0.85
    raw = make_raw(followers=500000, following=300, likes=50, comments=2)
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult < 1.0


def test_follow_unfollow_tactic_reduces_multiplier():
    # following > followers*0.8 AND ghost followers: -20 + -30 = -50 -> score=50 -> 0.65
    raw = make_raw(followers=50000, following=45000, likes=10, comments=1)
    # avg_eng=11, expected_min=50000*0.005=250, 0.3*250=75, 11<75 -> ghost -30
    # following=45000 > 50000*0.8=40000 -> follow/unfollow -20
    # total -50 -> score=50 -> 0.65
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult < 1.0


def test_hashtag_spam_reduces_multiplier():
    # hashtag spam (-10) + ghost followers (-30) = -40 -> score=60 -> 0.85
    raw = make_raw(followers=500000, following=300, likes=50, comments=2, hashtags_per_post=30)
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult < 1.0


def test_suspicious_comments_reduces_multiplier():
    # fraud_risk=0.8>0.6 -> -15, plus ghost followers -30 -> score=55 -> 0.65
    raw = make_raw(followers=500000, following=300, likes=50, comments=2)
    bad_sentiment = {"spam_ratio": 0.8, "purchase_intent_ratio": 0.0, "fraud_risk": 0.8, "source": "claude"}
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, bad_sentiment)
    assert mult < 1.0


def test_multiplier_values_are_discrete():
    raw = make_raw()
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, CLEAN_SENTIMENT)
    assert mult in (1.0, 0.85, 0.65, 0.40)


def test_none_sentiment_no_crash():
    raw = make_raw()
    mult = compute_fraud_multiplier(raw, DUMMY_SCORES, None)
    assert mult == 1.0
