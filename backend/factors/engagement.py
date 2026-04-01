def score_engagement(raw: dict) -> int:
    posts = raw.get("posts", [])
    followers = raw.get("followers", 1)

    if not posts:
        return 50

    valid = [p for p in posts if p.get("likesCount") is not None]
    posts = valid if valid else posts

    n = len(posts)
    avg_likes = sum(p.get("likesCount") or 0 for p in posts) / n
    avg_comments = sum(p.get("commentsCount") or 0 for p in posts) / n

    if avg_likes == 0 and avg_comments > 0:
        # Likes hidden — use comment-only rate with higher multiplier
        engagement_rate = avg_comments / max(followers, 1) * 100
        raw_score = min(100.0, engagement_rate * 60)
    else:
        engagement_rate = (avg_likes + avg_comments) / max(followers, 1) * 100
        raw_score = min(100.0, engagement_rate * 12)

    comment_ratio = avg_comments / (avg_likes + 1)
    if comment_ratio >= 0.05:
        quality_bonus = 15
    elif comment_ratio >= 0.02:
        quality_bonus = 8
    else:
        quality_bonus = 0

    engagements = [(p.get("likesCount") or 0) + (p.get("commentsCount") or 0) for p in posts]
    if len(engagements) > 1:
        mean_e = sum(engagements) / len(engagements)
        std_e = (sum((e - mean_e) ** 2 for e in engagements) / len(engagements)) ** 0.5
        variance_ratio = std_e / (mean_e + 1)
        if variance_ratio > 2.0:
            variance_penalty = -15
        elif variance_ratio > 1.0:
            variance_penalty = -7
        else:
            variance_penalty = 0
    else:
        variance_penalty = 0

    return min(100, max(0, int(raw_score + quality_bonus + variance_penalty)))
