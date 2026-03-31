# Vettly — Faz 1: Scoring Engine Yeniden Yazımı
**Tarih:** 2026-03-27
**Kapsam:** Backend scoring sistemi, fraud detection, Claude API sentiment entegrasyonu, frontend bug fix
**Değişmeyen:** main.py, auth.py, Supabase tabloları, Apify entegrasyonu, frontend tasarımı

---

## 1. Hedef

Mevcut 5 faktörlü, kademeli skorlama sistemini 7 faktörlü, continuous + fraud multiplier'lı sisteme yükseltmek. Temel felsefe değişikliği:

> **Eski:** "Bu influencer aktif mi?"
> **Yeni:** "Bu influencer gerçek satın almaya dönüştürür mü?"

---

## 2. Dosya Yapısı

```
backend/
├── main.py          — ScoreRequest'e category field eklenir
├── scraper.py       — ham veri döndürür, faktör hesaplamaları çıkarılır
├── scorer.py        — orchestrator (~50 satır)
├── auth.py          — değişmez
└── factors/
    ├── __init__.py
    ├── engagement.py    — Faktör 1: Engagement kalitesi (%30)
    ├── rhythm.py        — Faktör 2: İçerik ritmi (%20)
    ├── audience.py      — Faktör 3: Kitle güvenilirliği (%20)
    ├── niche.py         — Faktör 4: Niche derinliği (%15)
    ├── authenticity.py  — Faktör 5: Özgünlük / red flags (%10)
    ├── momentum.py      — Faktör 6: Büyüme momentumu (%5)
    ├── fraud.py         — Fraud multiplier (çarpan, ağırlık dışı)
    └── sentiment.py     — Claude Sonnet 4.6, günlük 50 cap
```

---

## 3. scraper.py Değişikliği

Mevcut `scraper.py` içindeki `comment_quality`, `before_after_ratio`, `audience_fit`, `niche_consistency`, `authenticity_penalty` hesaplamalarının tamamı silinir.

`_fetch_apify()` şunu döndürür:

```python
{
    "handle": str,
    "name": str,
    "followers": int,
    "following": int,
    "posts": list,          # latestPosts raw listesi
    "is_business": bool,
    "verified": bool,
    "bio_url": str,
    "platform": "instagram",
    "mock": bool,
}
```

`posts` listesindeki her öğe Apify'ın döndürdüğü raw obje — `likesCount`, `commentsCount`, `caption`, `hashtags`, `timestamp`, `latestComments` alanları kullanılır.

Mock profiller de aynı yapıya güncellenir.

---

## 4. scorer.py (Orchestrator)

```python
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

def compute_score(raw: dict) -> ScoreResult:
    scores = {
        "engagement":   score_engagement(raw),
        "rhythm":       score_rhythm(raw),
        "audience":     score_audience(raw),
        "niche":        score_niche(raw),
        "authenticity": score_authenticity(raw),
        "momentum":     score_momentum(raw),
    }

    sentiment_result = score_sentiment(raw)   # Claude API veya fallback
    fraud_multiplier = compute_fraud_multiplier(raw, scores, sentiment_result)

    weighted_sum = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    final_score = max(0, min(100, round(weighted_sum * 100 * fraud_multiplier)))

    label = _label(final_score)
    breakdown = _build_breakdown(scores, sentiment_result, fraud_multiplier)
    insight = _build_insight(raw["handle"], final_score, label, scores, sentiment_result)

    return ScoreResult(handle=raw["handle"], score=final_score, label=label,
                       breakdown=breakdown, insight=insight)
```

---

## 5. Faktör Modülleri

### 5.1 engagement.py — %30

```python
def score_engagement(raw) -> int:
    posts = raw.get("posts", [])
    followers = raw.get("followers", 1)
    if not posts:
        return 50

    # Katman 1: Continuous engagement rate
    n = len(posts)
    avg_likes = sum(p.get("likesCount", 0) for p in posts) / n
    avg_comments = sum(p.get("commentsCount", 0) for p in posts) / n
    engagement_rate = (avg_likes + avg_comments) / followers * 100
    raw_score = min(100, engagement_rate * 12)

    # Katman 2: Yorum/like oranı (kalite sinyali)
    comment_ratio = avg_comments / (avg_likes + 1)
    if comment_ratio >= 0.05:   quality_bonus = 15
    elif comment_ratio >= 0.02: quality_bonus = 8
    else:                       quality_bonus = 0

    # Katman 3: Tutarsızlık cezası (yapay spike tespiti)
    engagements = [p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts]
    if len(engagements) > 1:
        mean_e = sum(engagements) / len(engagements)
        std_e = (sum((e - mean_e)**2 for e in engagements) / len(engagements)) ** 0.5
        variance_ratio = std_e / (mean_e + 1)
        if variance_ratio > 2.0:   variance_penalty = -15
        elif variance_ratio > 1.0: variance_penalty = -7
        else:                      variance_penalty = 0
    else:
        variance_penalty = 0

    return min(100, max(0, int(raw_score + quality_bonus + variance_penalty)))
```

