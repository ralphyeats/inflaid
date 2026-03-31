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
    captions = ["skincare routine"] * 6 + ["just vibes"] * 14
    hashtags = [["skincare"]] * 6 + [["random"]] * 14
    raw = make_raw(captions=captions, hashtag_lists=hashtags, n=20)
    score = score_niche(raw)
    assert score >= 30


def test_empty_posts_returns_50():
    assert score_niche({"posts": []}) == 50


def test_multilingual_keywords():
    raw = make_raw(
        captions=["makyaj rutini her gün"] * 10,
        hashtag_lists=[["makyaj", "guzellik"]] * 10,
    )
    assert score_niche(raw) >= 60
