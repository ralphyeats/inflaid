def score_audience(raw: dict) -> int:
    followers = raw.get("followers", 1)
    following = raw.get("following", 1)
    posts = raw.get("posts", [])

    ff_ratio = followers / max(following, 1)

    if not posts:
        return 20

    n = len(posts)
    avg_engagement = sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts) / n
    if followers < 10_000:
        expected_rate = 0.05
    elif followers < 100_000:
        expected_rate = 0.03
    elif followers < 1_000_000:
        expected_rate = 0.015
    else:
        expected_rate = 0.005
    expected = followers * expected_rate
    fulfillment = avg_engagement / max(expected, 1)

    if fulfillment >= 1.0 and ff_ratio >= 5:
        return 95
    elif fulfillment >= 0.7 and ff_ratio >= 2:
        return 75
    elif fulfillment >= 0.4:
        return 50
    else:
        return 20
