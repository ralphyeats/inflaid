# Inflaid — Güncel Proje Durumu

> Bu dosya projeye yeni başlayan bir AI agent veya geliştirici için hazırlanmıştır.
> Tüm eski dokümanların (CONTEXT.md, VETTLY_README.md, PROJECT.md) yerine geçer.
> Tarih: 2026-04-06

---

## Proje Nedir?

**Inflaid**, beauty ve skincare markaların Instagram influencer'larını işbirliği yapmadan önce elemesini sağlayan bir SaaS aracıdır. Kullanıcı bir Instagram handle'ı girer, sistem gerçek veri çeker, 7 faktöre göre 0–100 arası ROI skoru üretir ve yapılandırılmış bir karar verir: hediye mi, ücretli mi, çalışma mı.

**Hedef kullanıcı:** Beauty/skincare ürünü satan marka sahipleri ve pazarlamacılar (özellikle Shopify store owners).

**Dürüst konumlandırma:** Inflaid hızlı bir eleme aracıdır. Kesin ROI oracle'ı değil. En güvenilir aralık: **10K–500K takipçi**.

---

## Deployment

| Katman | Platform | URL |
|--------|----------|-----|
| Frontend | Vercel | https://inflaid.com (domain alındı) |
| Backend | Railway | https://vettly-production-63d5.up.railway.app |
| Veritabanı | Supabase | `qpfjxbsvymlrbeoqwqmr.supabase.co` |
| Auth | Supabase Auth | Email/password |
| Ödeme | Stripe | Canlı mod (LemonSqueezy'ye geçiş planlanıyor) |
| AI | Anthropic Claude Haiku | Outreach mesajı üretimi |

> **Not:** Runtime ve ürün içi metinlerde `Inflaid` kullanılıyor. Railway/Vercel/GitHub tarafındaki bazı teknik adlar ve URL'ler hâlâ `vettly` olarak duruyor.

---

## Dosya Yapısı

```
vettly/
├── index.html              # Landing page (yeniden tasarlandı — light theme)
├── dashboard.html          # Ana uygulama (Discovery / Outreach / Analytics / Campaigns)
├── influencer.html         # Influencer detay sayfası (verdict + ROI forecast dahil)
├── auth.html               # Giriş / kayıt / şifre sıfırlama
├── legal.html              # Terms of Service + Privacy Policy
├── vercel.json             # Vercel yönlendirme
├── railway.toml            # Railway deploy ayarları
├── supabase_migrations.sql # Bekleyen SQL (henüz koşturulmadı — aşağıya bak)
├── PROJECT.md              # Eski proje dokümantasyonu
├── CONTEXT.md              # Eski bağlam dosyası
├── VETTLY_README.md        # Daha eski readme
└── backend/
    ├── main.py             # FastAPI app — tüm endpoint'ler
    ├── scorer.py           # 7 faktörlü skor motoru
    ├── scraper.py          # Apify entegrasyonu (Instagram)
    ├── auth.py             # Supabase client + cache yardımcıları
    ├── verdict.py          # Kural tabanlı karar motoru
    ├── roi.py              # ROI tahmin motoru
    ├── requirements.txt
    ├── factors/
    │   ├── engagement.py
    │   ├── rhythm.py
    │   ├── audience.py
    │   ├── niche.py
    │   ├── authenticity.py
    │   ├── momentum.py
    │   ├── fraud.py
    │   └── sentiment.py
    └── categories/
        └── config.py       # Beauty keyword'leri + faktör ağırlıkları
```

---

## Backend API

### Tüm Endpoint'ler

| Method | Path | Auth | Açıklama |
|--------|------|------|----------|
| POST | `/score` | JWT | Instagram handle analiz et |
| POST | `/outreach` | JWT | AI outreach mesajı üret (Claude Haiku) |
| POST | `/create-checkout` | JWT | Stripe checkout oturumu başlat |
| POST | `/customer-portal` | JWT | Stripe fatura portalı aç |
| POST | `/webhook` | Stripe sig | Stripe ödeme olaylarını işle |
| POST | `/campaign/create` | JWT | Yeni kampanya kaydet |
| GET | `/campaigns` | JWT | Kullanıcının kampanyalarını listele |
| POST | `/campaign/{id}/result` | JWT | Kampanya sonucunu güncelle |
| POST | `/referral/apply` | — | Referral kodu uygula (+5/+2 analiz) |
| GET | `/public/profile/{handle}` | — | Herkese açık önbelleğe alınmış skor |
| GET | `/health` | — | Sağlık kontrolü |

### `/score` Akışı

1. JWT doğrula → email al
2. `users` tablosunda kullanıcıyı bul; yoksa oluştur (free plan, limit: 2)
3. `analyses_used >= analyses_limit` ise 429 döndür
4. Supabase `analyses` cache'ini kontrol et (7 günlük TTL) → varsa döndür
5. Apify'ı çağır → son 20 feed post + takipçi sayısı + engagement
6. 7 faktörlü skor hesapla
7. Verdict motoru çalıştır → kampanya tipi, bütçe, risk, eylem maddeleri
8. ROI tahmin motoru çalıştır → reach, conversion, gelir projeksiyonu
9. Cache'e kaydet, kullanım sayacını artır
10. Tam `ScoreResponse` döndür

### Skor Sistemi

**Formül:** `score = round(weighted_sum × fraud_multiplier)`

| Faktör | Ağırlık | Güvenilirlik |
|--------|---------|--------------|
| Engagement Quality | %30 | Orta |
| Content Rhythm | %20 | Düşük |
| Audience Reliability | %20 | Orta |
| Niche Depth | %15 | İyi |
| Authenticity | %10 | Orta |
| Growth Momentum | %5 | Düşük |
| Fraud Multiplier | modifier | Orta |

**Label'lar:** `elite` (85+) · `high` (70+) · `mid` (50+) · `risky` (30+) · `avoid` (<30)

### Verdict Motoru (verdict.py)

- score < 30 veya authenticity < 30 → `avoid`
- followers < 50K ve score ≥ 50 → `gifted`
- followers ≥ 50K ve score ≥ 70 → `paid`
- diğer score ≥ 50 → `gifted`
- diğer → `avoid`

### Plan Limitleri

| Plan | Analiz/ay |
|------|-----------|
| free | 2 |
| trial | 2 |
| starter | 20 |
| growth | 75 |
| pro | 200 |

### Fiyatlandırma (inflaid.com'da gösterilen)

| Plan | Fiyat | Analiz |
|------|-------|--------|
| Starter | $19/ay | 20 |
| Growth | $49/ay | 75 |
| Pro | $99/ay | 200 |

### Railway Ortam Değişkenleri

```
SUPABASE_URL
SUPABASE_KEY              # service_role key
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_STARTER_PRICE
STRIPE_GROWTH_PRICE
STRIPE_PRO_PRICE
APIFY_API_TOKEN
ANTHROPIC_API_KEY
FRONTEND_URL              # ayarlandi: https://inflaid.com
```

---

## Frontend Sayfaları

### `index.html` — Landing Page
- Light theme: `#F8F7F4` arka plan, Bricolage Grotesque + DM Sans fontlar
- Hero: gradient başlık, animasyonlu dashboard mockup (18s döngü)
- Stats bar, 4 feature section, how it works (3 adım), testimonials, pricing, footer
- "Campaign Tracker" feature bölümünde "COMING SOON" badge'i var — kasıtlı

### `dashboard.html` — Ana Uygulama
- 4 sekme: Discovery · Outreach · Analytics · Campaigns
- Discovery: influencer kartları, skor, verdict, silme butonu, geçmişi temizle
- Outreach: influencer seç → AI outreach mesajı oluştur (Claude Haiku via /outreach)
- Analytics: skor dağılımı, toplam analiz, kategori özeti
- Campaigns: handle + spend tier + outcome formu → localStorage + backend senkronu birlikte çalışıyor; `/campaign/create` ve `/campaigns` aktif, silme işlemi için `DELETE /campaign/{id}` eklendi
- Sidebar: kullanım çubuğu + plan bilgisi + upgrade/yönet butonu

### `influencer.html` — Detay Sayfası
- Üstte büyük verdict banner ("Worth Working With" / "Proceed Carefully" / "Do Not Work With")
- Sol kolon: skor breakdown, faktör çubukları
- Sağ kolon: Decision card (reason + action), ROI Forecast (reach range + AOV input → gelir tahmini), Key Signals grid, Campaign Plan checklist
- Outreach template (AI üretilmiş veya statik)
- Niche skoru < 30 ise uyarı

### `auth.html` — Kimlik Doğrulama
- Giriş / Kayıt sekmeleri
- Şifremi unuttum → sıfırlama emaili → `?mode=update` kurtarma
- `?plan=` parametresiyle yönlendirilince doğrudan `/create-checkout` çağrılır

### `legal.html` — Yasal
- Terms of Service + Privacy Policy sekme layout'u

---

## Supabase Tabloları

### `users`
| Kolon | Tip | Not |
|-------|-----|-----|
| id | uuid | |
| email | text | |
| plan | text | free / starter / growth / pro |
| analyses_used | int4 | |
| analyses_limit | int4 | Plan tarafından belirlenir |
| created_at | timestamp | |

### `analyses`
| Kolon | Tip | Not |
|-------|-----|-----|
| id | uuid | |
| handle | text | |
| score | int4 | |
| label | text | |
| result | jsonb | Tam ScoreResponse JSON |
| created_at | timestamp | 7 günlük TTL |
| user_email | text | Eklendi ve yeni analizlerde doluyor |

### `campaigns`
| Kolon | Tip | Not |
|-------|-----|-----|
| id | uuid | |
| user_email | text | |
| handle | text | |
| spend_tier | text | gifted / under100 / 100-500 / 500-2k / 2k+ |
| outcome | text | worth_it / meh / waste |
| campaign_date | date | |
| orders_range | text | 0 / 1-5 / 5-20 / 20+ (opsiyonel) |
| notes | text | opsiyonel |
| status | text | logged / completed |
| created_at | timestamptz | |

> `campaigns` tablosu Supabase'de oluşturuldu ve aktif olarak kayıt alıyor.

**RLS: tüm tablolarda devre dışı.** Backend service_role key kullanıyor.

---

## Bekleyen Kritik Görevler

### 1. Supabase Migration (TAMAMLANDI)

`supabase_migrations.sql` Supabase üzerinde çalıştırıldı. Sonuç:
- `campaigns` tablosu oluşturuldu
- `analyses.user_email` kolonu eklendi
- yeni analiz ve kampanya kayıtları veritabanına düzgün yazılıyor

### 2. Campaign Tracker Senkronu (KISMEN TAMAMLANDI)

`dashboard.html` artık kampanya kayıtlarını kullanıcı bazlı localStorage anahtarında tutuyor ve backend ile senkronlamaya çalışıyor. Aktif akış:
- `POST /campaign/create` çağrılıyor
- `GET /campaigns` ile uzak kayıtlar çekiliyor
- `DELETE /campaign/{id}` endpoint'i eklendi ve dashboard silme işlemi backend'e de yansıtılıyor
- Unsynced local kayıtlar geçici `local-*` ID ile tutuluyor, backend başarılı dönerse gerçek Supabase ID'si ile değiştiriliyor

Bu akış artık production'da çalışıyor; kampanya kayıtları Supabase'e yazılıyor ve dashboard ile senkron oluyor.

### 3. FRONTEND_URL ve Auth Redirect Ayarlari (TAMAMLANDI)

Railway'de `FRONTEND_URL=https://inflaid.com` olarak ayarlandi. Supabase Auth tarafinda `Site URL` ve gerekli redirect URL'ler de guncellendi.

### 4. OG Image (TAMAMLANDI)

`og-image.png` dosyası repoda mevcut ve `index.html` meta tag'leri bu dosyayı referanslıyor.

### 5. Legal Linkler (TAMAMLANDI)

`index.html` footer'ında `Terms` ve `Privacy` linkleri mevcut. Ayrıca `auth.html` içindeki yasal metin de ayrı `/terms` ve `/privacy` sayfalarına güncellendi.

---

## Güncel Durum

Proje şu an calisan bir launch-ready MVP asamasinda:
- auth ve password reset akisi calisiyor
- influencer analizi veritabanina kaydoluyor
- campaign loglama Supabase'e yaziyor
- Campaign Tracker dashboard ile backend senkronu calisiyor

Kalan isler artik kritik blokaj degil; daha cok growth, polish ve yeni ozellik sinifinda.

---

## Bilinen Sınırlamalar (Önemli Bağlam)

1. **Scraper sadece feed post'ları çekiyor.** Reels ve Stories çekilemiyor. Ağırlıklı olarak Reels paylaşan büyük hesaplar (100K+) ritim faktöründen düşük skor alabilir.

2. **Instagram büyük hesaplarda beğenileri gizliyor.** `likesCount = 0` olduğunda fraud detector sadece yorum eşiği kullanıyor.

3. **Ağırlıklar veri ile doğrulanmadı.** 30/20/20/15/10/5 dağılımı sezgisel. Gerçek kampanya verisi henüz yok.

4. **ROI tahminleri heuristik.** Gelir = conversion × AOV ($45 varsayılan). Gerçek veriyle kalibre edilmedi.

5. **500K+ hesaplar güvenilmez.** Makro/mega influencer'larda engagement doğal olarak düşer.

---

## Gelecek / Growth (Henüz Yapılmadı)

- **LemonSqueezy geçişi** — KYC onayı bekleniyor. Onaylanınca `/create-checkout`, `/customer-portal`, `/webhook` endpoint'leri yeniden yazılacak. Yani Stripe yerine yeni ödeme sağlayıcısına taşınacak.
- **ROI kalibrasyon** — 50+ kampanya verisi birikince gerçek ROAS verisini skora besle. Yani skor formülü gerçek sonuçlara göre daha doğru hale getirilecek.
- **Email hatırlatma** — Kampanya kaydından 7 gün sonra "nasıl gitti?" emaili. Yani kullanıcıdan kampanya sonucu toplamak için otomatik follow-up gönderilecek.
- **Toplu analiz** — Pro plan özelliği (UI yok, backend yok). Yani tek tek handle girmek yerine aynı anda birden fazla influencer analiz edilebilecek.
- **CSV export** — Pro plan özelliği (UI yok, backend yok). Yani kullanıcı analiz veya kampanya verilerini Excel/Sheets'e aktarmak için dışa aktarabilecek.
- **Team seats** — Pro plan özelliği (implement edilmedi). Yani aynı hesap altında birden fazla ekip üyesi erişebilecek.
- **Fashion / food / fitness kategorileri** — `categories/config.py`'de placeholder var, sadece keyword lazım. Yani beauty dışındaki sektörlere genişleme altyapısı kısmen hazır.
- **Admin panel** — Başarısız scrape'ler ve kullanım istatistikleri için görünürlük yok. Yani içeride sistem sağlığını ve kullanıcı aktivitesini izlemek için yönetim ekranı eksik.
- **Gerçek testimonials** — Şu an landing page'deki testimonials mock data. Yani müşteri geri bildirimi bölümü gerçek kullanıcı yorumlarıyla değiştirilmeli.
- **Infrastructure rename** — Runtime içindeki ana marka izleri temizlendi; ancak GitHub repo, Vercel project, Railway project ve backend URL'si hâlâ "vettly" adını taşıyor. Yani dış servis isimlerinde eski marka izleri duruyor.

---

## Referral Sistemi (Mevcut)

Backend'de `/referral/apply` endpoint'i var. `btoa(referrer_email)` formatında kod üretilip `?ref=` query param'ı ile yeni kullanıcıya iletilir. Bonus: referrer +5 analiz, yeni kullanıcı +2 analiz. Frontend'de referral link oluşturma ve gösterme UI'ı eklenmemiş.

---

## Hızlı Başvuru

**Supabase Project ID:** `qpfjxbsvymlrbeoqwqmr`

**GitHub:** `https://github.com/ralphyeats/vettly`

**Stripe plan price ID env variable isimleri:**
- `STRIPE_STARTER_PRICE` → $19/ay
- `STRIPE_GROWTH_PRICE` → $49/ay
- `STRIPE_PRO_PRICE` → $99/ay
