SPONSORED_SIGNALS = [
    "#ad", "#sponsored", "#paid", "#partnership",
    "#reklam", "#işbirliği", "#tanıtım",
    "gifted", "in partnership with", "use my code",
    "discount code",
]
# "link in bio" and "#collab" removed — universal phrases, not sponsorship indicators


def _is_sponsored(post: dict) -> bool:
    text = (post.get("caption") or "").lower()
    tags = " ".join(h.lower() for h in (post.get("hashtags") or []))
    combined = text + " " + tags
    return any(s in combined for s in SPONSORED_SIGNALS)


def score_authenticity(raw: dict) -> int:
    posts = raw.get("posts", [])
    followers = raw.get("followers", 1)
    following = raw.get("following", 0)
    score = 100

    if posts:
        engagements = [p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts]
        mean_e = sum(engagements) / len(engagements)
        if any(e > mean_e * 4 for e in engagements):
            score -= 25

    if posts:
        sponsored_ratio = sum(1 for p in posts if _is_sponsored(p)) / len(posts)
        if sponsored_ratio > 0.5:
            score -= 20
        elif sponsored_ratio > 0.3:
            score -= 10

    if following > followers:
        score -= 15

    return max(0, min(100, score))
