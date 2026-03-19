"""
ROI scoring logic — 5 conversion signals.

Weights:
  comment_quality      35%
  before_after_ratio   25%
  audience_fit         20%
  niche_consistency    15%
  authenticity_penalty -5% (penalty, lower raw score = bigger deduction)
"""

from dataclasses import dataclass


WEIGHTS = {
    "comment_quality": 0.35,
    "before_after_ratio": 0.25,
    "audience_fit": 0.20,
    "niche_consistency": 0.15,
    "authenticity_penalty": -0.05,
}

FACTOR_META = {
    "comment_quality": {
        "label": "Product-question comments",
        "desc_template": "Purchase-intent comments make up {value}% of recent comments.",
    },
    "before_after_ratio": {
        "label": "Before / after content ratio",
        "desc_template": "{value}% of posts show results or transformations.",
    },
    "audience_fit": {
        "label": "Audience demographic fit",
        "desc_template": "Audience demographic overlap with typical buyers is {value}/100.",
    },
    "niche_consistency": {
        "label": "Niche consistency",
        "desc_template": "Niche focus score is {value}/100 — measures topic drift over time.",
    },
    "authenticity_penalty": {
        "label": "Authenticity penalty",
        "desc_template": "Authenticity check score: {value}/100. Lower = more red flags.",
    },
}


@dataclass
class FactorResult:
    key: str
    label: str
    description: str
    value: int       # 0–100 raw signal score
    weight: float    # e.g. 0.35
    contribution: float  # weighted contribution to final score


@dataclass
class ScoreResult:
    handle: str
    score: int
    label: str       # "high" | "mid" | "low"
    breakdown: list[FactorResult]
    insight: str


def compute_score(raw: dict) -> ScoreResult:
    """
    raw: dict with keys matching WEIGHTS, each value 0–100.
    Example:
        {
            "comment_quality": 88,
            "before_after_ratio": 75,
            "audience_fit": 80,
            "niche_consistency": 90,
            "authenticity_penalty": 100,  # 100 = clean, 0 = very suspicious
        }
    """
    handle = raw.get("handle", "unknown")

    breakdown = []
    weighted_sum = 0.0

    for key, weight in WEIGHTS.items():
        value = int(raw.get(key, 50))
        value = max(0, min(100, value))

        if key == "authenticity_penalty":
            # Penalty: authenticity score of 100 = no deduction (0 penalty applied)
            #          authenticity score of 0   = full -5 applied
            # contribution = weight * (value / 100)  → negative weight * fraction lost
            contribution = weight * ((100 - value) / 100)  # weight is -0.05
        else:
            contribution = weight * (value / 100)

        weighted_sum += contribution

        meta = FACTOR_META[key]
        breakdown.append(FactorResult(
            key=key,
            label=meta["label"],
            description=meta["desc_template"].format(value=value),
            value=value,
            weight=weight,
            contribution=round(contribution * 100, 2),
        ))

    score = max(0, min(100, round(weighted_sum * 100)))

    if score >= 70:
        label = "high"
    elif score >= 40:
        label = "mid"
    else:
        label = "low"

    insight = _build_insight(handle, score, label, breakdown, raw)

    return ScoreResult(
        handle=handle,
        score=score,
        label=label,
        breakdown=breakdown,
        insight=insight,
    )


def _build_insight(handle: str, score: int, label: str, breakdown: list[FactorResult], raw: dict) -> str:
    cq = raw.get("comment_quality", 50)
    ba = raw.get("before_after_ratio", 50)
    auth = raw.get("authenticity_penalty", 100)

    lines = []

    # Lead with the strongest signal
    top_factor = max(
        [f for f in breakdown if f.key != "authenticity_penalty"],
        key=lambda f: f.value,
    )
    lines.append(
        f"{top_factor.label} is the strongest signal at {top_factor.value}/100."
    )

    # Comment quality context
    if cq >= 80:
        lines.append(
            f"Purchase-intent comments at {cq}% place this account well above the category average."
        )
    elif cq >= 50:
        lines.append(f"Comment purchase-intent rate of {cq}% is near the category average.")
    else:
        lines.append(
            f"Product-question comment rate is only {cq}% — low buying signal from the audience."
        )

    # Before/after context
    if ba >= 70:
        lines.append(f"Results-driven content makes up {ba}% of posts — a strong conversion driver.")
    elif ba < 40:
        lines.append(f"Before/after content is underrepresented at {ba}% — mostly aesthetic posts.")

    # Authenticity
    if auth < 60:
        lines.append(
            "⚠ Authenticity signals are concerning: engagement drops or follower spikes detected. "
            "Not recommended for paid partnerships."
        )
    elif auth < 85:
        lines.append("Minor authenticity inconsistencies detected — monitor before committing to a deal.")

    # Final verdict
    if label == "high":
        lines.append(f"Overall: strong conversion candidate. ROI score {score}/100.")
    elif label == "mid":
        lines.append(
            f"Overall: better suited for brand awareness than direct conversion. ROI score {score}/100."
        )
    else:
        lines.append(f"Overall: risk signals present. Proceed with caution. ROI score {score}/100.")

    return " ".join(lines)
