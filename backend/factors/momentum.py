def score_momentum(raw: dict) -> int:
    posts = raw.get("posts", [])

    if len(posts) < 7:
        return 50

    def avg_eng(subset):
        if not subset:
            return 1
        return sum((p.get("likesCount") or 0) + (p.get("commentsCount") or 0) for p in subset) / len(subset)

    mid = len(posts) // 2
    recent = avg_eng(posts[:mid])
    older = avg_eng(posts[mid:])
    ratio = recent / max(older, 1)

    if ratio >= 1.3:
        return 100
    elif ratio >= 1.1:
        return 75
    elif ratio >= 0.9:
        return 50
    elif ratio >= 0.7:
        return 25
    else:
        return 0