### 5.2 rhythm.py — %20

Timestamp'leri parse eder, post aralıklarının ortalaması ve standart sapmasını hesaplar.

```python
def score_rhythm(raw) -> int:
    posts = raw.get("posts", [])
    if len(posts) < 2:
        return 50

    timestamps = [parse_timestamp(p.get("timestamp")) for p in posts if p.get("timestamp")]
    timestamps = sorted([t for t in timestamps if t], reverse=True)
    if len(timestamps) < 2:
        return 50

    intervals = [(timestamps[i] - timestamps[i+1]).days for i in range(len(timestamps)-1)]
    avg_interval = sum(intervals) / len(intervals)
    std_interval = (sum((x - avg_interval)**2 for x in intervals) / len(intervals)) ** 0.5

    if avg_interval <= 3:    base = 90
    elif avg_interval <= 7:  base = 70
    elif avg_interval <= 14: base = 45
    else:                    base = 20

    consistency_bonus = max(0, 15 - int(std_interval * 2))
    return min(100, base + consistency_bonus)
```

### 5.3 audience.py — %20

Follower/following oranı + engagement fulfillment kombinasyonu.

```python
def score_audience(raw) -> int:
    followers = raw.get("followers", 1)
    following = raw.get("following", 1)
    posts = raw.get("posts", [])

    ff_ratio = followers / max(following, 1)
    n = len(posts) if posts else 1
    avg_engagement = sum(
        p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts
    ) / n
    expected = followers * 0.03
    fulfillment = avg_engagement / max(expected, 1)

    if fulfillment >= 1.0 and ff_ratio >= 5:   return 95
    elif fulfillment >= 0.7 and ff_ratio >= 2:  return 75
    elif fulfillment >= 0.4:                    return 50
    else:                                       return 20
```

### 5.4 niche.py — %15

3 boyutlu analiz: coverage, depth, recency.

```python
BEAUTY_KEYWORDS = [
    "skincare", "makeup", "beauty", "skin", "glow", "routine", "serum",
    "moisturizer", "foundation", "lipstick", "hair", "cosmetic", "fashion",
    "style", "makyaj", "guzellik", "cilt", "ruj", "fondoten",
    "макияж", "красота", "уход", "beaute", "maquillage", "belleza",
]

def score_niche(raw) -> int:
    posts = raw.get("posts", [])
    if not posts:
        return 50

    def has_keyword(post):
        text = (post.get("caption") or "").lower()
        tags = [h.lower() for h in (post.get("hashtags") or [])]
        all_text = text + " " + " ".join(tags)
        return any(k in all_text for k in BEAUTY_KEYWORDS)

    def keyword_count(post):
        text = (post.get("caption") or "").lower()
        tags = [h.lower() for h in (post.get("hashtags") or [])]
        all_text = text + " " + " ".join(tags)
        return sum(1 for k in BEAUTY_KEYWORDS if k in all_text)

    niche_posts = [p for p in posts if has_keyword(p)]
    coverage = len(niche_posts) / len(posts)
    depth_score = min(1.0, (sum(keyword_count(p) for p in posts) / len(posts)) / 5)
    recent = sum(1 for p in posts[:6] if has_keyword(p)) / 6

    return int((coverage * 0.4 + depth_score * 0.3 + recent * 0.3) * 100)
```

### 5.5 authenticity.py — %10

100'den başlar, red flag'ler düşürür.

