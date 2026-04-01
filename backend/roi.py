"""
Heuristic ROI estimation engine.

Outputs reach and conversion estimates based on engagement signals.
Frontend multiplies estimated_conversions by the brand's AOV to get revenue projection.

All numbers are model-based benchmarks — clearly labelled as estimates, not tracking data.
"""


def _raw_engagement_rate(posts: list, followers: int) -> float:
    """Actual engagement rate from raw post data (not the 0-100 score)."""
    if not posts or followers <= 0:
        return 0.0
    total = sum(
        (p.get("likesCount") or 0) + (p.get("commentsCount") or 0)
        for p in posts
    )
    return total / len(posts) / followers


def compute_roi_estimate(raw: dict, scores: dict) -> dict:
    posts     = raw.get("posts", []) or []
    followers = raw.get("followers") or 0

    if followers <= 0:
        return _empty_estimate("Follower count unavailable — reach estimate requires follower data.")

    eng_rate        = _raw_engagement_rate(posts, followers)
    niche_score     = scores.get("niche", 50)
    auth_score      = scores.get("authenticity", 50)
    engagement_score = scores.get("engagement", 50)

    # --- Reach model ---
    # Reel reach: engagement-driven, can exceed followers for high-engagement accounts.
    # Story reach: typically 5–12% of followers.
    # We model a standard 1 Reel + 2 Stories campaign.
    reel_reach  = followers * min(eng_rate * 15, 0.9)   # cap at 90% of followers
    story_reach = followers * 0.08                       # ~8% per story
    blended     = reel_reach * 0.6 + story_reach * 2 * 0.4

    # --- Conversion model ---
    # CTR driven by niche alignment (do followers care about this category?)
    ctr = (niche_score / 100) * 0.025 + 0.005   # 0.5% base, up to 3%

    # CVR driven by trust (authenticity) + intent (engagement)
    cvr = ((auth_score + engagement_score) / 200) * 0.02 + 0.005

    conversions_mid  = blended * ctr * cvr
    conversions_low  = conversions_mid * 0.6
    conversions_high = conversions_mid * 1.8

    # Confidence based on data quality
    if len(posts) >= 10 and followers > 0:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "estimated_reach_low":        max(1, round(blended * 0.7)),
        "estimated_reach_high":       max(1, round(blended * 1.3)),
        "estimated_conversions_low":  max(1, round(conversions_low)),
        "estimated_conversions_high": max(1, round(conversions_high)),
        "confidence":                 confidence,
        "note": (
            f"Based on {len(posts)} recent posts and industry benchmarks "
            f"for beauty/skincare influencer campaigns. Actual results vary."
        ),
    }


def _empty_estimate(reason: str) -> dict:
    return {
        "estimated_reach_low":        None,
        "estimated_reach_high":       None,
        "estimated_conversions_low":  None,
        "estimated_conversions_high": None,
        "confidence":                 "none",
        "note":                       reason,
    }
