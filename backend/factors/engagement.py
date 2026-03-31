def score_engagement(raw: dict) -> int:
    posts = raw.get("posts", [])
    followers = raw.get("followers", 1)

    if not posts:
        return 50

    n = len(posts)
    total_likes = sum(p.get("likesCount", 0) for p in posts)
    total_comments = sum(p.get("commentsCount", 0) for p in posts)
    avg_likes = total_likes / n
    avg_comments = total_comments / n

    engagement_rate = (total_likes + total_comments) / max(followers, 1) * 100
    raw_score = int(engagement_rate)

    comment_ratio = avg_comments / (avg_likes + 1)
    if comment_ratio >= 0.05:
        quality_bonus = 15
    elif comment_ratio >= 0.02:
        quality_bonus = 8
    else:
        quality_bonus = 0

    engagements = [p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts]
    if len(engagements) > 1:
        mean_e = sum(engagements) / len(engagements)
        std_e = (sum((e - mean_e) ** 2 for e in engagements) / len(engagements)) ** 0.5
        variance_ratio = std_e / (mean_e + 1)
        if variance_ratio > 1.2:
            variance_penalty = -15
        elif variance_ratio > 0.5:
            variance_penalty = -7
        else:
            variance_penalty = 0
    else:
        variance_penalty = 0

    final_score = raw_score + quality_bonus + variance_penalty
    return int(min(100, max(0, final_score)))
