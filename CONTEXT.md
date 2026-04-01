# Vettly — Proje Bağlamı ve Mevcut Durum

> Bu dosya, projeye yeni katılan bir yapay zeka aracının veya geliştiricinin hızla bağlamı kavraması için hazırlanmıştır.

---

## Proje Nedir?

**Vettly**, beauty ürünleri satan markaların Instagram influencer'larını analiz edip ROI potansiyelini skorlamasını sağlayan bir SaaS platformudur. Kullanıcı bir Instagram handle'ı girer, sistem o hesabın gerçek verilerini çekip 0–100 arası bir ROI skoru üretir.

**Hedef kullanıcı:** Beauty/skincare/makeup ürünü satan marka sahipleri ve pazarlamacılar (özellikle Shopify store owners).

---

## Deployment

| Katman    | Platform | URL |
|-----------|----------|-----|
| Frontend  | Vercel   | https://vettly-eight.vercel.app |
| Backend   | Railway  | https://vettly-production-63d5.up.railway.app |
| Veritabanı| Supabase | `qpfjxbsvymlrbeoqwqmr.supabase.co` |
| Auth      | Supabase Auth | Email/password |
| Ödeme     | Stripe   | Subscription tabanlı |

---

## Dosya Yapısı

```
vettly/
├── index.html          # Landing page (YENİDEN TASARLANDI)
├── auth.html           # Login / signup
├── dashboard.html      # Ana uygulama (Discovery, Outreach, Analytics tabları)
├── influencer.html     # Influencer detay sayfası (GÜNCELLENMESİ GEREKIYOR — aşağıya bak)
├── CONTEXT.md          # Bu dosya
├── vercel.json         # Vercel yönlendirme ayarları
├── railway.toml        # Railway deploy ayarları
└── backend/
    ├── main.py         # FastAPI app, endpoint'ler, Pydantic modeller
    ├── scorer.py       # 7 faktörlü skor hesaplama motoru
    ├── scraper.py      # Apify entegrasyonu (Instagram verisi çekme)
    ├── auth.py         # Supabase client, cache (analyses tablosu), usage tracking
    ├── verdict.py      # YENİ — Karar motoru (gifted/paid/avoid + reason + action)
    ├── roi.py          # YENİ — ROI tahmin motoru (reach/conversion estimates)
    ├── requirements.txt
    ├── factors/
    │   ├── engagement.py
    │   ├── rhythm.py
    │   ├── audience.py
    │   ├── niche.py        # GÜNCELLENDİ — artık config'den keyword alıyor
    │   ├── authenticity.py
    │   ├── momentum.py
    │   ├── fraud.py
    │   └── sentiment.py
    └── categories/
        ├── __init__.py
        └── config.py       # YENİ — Category registry (keywords + weights per category)
```

---

## Backend API

### `POST /score`
Ana endpoint. Instagram handle'ı alır, skoru döner.

**Request:**
```json
{
  "handle": "@kullaniciadi",
  "user_email": "user@example.com",
  "category": "beauty"
}
```

**Response (güncel — yeni alanlar eklendi):**
```json
{
  "handle": "@kullaniciadi",
  "score": 78,
  "label": "high",
  "followers": 15100,
  "name": "Sophia Reeves",
  "breakdown": [
    { "key": "engagement", "label": "Engagement Quality", "description": "...", "value": 85, "weight": 0.30, "contribution": 25.5 },
    ...6 faktör...
  ],
  "insight": "Engagement Quality is the strongest signal at 85/100. Strong ROI potential. Score 78/100.",
  "verdict": {
    "verdict": "gifted",
    "verdict_label": "Gifted Campaign",
    "reason": "Micro-influencer with strong engagement and high niche alignment...",
    "action": "Send 1–2 products. Request one Reel + two Stories. No cash fee.",
    "campaign_type": "Reels",
    "budget_range": "$0 cash · product cost only (~$30–80)",
    "risk": "Low"
  },
  "roi_estimate": {
    "estimated_reach_low": 840,
    "estimated_reach_high": 1560,
    "estimated_conversions_low": 4,
    "estimated_conversions_high": 12,
    "confidence": "medium",
    "note": "Based on 12 recent posts and industry benchmarks. Actual results vary."
  },
  "mock": false
}
```

