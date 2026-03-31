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
