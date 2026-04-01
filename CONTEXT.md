# Vettly — Proje Bağlamı ve Mevcut Durum

> Bu dosya, projeye yeni katılan bir yapay zeka aracının veya geliştiricinin hızla bağlamı kavraması için hazırlanmıştır.

---

## Proje Nedir?

**Vettly**, beauty ürünleri satan markaların Instagram influencer'larını analiz edip ROI potansiyelini skorlamasını sağlayan bir SaaS platformudur. Kullanıcı bir Instagram handle'ı girer, sistem o hesabın gerçek verilerini çekip 0–100 arası bir ROI skoru üretir.

**Hedef kullanıcı:** Beauty/skincare/makeup ürünü satan marka sahipleri ve pazarlamacılar.

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
├── index.html          # Landing page
├── auth.html           # Login / signup
├── dashboard.html      # Ana uygulama (Discovery, Outreach, Analytics tabları)
├── influencer.html     # Influencer detay sayfası
├── i18n.js             # (kullanılmıyor şu an)
├── vercel.json         # Vercel yönlendirme ayarları
├── railway.toml        # Railway deploy ayarları
└── backend/
    ├── main.py         # FastAPI app, endpoint'ler, Pydantic modeller
    ├── scorer.py       # 7 faktörlü skor hesaplama motoru
    ├── scraper.py      # Apify entegrasyonu (Instagram verisi çekme)
    ├── auth.py         # Supabase client, cache (analyses tablosu), usage tracking
    ├── requirements.txt
    ├── factors/
    │   ├── engagement.py   # Engagement rate + kalite bonusu (ağırlık: %30)
    │   ├── rhythm.py       # Yayın sıklığı ve tutarlılığı (ağırlık: %20)
    │   ├── audience.py     # Takipçi kalitesi ve engagement fulfillment (ağırlık: %20)
    │   ├── niche.py        # Beauty keyword coverage/depth/recency (ağırlık: %15)
    │   ├── authenticity.py # Sponsorlu içerik, bot sinyalleri (ağırlık: %10)
    │   ├── momentum.py     # Engagement büyüme/düşüş trendi (ağırlık: %5)
    │   ├── fraud.py        # Fraud multiplier (0.4–1.0 arasında final skoru ezer)
    │   └── sentiment.py    # Claude AI ile yorum analizi (purchase intent, spam, fraud risk)
    └── categories/
        └── __init__.py     # (boş — category-ready altyapı için hazırlandı, henüz config.py yok)
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

**Response:**
```json
{
  "handle": "@kullaniciadi",
  "score": 78,
  "label": "high",
  "breakdown": [
    { "key": "engagement", "label": "Engagement Quality", "description": "...", "value": 85, "weight": 0.30, "contribution": 25.5 },
    ...6 faktör...
  ],
  "insight": "Engagement Quality is the strongest signal at 85/100. Strong ROI potential. Score 78/100.",
  "mock": false
}
```

**Labellar:** `elite` (85+), `high` (70+), `mid` (50+), `risky` (30+), `avoid` (<30)

**Limitler:**
- Free plan: 2 analiz
- Pro plan: 50 analiz ($9/ay — Stripe)
- Growth plan: sınırsız ($49/ay — Stripe)
- 429 döndüğünde `detail: "limit_reached:free"` formatında hata gelir

**Cache:** Her analiz Supabase `analyses` tablosuna 7 günlük TTL ile kaydedilir. Aynı handle tekrar sorgulanırsa cache'den döner (kullanım sayısını yine artırır).

### `POST /create-checkout`
Stripe checkout session oluşturur.

### `POST /webhook`
Stripe webhook — ödeme tamamlandığında kullanıcı planını günceller.

### `GET /health`
Sağlık kontrolü.

---

## Scoring Algoritması

```
final_score = round(weighted_sum × fraud_multiplier)

weighted_sum = engagement×0.30 + rhythm×0.20 + audience×0.20
             + niche×0.15 + authenticity×0.10 + momentum×0.05
```

Fraud multiplier: 1.0 (temiz) → 0.85 → 0.65 → 0.40 (ağır fraud)

Sentiment analizi (Claude Sonnet 4.6 ile): Yorumlardan purchase intent, spam ratio ve fraud risk çıkarır. Fraud multiplier hesaplamasında kullanılır. Günlük 50 Claude çağrısı limiti var, üstünde keyword fallback'e düşer.