**Labellar:** `elite` (85+), `high` (70+), `mid` (50+), `risky` (30+), `avoid` (<30)

**Verdict değerleri:** `gifted`, `paid`, `avoid`

**Limitler:**
- Free plan: 2 analiz
- Pro plan: 50 analiz ($9/ay — Stripe)
- Growth plan: sınırsız ($49/ay — Stripe)
- 429 döndüğünde `detail: "limit_reached:free"` formatında hata gelir

**Cache:** Her analiz Supabase `analyses` tablosuna 7 günlük TTL ile kaydedilir.

---

## Scoring Algoritması

```
final_score = round(weighted_sum × fraud_multiplier)

weighted_sum = engagement×0.30 + rhythm×0.20 + audience×0.20
             + niche×0.15 + authenticity×0.10 + momentum×0.05
```

Fraud multiplier: 1.0 (temiz) → 0.85 → 0.65 → 0.40 (ağır fraud)

**Verdict motoru (verdict.py):** Skor + follower sayısı + faktör skorları → karar
- score < 30 veya authenticity < 30 → `avoid`
- followers < 50K ve score ≥ 50 → `gifted`
- followers ≥ 50K ve score ≥ 70 → `paid`
- diğer score ≥ 50 → `gifted`
- diğer → `avoid`

**ROI tahmin motoru (roi.py):** Heuristik model
- Ham engagement rate hesabı (raw likesCount + commentsCount / followers)
- Reel reach = followers × min(eng_rate × 15, 0.9)
- Story reach = followers × 0.08
- CTR = (niche_score/100) × 0.025 + 0.005
- CVR = ((auth_score + engagement_score) / 200) × 0.02 + 0.005
- Frontend bu değerleri kullanıcının AOV'si ile çarparak revenue tahmini gösterir

---

## Frontend Özeti

### `dashboard.html` — Tek sayfalık uygulama (3 tab)
- Mock data tamamen kaldırıldı
- Tüm analiz geçmişi `localStorage`'da `vettly_history_<email>` key'i ile saklanır
- `renderAnalytics()` gerçek verilerden hesaplanıyor
- Analiz edilen influencer'lar karta tıklanınca `influencer.html?handle=@...` açılır

### `influencer.html` — Influencer detay sayfası — ⚠️ YAPILMASI GEREKEN İŞ VAR

**Mevcut durum:**
- Sayfada hâlâ eski hardcoded `DATA` array'i var (8 mock influencer) — kaldırılmadı
- `followers` ve `name` alanları API'dan geliyor ama eski kod `"—"` gösteriyor
- `verdict` ve `roi_estimate` alanları API'dan geliyor ama UI'da hiç gösterilmiyor
- Outreach template hâlâ basit string interpolation — Claude ile kişiselleştirilmedi

**Yapılması gereken (devam eden iş):**
1. Hardcoded `DATA` array'ini kaldır
2. Sol kolona **Verdict card** ekle: `verdict_label`, `risk`, `budget_range`, `campaign_type`
3. Sağ kolona en üste **Decision card** ekle: `reason` + `action` highlighted
4. Sağ kolona **ROI Forecast card** ekle: reach range + conversions range + AOV input → revenue projection
5. `followers` ve `name`'i API response'undan düzgün oku
6. Outreach template'i Claude ile kişiselleştir (bu sonraya bırakılabilir)

**Tasarım yönü:**
- Mevcut dark theme korunacak (Syne + Geist fontları, dark blue palette)
- Verdict card: sol kolonda score-card'ın altına, "Best for" yerine geçecek
- Decision card: sağ kolonda en üstte, belirgin action highlight ile
- ROI Forecast card: decision card'ın altında, AOV input + revenue range

### `index.html` — Landing page (YENİDEN TASARLANDI)
- Light theme: `#F8F7F4` background
- Bricolage Grotesque + DM Sans fontları
- Gradient hero text, browser mockup, floating chips
- Scroll reveal (IntersectionObserver)
- Score card count-up animasyonu
- Pricing: Free / Pro ($9) / Growth ($49)

---

## Supabase Tabloları

