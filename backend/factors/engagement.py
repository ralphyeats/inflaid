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

    # Tier-based multiplier — large accounts naturally have lower ER.
    # Calibrated so "industry average ER for that tier" maps to ~60.
    # Mega (5M+): avg ER ~0.7%  → multiplier 80
    # Macro (1M-5M): avg ER ~1.2% → multiplier 50
    # Mid (100k-1M): avg ER ~2%  → multiplier 28
    # Micro (10k-100k): avg ER ~3.5% → multiplier 17
    # Nano (<10k): avg ER ~5%    → multiplier 12
    if followers >= 5_000_000:
        multiplier = 80
    elif followers >= 1_000_000:
        multiplier = 58
    elif followers >= 500_000:
        multiplier = 52
    elif followers >= 100_000:
        multiplier = 42
    elif followers >= 10_000:
        multiplier = 22
    else:
        multiplier = 12

    if avg_likes == 0 and avg_comments > 0:
        # Likes hidden — use comment-only rate with higher multiplier
        engagement_rate = avg_comments / max(followers, 1) * 100
        raw_score = min(100.0, engagement_rate * multiplier * 5)
    else:
        engagement_rate = (avg_likes + avg_comments) / max(followers, 1) * 100
        raw_score = min(100.0, engagement_rate * multiplier)

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
