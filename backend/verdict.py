"""
Rule-based verdict + decision engine.

Takes score, follower count, individual factor scores, and label.
Returns a structured decision: what to do, why, campaign type, budget, risk level.
No ML — pure heuristics based on influencer marketing benchmarks.
"""


def _campaign_type(scores: dict) -> str:
    eng   = scores.get("engagement", 50)
    niche = scores.get("niche", 50)
    auth  = scores.get("authenticity", 50)

    if eng >= 70 and niche >= 60:
        return "Reels"
    if auth >= 70 and eng < 60:
        return "UGC"
    if niche < 50:
        return "Stories"
    return "Reels"


def _budget_range(verdict: str, followers: int) -> str:
    if verdict == "avoid":
        return "Not recommended"
    if verdict == "gifted":
        return "$0 cash · product cost only (~$30–80)"
    # paid tiers
    if followers < 20_000:
        return "$100–300 per post"
    if followers < 100_000:
        return "$300–800 per post"
    if followers < 500_000:
        return "$800–3,000 per post"
    return "$3,000+ per post"


def _risk_level(scores: dict, label: str) -> str:
    auth = scores.get("authenticity", 100)
    if label in ("avoid", "risky") or auth < 40:
        return "High"
    if label == "mid" or auth < 65:
        return "Medium"
    return "Low"


def _campaign_instruction(verdict: str, scores: dict, followers: int) -> str:
    """Specific, actionable campaign brief — what to send, what to ask for."""
    eng  = scores.get("engagement", 50)
    auth = scores.get("authenticity", 50)

    if verdict == "avoid":
        return (
            "Do not proceed. Reallocate this budget to higher-scoring profiles. "
            "If you've already made contact, do not commit to any fee."
        )

    ctype = _campaign_type(scores)

    if verdict == "gifted":
        products = "2–3 hero products" if auth >= 65 else "1 product (low commitment)"
        deliverables = (
            "1 Reel (60s review or tutorial) + 2 Stories (unboxing + swipe-up link)"
            if eng >= 60
            else "1 Story set (3 frames: unboxing, use, opinion) + optional Reel at their discretion"
        )
        timeline = "Agree on a 14-day posting window from product receipt."
        usage = "Request 30-day content repurposing rights for paid ads."
        return (
            f"Ship {products}. Brief: {deliverables}. "
            f"{timeline} {usage} No cash fee — product only."
        )

    # paid path
    if followers < 100_000:
        deliverables = "1 Reel (60–90s, featuring your product in the first 3 seconds) + 1 Story set"
        fee_note     = "Start with a single-post deal. Offer a performance bonus if link clicks exceed 300."
    elif followers < 500_000:
        deliverables = "1 dedicated Reel + 2 Story sets + 1 link-in-bio placement (48h)"
        fee_note     = "Negotiate a 2-post package. Lock in content rights for 60 days."
    else:
        deliverables = "1 dedicated Reel + 3 Story sets + link-in-bio placement (72h) + 1 static feed post"
        fee_note     = "Request exclusivity in beauty/skincare for 30 days. Require approval before posting."

    return (
        f"Brief: {deliverables}. "
        f"{fee_note} Provide a UTM-tracked link and a unique discount code to measure attribution."
    )


def _warning_flags(scores: dict, label: str) -> list:
    """Return a list of specific risk flags based on factor scores."""
    flags = []
    if scores.get("authenticity", 100) < 50:
        flags.append("Low authenticity score — possible purchased engagement or scripted content.")
    if scores.get("engagement", 100) < 40:
        flags.append("Engagement rate below category average — weak conversion potential.")
    if scores.get("niche", 100) < 40:
        flags.append("Niche alignment is weak — audience may not match your customer profile.")
    if scores.get("momentum", 100) < 35:
        flags.append("Declining follower growth — account may be losing relevance.")
    if label in ("risky", "avoid"):
        flags.append("Overall score places this influencer in a high-risk tier.")
    return flags