**Veri kaynağı:** Apify `apify/instagram-profile-scraper` — her analizde son ~12 post çekilir.

---

## Frontend Özeti

### `dashboard.html` — Tek sayfalık uygulama (3 tab)

**Discovery tab:**
- Instagram handle input + "Analyze →" butonu
- Kategori filtresi (All / Skincare / Makeup / Haircare / Fragrance)
- Platform filtresi (All / Instagram / TikTok)
- Analiz edilen influencer'ların kartları (grid)
- Kartlara tıklayınca `influencer.html?handle=@...` açılır

**Outreach tab:**
- Analiz edilen her influencer için otomatik oluşturulan outreach e-posta şablonu
- "Copy to clipboard" ve "Mark as sent" butonları
- Status: pending / sent / replied (localStorage'a kaydedilir)

**Analytics tab:**
- Total analyzed, High ROI count, Outreach sent, Avg ROI score — gerçek verilerden hesaplanır
- Score distribution bar'ları (High/Mid/Risk yüzdeleri)
- Son 7 analizin skor bar chart'ı
- Recent analyses listesi

**Önemli frontend detayları:**
- Supabase Auth ile login kontrolü (`auth.html`'e redirect)
- Tüm analiz geçmişi `localStorage`'da `vettly_history_<email>` key'i ile saklanır (kullanıcıya özel)
- Sayfa yenilenince geçmiş kaybolmaz — auth resolve olunca localStorage yüklenir
- Mock data tamamen kaldırıldı; sadece gerçek API sonuçları gösterilir

### `influencer.html` — Influencer detay sayfası
- `?handle=@...` parametresiyle açılır
- Önce localStorage cache'den okur (ekstra API çağrısı yapmaz)
- Cache'de yoksa backend'e fresh çağrı yapar
- Sol kolon: profil bilgileri, ROI skoru, "Best for" listesi
- Sağ kolon: "Why this score" insight, faktör breakdown, outreach template

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

## Şu An Yapılmakta Olan İş

**Category-ready architecture refactor:**

Scoring algoritması şu an tamamen beauty'e hardcode edilmiş durumda:
- `factors/niche.py` içinde `BEAUTY_KEYWORDS` sabit listesi var
- `scorer.py` içinde ağırlıklar sabit (`WEIGHTS = {"engagement": 0.30, ...}`)

Kullanıcı şu an beauty odaklı kalmak istiyor ama ileride giyim/food/fitness gibi yeni kategoriler eklenebilmesi için altyapıyı hazır hale getireceğiz. **UI değişmeyecek.**

**Yapılacak değişiklikler:**
1. `backend/categories/config.py` oluştur — category registry (keywords + weights per category)
2. `backend/factors/niche.py` güncelle — `BEAUTY_KEYWORDS` hardcode yerine config'den al
3. `backend/scorer.py` güncelle — `WEIGHTS` hardcode yerine config'den al
4. Sub-category map ekle: skincare/makeup/haircare/fragrance → beauty

**Değişmeyecek dosyalar:** `main.py`, tüm diğer factor dosyaları, frontend

---

## Geçmiş Commit Özeti

```
bbca616  Fix analytics real stats, influencer detail from cache, category filtering
2c03917  Remove mock data, persist analysis history to localStorage
aa74534  fix: treat analyses_limit=0 as no-limit
fd843b1  fix: replace undefined selectedCategory with curCat
75a1e31  fix: remove leftover bypass_cache reference causing 500
78eaaec  fix: use Optional[str] for user_email (Pydantic v2)
9ed68b1  fix: adapt momentum to Apify 12-post limit
58df1e0  fix: handle hidden likes (likesCount=0/null)
3a30ca*  fix: resolve 4 scoring reliability issues
49d3beb  feat: block private accounts from scoring
d616dbe  feat: complete Phase 1 scoring engine rewrite
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

## Bilinen Sınırlamalar / İyileştirilecek Noktalar

- TikTok desteği yok (scraper sadece Instagram çekiyor)
- `followers` değeri API response'unda `"—"` dönüyor (Apify'dan gelmiyor)
- Sentiment analizi günlük 50 çağrı sınırı var — yoğun kullanımda keyword fallback'e düşer
- `mock: true` flag'i bazen yanlış — scraper bazen mock data dönüyor (Apify başarısız olduğunda)
