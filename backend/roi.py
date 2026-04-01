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

    niche_score      = scores.get("niche", 50)
    auth_score       = scores.get("authenticity", 50)
    engagement_score = scores.get("engagement", 50)

    # --- Engagement rate: real data if available, else derive from score ---
    if posts:
        eng_rate = _raw_engagement_rate(posts, followers)
        eng_rate = min(eng_rate, 0.20)   # cap outliers from tiny post samples
    else:
        # Fallback: map engagement score (0–100) → realistic rate (0.5%–8%)
        eng_rate = 0.005 + (engagement_score / 100) * 0.075

    # --- Reach model (1 Reel + 2 Stories campaign) ---
    reel_reach  = followers * min(eng_rate * 15, 0.9)
    story_reach = followers * 0.08
    blended     = reel_reach * 0.6 + story_reach * 2 * 0.4

    # --- Conversion model ---
    ctr = (niche_score / 100) * 0.025 + 0.005        # 0.5% base, up to 3%
    cvr = ((auth_score + engagement_score) / 200) * 0.02 + 0.005

    conversions_mid  = blended * ctr * cvr
    conversions_low  = conversions_mid * 0.6
    conversions_high = conversions_mid * 1.8

    # --- Confidence ---
    if len(posts) >= 20 and followers > 10_000:
        confidence = "high"
    elif len(posts) >= 10:
        confidence = "medium"
    else:
        confidence = "low"

    # --- Confidence explanation ---
    if confidence == "high":
        confidence_explanation = (
            f"High confidence. Estimate is based on {len(posts)} posts with verified follower data. "
            "Enough data points to produce a reliable engagement rate and reach model."
        )
    elif confidence == "medium":
        confidence_explanation = (
            f"Medium confidence. Based on {len(posts)} posts — sufficient for a directional estimate "
            "but not enough to fully account for post-type variance (Reels vs Stories vs carousels). "
            "Treat the range as a planning input, not a guarantee."
        )
    else:
        if posts:
            confidence_explanation = (
                f"Low confidence. Only {len(posts)} post(s) available — too few to establish a "
                "reliable engagement rate. The estimate uses available data plus category benchmarks. "
                "Verify performance manually before committing budget."
            )
        else:
            confidence_explanation = (
                "Low confidence. No post data available — reach and conversions are estimated "
                "from the engagement score and industry benchmarks only. "
                "Treat these numbers as rough directional estimates. "
                "Request a media kit from the influencer to validate before committing spend."
            )

    # --- Reach explanation ---
    reach_low  = max(1, round(blended * 0.7))
    reach_high = max(1, round(blended * 1.3))
    conv_low   = max(1, round(conversions_low))
    conv_high  = max(1, round(conversions_high))

    eng_pct = round(eng_rate * 100, 2)
    reach_explanation = (
        f"For a standard campaign (1 Reel + 2 Stories), we estimate {reach_low:,}–{reach_high:,} "
        f"total impressions based on a {eng_pct}% engagement rate and {followers:,} followers. "
        "Reel reach is modelled at 60% of blended exposure; Stories at 40%."
    )

    conversion_explanation = (
        f"Estimated {conv_low}–{conv_high} conversions based on a "
        f"~{round((niche_score/100)*0.025 + 0.005, 3)*100:.1f}% click-through rate "
        f"(driven by niche alignment score of {niche_score}/100) and "
        f"~{round(((auth_score + engagement_score)/200)*0.02 + 0.005, 3)*100:.1f}% conversion rate "
        f"(driven by authenticity {auth_score}/100 + engagement {engagement_score}/100). "
        "Multiply by your product's average order value to project revenue."
    )

    data_source = f"{len(posts)} recent posts" if posts else "engagement score (no post data)"
    return {
        "estimated_reach_low":        reach_low,
        "estimated_reach_high":       reach_high,
        "estimated_conversions_low":  conv_low,
        "estimated_conversions_high": conv_high,
        "confidence":                 confidence,
        "confidence_explanation":     confidence_explanation,
        "reach_explanation":          reach_explanation,
        "conversion_explanation":     conversion_explanation,
        "note": (
            f"Based on {data_source} and industry benchmarks "
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
        "confidence_explanation":     reason,
        "reach_explanation":          None,
        "conversion_explanation":     None,
        "note":                       reason,
    }
