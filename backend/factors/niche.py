BEAUTY_KEYWORDS = [
    "skincare", "makeup", "beauty", "skin", "glow", "routine", "serum",
    "moisturizer", "foundation", "lipstick", "hair", "cosmetic", "fashion",
    "style", "makyaj", "guzellik", "cilt", "ruj", "fondoten", "kirpik",
    "макияж", "красота", "уход", "косметика", "beaute", "maquillage",
    "belleza", "maquillaje",
]


def _has_keyword(post: dict) -> bool:
    text = (post.get("caption") or "").lower()
    tags = " ".join(h.lower() for h in (post.get("hashtags") or []))
    combined = text + " " + tags
    return any(k in combined for k in BEAUTY_KEYWORDS)


def _keyword_count(post: dict) -> int:
    text = (post.get("caption") or "").lower()
    tags = " ".join(h.lower() for h in (post.get("hashtags") or []))
    combined = text + " " + tags
    return sum(1 for k in BEAUTY_KEYWORDS if k in combined)


def score_niche(raw: dict) -> int:
    posts = raw.get("posts", [])
    if not posts:
        return 50

    niche_count = sum(1 for p in posts if _has_keyword(p))
    coverage = niche_count / len(posts)

    total_keywords = sum(_keyword_count(p) for p in posts)
    depth_score = min(1.0, (total_keywords / len(posts)) / 5)

    recent_posts = posts[:6]
    recent_niche = sum(1 for p in recent_posts if _has_keyword(p)) / len(recent_posts)

    return int((coverage * 0.4 + depth_score * 0.3 + recent_niche * 0.3) * 100)
