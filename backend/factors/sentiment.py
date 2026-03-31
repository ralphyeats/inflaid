import os
import json
from datetime import date

_client = None
_daily_count = {"date": None, "count": 0}
DAILY_CAP = 50


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _within_cap() -> bool:
    today = date.today().isoformat()
    if _daily_count["date"] != today:
        _daily_count["date"] = today
        _daily_count["count"] = 0
    return _daily_count["count"] < DAILY_CAP


def _extract_comments(raw: dict) -> list:
    comments = []
    for post in raw.get("posts", [])[:10]:
        for c in (post.get("latestComments") or [])[:3]:
            text = (c.get("text") or "").strip()
            if text:
                comments.append(text)
    return comments[:30]


def score_sentiment(raw: dict) -> dict:
    comments = _extract_comments(raw)

    if not comments:
        return {"spam_ratio": 0.1, "purchase_intent_ratio": 0.1, "fraud_risk": 0.1, "source": "no_comments"}

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not _within_cap():
        return _keyword_fallback(comments)

    try:
        client = _get_client()
        prompt = (
            f"Analyze these {len(comments)} Instagram comments and return ONLY valid JSON.\n\n"
            f"Comments:\n" + "\n".join(f"- {c}" for c in comments) +
            "\n\nReturn JSON with:\n"
            "- spam_ratio: float 0-1 (generic/emoji-only/bot-like)\n"
            "- purchase_intent_ratio: float 0-1 (buying interest, price questions)\n"
            "- fraud_risk: float 0-1 (bot patterns, suspiciously uniform)\n"
            "- summary: string (one sentence insight)"
        )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        _daily_count["count"] += 1

        text = response.content[0].text.strip()
        if "```" in text:
            parts = text.split("```")
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]

        result = json.loads(text.strip())
        result["source"] = "claude"
        return result

    except Exception as e:
        print(f"Sentiment error: {e}")
        return _keyword_fallback(comments)


def _keyword_fallback(comments: list) -> dict:
    spam_signals = ["nice", "great", "amazing", "follow me", "check my", "👍", "❤️", "🔥"]
    intent_signals = ["price", "where", "buy", "shop", "link", "how much", "available", "order"]

    total = len(comments)
    spam = sum(1 for c in comments if any(s in c.lower() for s in spam_signals)) / total
    intent = sum(1 for c in comments if any(s in c.lower() for s in intent_signals)) / total

    return {
        "spam_ratio": round(spam, 3),
        "purchase_intent_ratio": round(intent, 3),
        "fraud_risk": round(spam * 0.5, 3),
        "source": "fallback",
    }
