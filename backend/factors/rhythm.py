from datetime import datetime


def _parse_ts(ts_str: str):
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def score_rhythm(raw: dict) -> int:
    posts = raw.get("posts", [])
    timestamps = sorted(
        [t for t in (_parse_ts(p.get("timestamp")) for p in posts) if t],
        reverse=True,
    )

    if len(timestamps) < 2:
        return 50

    intervals = [max(0, (timestamps[i] - timestamps[i + 1]).days) for i in range(len(timestamps) - 1)]

    avg_interval = sum(intervals) / len(intervals)
    std_interval = (sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)) ** 0.5

    # Realistic posting benchmarks for beauty creators:
    # Daily (≤2d): exceptional, 90
    # 3-5x/week (≤3d): very active, 80
    # Weekly (≤7d): solid, 70
    # Bi-weekly (≤14d): normal for quality creators, 55
    # Monthly-ish (≤30d): low but not disqualifying, 35
    # Rarely (>30d): inactive, 15
    if avg_interval <= 2:
        base = 90
    elif avg_interval <= 3:
        base = 80
    elif avg_interval <= 7:
        base = 70
    elif avg_interval <= 14:
        base = 55
    elif avg_interval <= 30:
        base = 35
    else:
        base = 15

    consistency_bonus = max(0, 12 - int(std_interval * 1.2))
    return min(100, max(0, base + consistency_bonus))
