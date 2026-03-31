"""
Vettly ROI Scorer — 7-factor modular system with fraud multiplier.

Formula:
  score = round(weighted_sum * fraud_multiplier)

  weighted_sum = engagement*0.30 + rhythm*0.20 + audience*0.20
               + niche*0.15 + authenticity*0.10 + momentum*0.05
  (each factor is 0-100, weights sum to 1.0, so weighted_sum is 0-100)

Labels: elite(85+) | high(70+) | mid(50+) | risky(30+) | avoid(<30)
"""

from dataclasses import dataclass

from factors.engagement import score_engagement
from factors.rhythm import score_rhythm
from factors.audience import score_audience
from factors.niche import score_niche
from factors.authenticity import score_authenticity
from factors.momentum import score_momentum
from factors.fraud import compute_fraud_multiplier
from factors.sentiment import score_sentiment

WEIGHTS = {
    "engagement":   0.30,
    "rhythm":       0.20,
    "audience":     0.20,
    "niche":        0.15,
    "authenticity": 0.10,
    "momentum":     0.05,
}

LABELS = {
    "engagement":   "Engagement Quality",
    "rhythm":       "Content Rhythm",
    "audience":     "Audience Reliability",
    "niche":        "Niche Depth",
    "authenticity": "Authenticity",
    "momentum":     "Growth Momentum",
}


@dataclass
class ScoreResult:
    handle: str
    score: int
    label: str
    breakdown: list
    insight: str


def compute_score(raw: dict) -> ScoreResult:
    handle = raw.get("handle", "unknown")

    scores = {k: f(raw) for k, f in [
        ("engagement",   score_engagement),
        ("rhythm",       score_rhythm),
        ("audience",     score_audience),
        ("niche",        score_niche),
        ("authenticity", score_authenticity),
        ("momentum",     score_momentum),
    ]}

    sentiment = score_sentiment(raw)
    fraud_multiplier = compute_fraud_multiplier(raw, scores, sentiment)

    weighted_sum = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    final_score = max(0, min(100, round(weighted_sum * fraud_multiplier)))

    label = _label(final_score)
    breakdown = [
        {
            "key":          k,
            "label":        LABELS[k],
            "description":  f"{LABELS[k]} score: {scores[k]}/100.",
            "value":        scores[k],
            "weight":       WEIGHTS[k],
            "contribution": round(scores[k] * WEIGHTS[k], 2),
        }
        for k in WEIGHTS
    ]
    insight = _build_insight(final_score, label, scores, fraud_multiplier, sentiment)

    return ScoreResult(handle=handle, score=final_score, label=label,
                       breakdown=breakdown, insight=insight)


def _label(score: int) -> str:
    if score >= 85: return "elite"
    if score >= 70: return "high"
    if score >= 50: return "mid"
    if score >= 30: return "risky"
    return "avoid"


def _build_insight(score, label, scores, fraud_multiplier, sentiment) -> str:
    lines = []

    top = max(scores, key=scores.get)
    lines.append(f"{LABELS[top]} is the strongest signal at {scores[top]}/100.")

    if scores["engagement"] >= 75:
        lines.append("Engagement rate is well above average — strong buying signal.")
    elif scores["engagement"] < 40:
        lines.append("Engagement rate is low — weak conversion potential.")

    if fraud_multiplier < 1.0:
        lines.append(f"Fraud signals detected — score reduced by {int((1 - fraud_multiplier) * 100)}%.")

    if sentiment and sentiment.get("purchase_intent_ratio", 0) > 0.3:
        lines.append("Comment analysis shows high purchase intent — strong ROI signal.")

    verdicts = {
        "elite": f"Elite conversion candidate. ROI score {score}/100.",
        "high":  f"Strong ROI potential. Safe choice for paid partnerships. Score {score}/100.",
        "mid":   f"Better suited for brand awareness than direct conversion. Score {score}/100.",
        "risky": f"Risk signals present. Proceed with caution. Score {score}/100.",
        "avoid": f"Multiple red flags. Not recommended for paid partnerships. Score {score}/100.",
    }
    lines.append(verdicts[label])

    return " ".join(lines)
