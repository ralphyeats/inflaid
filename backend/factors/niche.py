from categories.config import get_category_config


def _has_keyword(post: dict, keywords: list) -> bool:
    text = (post.get("caption") or "").lower()
    tags = " ".join(h.lower() for h in (post.get("hashtags") or []))
    combined = text + " " + tags
    return any(k in combined for k in keywords)


def _keyword_count(post: dict, keywords: list) -> int:
    text = (post.get("caption") or "").lower()
    tags = " ".join(h.lower() for h in (post.get("hashtags") or []))
    combined = text + " " + tags
    return sum(1 for k in keywords if k in combined)


def score_niche(raw: dict) -> int:
    posts = raw.get("posts", [])
    if not posts:
        return 50

    cfg = get_category_config(raw.get("category", "beauty"))
    keywords = [k.lower() for k in cfg["keywords"]]

    niche_count = sum(1 for p in posts if _has_keyword(p, keywords))
    coverage = niche_count / len(posts)

    total_keywords = sum(_keyword_count(p, keywords) for p in posts)
    depth_score = min(1.0, (total_keywords / len(posts)) / 3)

    recent_posts = posts[:6]
    recent_niche = sum(1 for p in recent_posts if _has_keyword(p, keywords)) / len(recent_posts)

    return int((coverage * 0.4 + depth_score * 0.3 + recent_niche * 0.3) * 100)