```python
SPONSORED_SIGNALS = [
    "#ad", "#sponsored", "#paid", "#partnership", "#collab",
    "#reklam", "#işbirliği", "#tanıtım",
    "gifted", "in partnership with", "use my code",
    "discount code", "link in bio",
]

def score_authenticity(raw) -> int:
    posts = raw.get("posts", [])
    followers = raw.get("followers", 1)
    following = raw.get("following", 1)
    score = 100

    # Red Flag 1: Engagement spike'ları
    if posts:
        engagements = [p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts]
        mean_e = sum(engagements) / len(engagements)
        if any(e > mean_e * 4 for e in engagements):
            score -= 25

    # Red Flag 2: Aşırı sponsored içerik
    if posts:
        def is_sponsored(post):
            text = (post.get("caption") or "").lower()
            tags = [h.lower() for h in (post.get("hashtags") or [])]
            all_text = text + " " + " ".join(tags)
            return any(s in all_text for s in SPONSORED_SIGNALS)

        sponsored_ratio = sum(1 for p in posts if is_sponsored(p)) / len(posts)
        if sponsored_ratio > 0.5:   score -= 20
        elif sponsored_ratio > 0.3: score -= 10

    # Red Flag 3: Following > Followers
    if following > followers:
        score -= 15

    return max(0, min(100, score))
```

### 5.6 momentum.py — %5

Son 12 post ile önceki 12'yi karşılaştırır.

```python
def score_momentum(raw) -> int:
    posts = raw.get("posts", [])
    if len(posts) < 13:
        return 50

    def avg_eng(subset):
        if not subset:
            return 1
        return sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in subset) / len(subset)

    recent = avg_eng(posts[:12])
    older  = avg_eng(posts[12:24])
    ratio  = recent / max(older, 1)

    if ratio >= 1.3:   return 100
    elif ratio >= 1.1: return 75
    elif ratio >= 0.9: return 50
    elif ratio >= 0.7: return 25
    else:              return 0
```

---

## 6. fraud.py — Fraud Multiplier

```python
def compute_fraud_multiplier(raw, scores, sentiment_result) -> float:
    followers = raw.get("followers", 1)
    following = raw.get("following", 1)
    posts = raw.get("posts", [])
    fraud_score = 100
    fraud_flags = []

    # Sinyal 1: Ghost followers
    if posts:
        n = len(posts)
        avg_eng = sum(p.get("likesCount", 0) + p.get("commentsCount", 0) for p in posts) / n
        expected_min = followers * 0.005
        if avg_eng < expected_min * 0.3:
            fraud_flags.append("GHOST_FOLLOWERS")
            fraud_score -= 30

    # Sinyal 2: Suspicious growth (eski postlar çok daha yüksek engagement)
    if len(posts) >= 24:
        early_eng = sum(p.get("likesCount",0)+p.get("commentsCount",0) for p in posts[18:24]) / 6
        recent_eng = sum(p.get("likesCount",0)+p.get("commentsCount",0) for p in posts[:6]) / 6
        if early_eng / max(recent_eng, 1) > 3:
            fraud_flags.append("SUSPICIOUS_GROWTH")
            fraud_score -= 25

    # Sinyal 3: Follow/unfollow taktisyeni
    if following > followers * 0.8:
        fraud_flags.append("FOLLOW_UNFOLLOW_TACTIC")
        fraud_score -= 20

    # Sinyal 4: Hashtag spam
    if posts:
        avg_hashtags = sum(len(p.get("hashtags") or []) for p in posts) / len(posts)
        if avg_hashtags > 25:
            fraud_flags.append("HASHTAG_SPAM")
            fraud_score -= 10

    # Sinyal 5: Sentiment fraud risk (Claude'dan gelirse)
    if sentiment_result and sentiment_result.get("fraud_risk", 0) > 0.6:
        fraud_flags.append("SUSPICIOUS_COMMENTS")
        fraud_score -= 15

    fraud_score = max(0, fraud_score)

    if fraud_score >= 80:   return 1.0
    elif fraud_score >= 60: return 0.85
    elif fraud_score >= 40: return 0.65
    else:                   return 0.40
```

---

## 7. sentiment.py — Claude Sonnet 4.6

Günlük 50 cap. Cap dolunca veya API hatasında keyword-based fallback devreye girer.

