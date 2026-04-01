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


def compute_verdict(score: int, followers: int, scores: dict, label: str) -> dict:
    eng   = scores.get("engagement", 50)
    niche = scores.get("niche", 50)
    auth  = scores.get("authenticity", 50)

    if score < 30 or auth < 30:
        verdict       = "avoid"
        verdict_label = "Do Not Collaborate"
        reason = (
            "Multiple red flags detected — low engagement, fraud signals, "
            "or poor niche alignment make this a high-risk spend."
        )
        action = "Skip this influencer. Better options exist for your budget."

    elif followers < 50_000 and score >= 50:
        verdict       = "gifted"
        verdict_label = "Gifted Campaign"
        eng_word   = "strong"  if eng   >= 70 else "decent"
        niche_word = "high"    if niche >= 70 else "moderate"
        reason = (
            f"Micro-influencer with {eng_word} engagement and {niche_word} niche alignment. "
            "Audience is too small for a paid fee to make sense financially, "
            "but product gifting has solid upside here."
        )
        action = "Send 1–2 products. Request one Reel + two Stories. No cash fee."

    elif followers >= 50_000 and score >= 70:
        verdict       = "paid"
        verdict_label = "Paid Partnership"
        eng_word = "above average" if eng >= 70 else "solid"
        reason = (
            f"Strong ROI signals with a substantial audience. "
            f"Engagement is {eng_word} and niche alignment supports conversion."
        )
        action = "Negotiate a paid deal. Start with one Reel to test conversion before a larger commitment."

    elif score >= 50:
        verdict       = "gifted"
        verdict_label = "Gifted Campaign"
        reason = (
            "Decent signals overall but not strong enough to justify a paid fee yet. "
            "Content quality and niche depth need more validation."
        )
        action = "Test with gifted first. If content converts, upgrade to paid next campaign."

    else:
        verdict       = "avoid"
        verdict_label = "Do Not Collaborate"
        reason = (
            "Weak ROI signals. Low engagement or poor niche alignment "
            "makes this a risky spend with low expected return."
        )
        action = "Skip this influencer. The expected ROI does not justify the effort."

    return {
        "verdict":       verdict,
        "verdict_label": verdict_label,
        "reason":        reason,
        "action":        action,
        "campaign_type": _campaign_type(scores),
        "budget_range":  _budget_range(verdict, followers),
        "risk":          _risk_level(scores, label),
    }