def compute_verdict(score: int, followers: int, scores: dict, label: str) -> dict:
    eng   = scores.get("engagement", 50)
    niche = scores.get("niche", 50)
    auth  = scores.get("authenticity", 50)
    momentum = scores.get("momentum", 50)

    followers_known = followers > 0

    # --- Decision routing ---
    if score < 30 or auth < 30:
        verdict       = "avoid"
        verdict_label = "Do Not Collaborate"
        reason = (
            f"Score of {score}/100 with an authenticity signal of {auth}/100 indicates "
            "significant risk. Likely fraud signals, very low engagement, or near-zero niche "
            "alignment. A paid collaboration here would produce negligible return."
        )

    elif score >= 70 and (not followers_known or followers >= 50_000):
        verdict       = "paid"
        verdict_label = "Paid Partnership"
        eng_word  = "strong" if eng >= 75 else "above average" if eng >= 60 else "acceptable"
        niche_str = f"niche score of {niche}/100"
        auth_str  = f"authenticity at {auth}/100"
        reason = (
            f"This influencer scores {score}/100 — placing them in the '{label}' tier. "
            f"Engagement is {eng_word} ({eng}/100), {niche_str}, and {auth_str}. "
            f"The combination of audience size and content signals justifies a paid fee. "
        )
        if momentum >= 60:
            reason += "Growing momentum adds upside to long-term partnership potential."
        else:
            reason += "Growth has slowed, so treat this as a single campaign test before a retainer."

    elif followers_known and followers < 50_000 and score >= 50:
        verdict       = "gifted"
        verdict_label = "Gifted Campaign"
        eng_word   = "strong" if eng >= 70 else "decent"
        niche_word = "well-aligned" if niche >= 70 else "moderately aligned"
        reason = (
            f"Micro-influencer ({followers:,} followers) with {eng_word} engagement ({eng}/100) "
            f"and a {niche_word} audience ({niche}/100 niche score). "
            "The follower base is too small for a cash fee to produce a positive ROI, "
            "but gifted product has high upside due to the quality of engagement. "
            f"Authenticity score of {auth}/100 suggests the audience trusts their recommendations."
        )

    elif followers_known and followers >= 50_000 and 50 <= score < 70:
        verdict       = "gifted"
        verdict_label = "Gifted Campaign"
        reason = (
            f"Audience size ({followers:,} followers) is large enough for a paid deal, "
            f"but the ROI score of {score}/100 doesn't yet justify the fee. "
            f"Engagement ({eng}/100) or niche alignment ({niche}/100) — or both — "
            "need to be stronger before committing budget. "
            "A gifted campaign reduces your risk while generating proof-of-concept content."
        )

    elif score >= 50:
        verdict       = "gifted"
        verdict_label = "Gifted Campaign"
        reason = (
            f"Score of {score}/100 shows decent signals, but follower count data is unavailable — "
            "making it impossible to size the paid opportunity accurately. "
            f"Engagement ({eng}/100) and authenticity ({auth}/100) suggest real audience trust. "
            "Gifted is the right entry point: low cost, generates real content, and validates "
            "conversion before any cash commitment."
        )

    else:
        verdict       = "avoid"
        verdict_label = "Do Not Collaborate"
        reason = (
            f"Score of {score}/100 reflects weak signals across the board. "
            f"Engagement is {eng}/100, niche alignment is {niche}/100. "
            "The expected return does not justify even a gifted campaign at this time."
        )

    return {
        "verdict":              verdict,
        "verdict_label":        verdict_label,
        "reason":               reason,
        "action":               _campaign_instruction(verdict, scores, followers),
        "campaign_type":        _campaign_type(scores),
        "budget_range":         _budget_range(verdict, followers),
        "risk":                 _risk_level(scores, label),
        "warning_flags":        _warning_flags(scores, label),
    }