```python
import os
import json
from datetime import date
from anthropic import Anthropic

_client = None
_daily_count = {"date": None, "count": 0}
DAILY_CAP = 50

def _get_client():
    global _client
    if not _client:
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client

def _within_cap() -> bool:
    today = date.today().isoformat()
    if _daily_count["date"] != today:
        _daily_count["date"] = today
        _daily_count["count"] = 0
    return _daily_count["count"] < DAILY_CAP

def score_sentiment(raw) -> dict:
    posts = raw.get("posts", [])
    comments = []
    for post in posts[:10]:
        for c in (post.get("latestComments") or [])[:3]:
            text = c.get("text", "").strip()
            if text:
                comments.append(text)
    comments = comments[:30]

    if not comments:
        return {"spam_ratio": 0.1, "purchase_intent_ratio": 0.1, "fraud_risk": 0.1, "source": "no_comments"}

    if not _within_cap() or not os.getenv("ANTHROPIC_API_KEY"):
        return _keyword_fallback(comments)

    try:
        client = _get_client()
        prompt = f"""Analyze these {len(comments)} Instagram comments and return a JSON object.

Comments:
{chr(10).join(f'- {c}' for c in comments)}

Return ONLY valid JSON with these keys:
- spam_ratio: float 0-1 (generic/emoji-only/bot-like comments)
- purchase_intent_ratio: float 0-1 (comments showing buying interest, asking prices, product questions)
- fraud_risk: float 0-1 (suspiciously uniform, bot-pattern, or purchased comment indicators)
- summary: string (1 sentence insight)"""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        _daily_count["count"] += 1
        text = response.content[0].text.strip()
        # Extract JSON if wrapped in markdown
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        result["source"] = "claude"
        return result
    except Exception as e:
        print(f"Sentiment API error: {e}")
        return _keyword_fallback(comments)

def _keyword_fallback(comments) -> dict:
    spam_signals = ["nice", "great", "amazing", "follow me", "check my", "👍", "❤️", "🔥"]
    intent_signals = ["price", "where", "buy", "shop", "link", "how much", "available", "order"]
    spam = sum(1 for c in comments if any(s in c.lower() for s in spam_signals)) / len(comments)
    intent = sum(1 for c in comments if any(s in c.lower() for s in intent_signals)) / len(comments)
    return {"spam_ratio": spam, "purchase_intent_ratio": intent, "fraud_risk": spam * 0.5, "source": "fallback"}
```

---

## 8. Etiket Sistemi

| Skor | Etiket | Anlam |
|------|--------|-------|
| 85-100 | Elite | Direkt conversion için ideal |
| 70-84 | High ROI | Güvenli seçim |
| 50-69 | Mid Tier | Brand awareness için uygun |
| 30-49 | Risky | Dikkatli ol |
| 0-29 | Avoid | Önerme |

---

## 9. main.py Değişikliği

`ScoreRequest`'e `category` field'ı eklenir:

```python
class ScoreRequest(BaseModel):
    handle: str
    user_email: str = None
    category: str = "beauty"   # ← YENİ
```

`category` scraper ve niche modülüne iletilir (şimdilik sadece beauty keyword seti aktif, ileride genişletilebilir).

---

## 10. Dashboard Değişiklikleri

`dashboard.html` line 335: duplicate `analyzeHandle` tanımı temizlenir.

**Mevcut (bozuk):**
```js
function analyzeHandle(){...}function analyzeHandle(){...}async function doAnalyze(handle){
```

**Düzeltilmiş:**
```js
function analyzeHandle(){var i=document.getElementById("handle-input");var r=i.value.trim();if(!r)return;doAnalyze(r.startsWith("@")?r:"@"+r);}
async function doAnalyze(handle){
```

**LBL objesi güncellenir** (3'lü → 5'li etiket):
```js
const LBL = {
  elite:  {bg:"var(--green-lo)",  col:"var(--green)",  brd:"var(--green-mid)",  txt:"Elite"},
  high:   {bg:"var(--green-lo)",  col:"var(--green)",  brd:"var(--green-mid)",  txt:"High ROI"},
  mid:    {bg:"var(--amber-lo)",  col:"var(--amber)",  brd:"var(--amber-mid)",  txt:"Mid Tier"},
  risky:  {bg:"var(--red-lo)",    col:"var(--red)",    brd:"var(--red-mid)",    txt:"Risky"},
  avoid:  {bg:"var(--red-lo)",    col:"var(--red)",    brd:"var(--red-mid)",    txt:"Avoid"},
};
```

---

## 11. Değişmeyen Parçalar

- `auth.py` — Supabase cache, analiz kaydı
- `main.py` `/webhook`, `/create-checkout`, `/health` endpoint'leri
- Supabase tablo şeması
- Frontend görsel tasarımı — renkler, layout, CSS (değişmez)
- Apify scraping mantığı

---

## 12. Environment Variables (Railway'e eklenecek)

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 13. Başarı Kriterleri

- [ ] Tüm 7 faktör doğru hesaplanıyor
- [ ] Fraud multiplier negatif sinyallerde skoru düşürüyor
- [ ] Claude API çağrısı çalışıyor, fallback devreye giriyor
- [ ] Günlük cap 50'de duruyor
- [ ] `analyzeHandle` çalışıyor, analiz sonucu dashboard'a yansıyor
- [ ] 5'li etiket sistemi doğru gösteriliyor
- [ ] Mock profiller yeni ham veri yapısına uygun