### `users`
| Kolon | Tip | Açıklama |
|-------|-----|----------|
| email | text (PK) | Kullanıcı email'i |
| plan | text | `free` / `pro` / `growth` |
| analyses_used | int | Toplam kullanılan analiz sayısı |
| analyses_limit | int | Plan limiti (2 / 50 / 999999) |

### `analyses`
| Kolon | Tip | Açıklama |
|-------|-----|----------|
| handle | text | Instagram handle |
| score | int | ROI skoru |
| label | text | Label |
| result | jsonb | Tam ScoreResponse JSON |
| created_at | timestamp | Cache TTL için kullanılır (7 gün) |

---

## Bu Oturumda Yapılanlar (Kronolojik)

### 1. Category-ready backend refactor
- `backend/categories/config.py` oluşturuldu — CATEGORY_CONFIG registry
- `backend/categories/__init__.py` oluşturuldu (boş, Python package için)
- `SUBCATEGORY_MAP`: skincare/makeup/haircare/fragrance → beauty
- `backend/factors/niche.py` güncellendi — BEAUTY_KEYWORDS hardcode yerine config'den alıyor
- `backend/scorer.py` güncellendi — WEIGHTS hardcode yerine config'den alıyor

### 2. Landing page redesign (index.html)
- Komple yeniden yazıldı
- Light warm theme, Bricolage Grotesque + DM Sans
- Hero gradient text, animated browser mockup, floating chips
- 3 feature split sections, pricing section, dark CTA, footer
- Scroll reveal + score card count-up animasyonu

### 3. CONTEXT.md oluşturuldu
- Projeye yeni başlayan AI aracı/geliştirici için tam bağlam dosyası

### 4. Verdict + ROI backend layer (EN SON — push edildi)
- `backend/verdict.py` oluşturuldu — rule-based karar motoru
- `backend/roi.py` oluşturuldu — heuristik ROI tahmin motoru
- `backend/scorer.py` güncellendi — verdict ve roi_estimate ScoreResult'a eklendi
- `backend/main.py` güncellendi:
  - `VerdictOut` Pydantic modeli eklendi
  - `RoiEstimateOut` Pydantic modeli eklendi
  - `ScoreResponse`'a `followers`, `name`, `verdict`, `roi_estimate` eklendi
- **Railway'e push edildi, deploy bekliyor**

---

## Şu An Yapılmakta Olan İş

**`influencer.html` redesign** — YENİ BACKEND VERİLERİNİ GÖSTERECEK ŞEKİLDE

Bu iş yarım kaldı. Yukarıdaki "Yapılması gereken" listesine bak.

Yapılacak adımlar:
1. Hardcoded DATA array'ini kaldır
2. Sol kolona verdict summary card ekle
3. Sağ kolona decision card + ROI forecast card ekle (AOV input dahil)
4. followers/name'i doğru oku
5. Render fonksiyonunu yeni API field'larına göre güncelle

---

## Git Commit Özeti (Bu Oturum)

```
e8b7bba  feat: add verdict + ROI estimation layer to score response
1d84048  feat: category-ready backend + redesigned landing page
bbca616  Fix analytics real stats, influencer detail from cache, category filtering
```

---

## Ortam Değişkenleri (Railway'de tanımlı)

```
APIFY_TOKEN          — Instagram scraper için
ANTHROPIC_API_KEY    — Sentiment analizi için (Claude Sonnet 4.6)
SUPABASE_URL         — Supabase proje URL'i
SUPABASE_KEY         — Supabase service key
STRIPE_SECRET_KEY    — Stripe API key
STRIPE_WEBHOOK_SECRET— Stripe webhook doğrulama
STRIPE_PRO_PRICE     — Stripe pro plan price ID
STRIPE_GROWTH_PRICE  — Stripe growth plan price ID
```

---

## Bilinen Sınırlamalar

- TikTok desteği yok (scraper sadece Instagram çekiyor — planlanmıyor şimdilik)
- Sentiment analizi günlük 50 çağrı sınırı var — yoğun kullanımda keyword fallback'e düşer
- ROI tahmini heuristik — gerçek kampanya verisiyle kalibre edilmedi
- Supabase cache'deki eski analizler verdict/roi_estimate içermiyor (yeni analizlerde gelir)
