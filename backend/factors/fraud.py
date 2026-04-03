def compute_fraud_multiplier(raw: dict, scores: dict, sentiment_result) -> float:
    followers = raw.get("followers", 1)
    following = raw.get("following", 0)
    posts = raw.get("posts", [])
    fraud_score = 100

    # Signal 1: Ghost followers
    # Skip if likes are hidden (likesCount consistently 0) — Instagram hides likes
    # for large accounts; use comments-only check with lenient threshold instead
    if posts:
        n = len(posts)
        avg_likes = sum(p.get("likesCount", 0) for p in posts) / n
        avg_comments = sum(p.get("commentsCount", 0) for p in posts) / n
        avg_eng = avg_likes + avg_comments
        likes_hidden = avg_likes < 1
        if likes_hidden:
            # Comment-only fraud check: expect at least 0.02% comment rate
            expected_comments_min = followers * 0.0002
            if avg_comments < expected_comments_min * 0.3:
                fraud_score -= 30
        else:
            expected_min = followers * 0.005
            if avg_eng < expected_min * 0.3:
                fraud_score -= 30

    # Signal 2: Suspicious growth (old posts much higher engagement)
    # Large accounts (1M+) have higher natural variance — raise threshold
    if len(posts) >= 24:
        early = sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts[18:24]) / 6
        recent = sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts[:6]) / 6
        drop_threshold = 5 if followers >= 1_000_000 else 3
        if early / max(recent, 1) > drop_threshold:
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
