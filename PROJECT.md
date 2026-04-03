# Inflaid — Project Overview

**Inflaid** is a SaaS tool that helps beauty & skincare brands vet Instagram influencers before spending budget on collaborations. A brand enters any Instagram handle, and the system pulls live data, scores the account across 7 ROI factors, and outputs a structured decision: verdict, campaign type, budget estimate, ROI forecast, and a personalized outreach message.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Static HTML/CSS/JS — deployed on **Vercel** |
| Backend | **FastAPI** (Python) — deployed on **Railway** |
| Database / Auth | **Supabase** (PostgreSQL + Auth) |
| Data Source | **Apify** (Instagram scraper) |
| Payments | **Stripe** (switching to LemonSqueezy — KYC pending) |
| AI Outreach | **Anthropic Claude Haiku** |
| Version Control | GitHub (`ralphyeats/vettly`) |

---

## Repository Structure

```
vettly/
├── index.html          # Landing page
├── dashboard.html      # Main app — analysis + history
├── influencer.html     # Influencer detail page
├── auth.html           # Login / signup / password reset
├── legal.html          # Terms of Service + Privacy Policy
├── vercel.json         # Vercel routing config
├── railway.toml        # Railway deploy config
└── backend/
    ├── main.py         # FastAPI app — all endpoints
    ├── auth.py         # Supabase client + cache helpers
    ├── scraper.py      # Apify Instagram scraper
    ├── scorer.py       # 7-factor scoring engine
    ├── verdict.py      # Rule-based decision engine
    ├── roi.py          # ROI estimation engine
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
        └── config.py   # Beauty keywords + factor weights
```

---

## Backend

### Framework
FastAPI on Python. Deployed on Railway. Single `main.py` entry point.

### Authentication
All protected endpoints require `Authorization: Bearer <token>` header. The token is a Supabase JWT from the logged-in user's session. Backend verifies it via `sb.auth.get_user(token)` — cryptographic verification, not just email trust.

```python
def verify_token(authorization: str) -> str:
    # Returns verified email or raises 401
```

### Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/score` | ✅ Required | Analyze an Instagram handle |
| POST | `/create-checkout` | ✅ Required | Create Stripe checkout session |
| POST | `/customer-portal` | ✅ Required | Open Stripe billing portal |
| POST | `/outreach` | ✅ Required | Generate AI outreach message (Claude Haiku) |
| POST | `/webhook` | Stripe sig | Handle Stripe payment events |
| GET | `/health` | ❌ | Health check |

### `/score` Flow
1. Verify JWT → get email
2. Look up user in Supabase `users` table — create on first use (`plan: free`, `analyses_limit: 2`)
3. Check `analyses_used >= analyses_limit` → 429 if over limit
4. Check Supabase `analyses` cache (7-day TTL) — return cached result if found (still increments usage)
5. Call Apify scraper → fetch last 20 posts, follower count, engagement
6. Run 7-factor scorer → compute final score
7. Run verdict engine → campaign type, budget, risk, action items
8. Run ROI estimator → reach, conversion, revenue projection
9. Save to Supabase cache, increment usage counter
10. Return full `ScoreResponse`

### Scoring System
**Formula:** `score = round(weighted_sum × fraud_multiplier)`

| Factor | Weight | What it measures |
|---|---|---|
| Engagement Quality | 30% | Like/comment ratio vs follower count, comment depth |
| Content Rhythm | 20% | Posting consistency, frequency |
| Audience Reliability | 20% | Follower/following ratio, engagement consistency |
| Niche Depth | 15% | Beauty keyword coverage in captions + hashtags |
| Authenticity | 10% | Comment authenticity signals, spam detection |
| Growth Momentum | 5% | Recent follower trend |
| Fraud Multiplier | modifier | Ghost follower signals, engagement spikes — reduces final score |

**Labels:** `elite` (85+) · `high` (70+) · `mid` (50+) · `risky` (30+) · `avoid` (<30)

### Niche Keywords
`categories/config.py` contains 80+ beauty keywords in English, Turkish, Russian, French, and Spanish. Covers product types (serum, fondoten, тушь, maquillaje) and content formats (grwm, makyaj tutorial, routine beaute). Niche score measures what % of the influencer's posts contain these keywords.

The system is currently **beauty-only**. The config file has placeholder entries for `fashion` and `food` categories — adding a new category only requires adding an entry to `CATEGORY_CONFIG`.

### Verdict Engine (`verdict.py`)
Rule-based heuristics — no ML. Takes final score, follower count, and individual factor scores. Outputs:
- `verdict_label`: e.g. "Gifted Campaign — Stories"
- `campaign_type`: Reels / Stories / UGC / Mixed
- `action`: What to do (3-week checklist items)
- `budget_range`: Cash estimate
- `risk`: Low / Medium / High
- `warning_flags`: List of specific red flags

### ROI Estimator (`roi.py`)
Heuristic-based. Takes follower count, engagement rate, niche score, authenticity score. Outputs:
- Estimated reach (low/high)
- Estimated conversions (low/high)
- Revenue estimate (multiplied by brand's AOV — default $45 for beauty)
- Confidence level (low/medium/high)
- Explanation text

### AI Outreach (`/outreach`)
Calls Claude Haiku with a structured prompt including influencer name, niche, follower count, score, and collab type. Tone adapts based on score: ≥70 → confident/paid collab tone, <70 → low-pressure/gifted tone. Falls back to static template if API fails.

### Plan Limits

| Plan | Analyses/month |
|---|---|
| free | 2 |
| trial | 2 |
| starter | 20 |
| growth | 75 |
| pro | 200 |

Usage tracked in Supabase `users` table. Limits enforced server-side on every `/score` call.

### Environment Variables (Railway)

```
SUPABASE_URL
SUPABASE_KEY              # service_role key (bypasses RLS)
STRIPE_SECRET_KEY         # sk_live_xxx
STRIPE_WEBHOOK_SECRET     # whsec_xxx
STRIPE_STARTER_PRICE      # price_xxx
STRIPE_GROWTH_PRICE       # price_xxx
STRIPE_PRO_PRICE          # price_xxx
APIFY_API_TOKEN
ANTHROPIC_API_KEY
FRONTEND_URL              # https://inflaid.io (update after domain)
```

---

## Frontend

Three app pages (dashboard, influencer detail, auth) + one landing page. All static HTML/CSS/JS, no framework. Deployed on Vercel.

### Pages

#### `index.html` — Landing Page
- Hero with animated dashboard mockup (CSS-only, 18s loop)
- Shows full product flow: search → card result → influencer detail → outreach
- Features section, testimonials, pricing grid
- Targeted at beauty & skincare brands — explicit in all copy

#### `dashboard.html` — Main App
- Sidebar navigation (Discovery / Outreach / Analytics)
- Analyze input: enter any Instagram handle → calls `/score`
- Results grid: influencer cards with score, verdict badge, ROI tier
- Outreach tab: select influencer → generate AI outreach message
- Analytics tab: charts, totals, sent/replied tracking
- Usage bar + upgrade button in sidebar
- History: loads from localStorage first, then syncs from Supabase (cross-device)

#### `influencer.html` — Detail View
- Full decision output for one influencer
- Decision bar: verdict label, bullet-point action items, Budget/Risk/Est. Sales pills
- ROI Forecast: spend vs return, confidence level, adjustable AOV
- Key Signals: 2×2 grid (Biggest Strength, Biggest Risk, Frequency, Authenticity)
- Campaign Plan: 3-week execution checklist
- Score breakdown: factor-by-factor bars
- Outreach template: static or AI-generated (Claude)
- Niche warning: shown if niche score < 30 (non-beauty account)

#### `auth.html` — Auth
- Sign in / Sign up tabs
- Forgot password → `resetPasswordForEmail()` → email with redirect to `?mode=update`
- Password recovery form shown via `PASSWORD_RECOVERY` Supabase auth event
- After login with `?plan=` param → immediately calls `/create-checkout`

#### `legal.html` — Legal
- Tabbed: Terms of Service + Privacy Policy
- Both reference Inflaid brand, hello@inflaid.io contact

### Auth Flow
Supabase JS SDK. Session stored in browser. All API calls include `Authorization: Bearer <access_token>` header. 401 responses redirect to `/auth.html`.

### Supabase Tables

**`users`**
| Column | Type | Notes |
|---|---|---|
| id | uuid | |
| email | text | |
| plan | text | free / starter / growth / pro |
| analyses_used | int4 | Incremented on each analysis |
| analyses_limit | int4 | Set by plan (0 = unlimited) |
| created_at | timestamp | |

**`analyses`**
| Column | Type | Notes |
|---|---|---|
| id | uuid | |
| handle | text | Instagram handle |
| score | int4 | |
| label | text | elite/high/mid/risky/avoid |
| result | jsonb | Full ScoreResponse JSON |
| created_at | timestamp | Cache TTL: 7 days |

RLS is currently **disabled** on both tables — backend uses service_role key which bypasses RLS anyway. Frontend never queries these tables directly.

---

## Payments

Currently **Stripe** (test mode). Switching to **LemonSqueezy** (KYC review pending) because LemonSqueezy is a Merchant of Record — no registered company required.

**Stripe flow (current):**
1. User clicks upgrade → frontend calls `POST /create-checkout` with plan name + JWT
2. Backend verifies token, creates Stripe Checkout Session with `metadata: {plan}`
3. User pays → Stripe fires `checkout.session.completed` webhook
4. Backend reads `metadata.plan`, updates `users` table: plan + analyses_limit
5. Redirect to `/dashboard.html?upgraded=1`

**LemonSqueezy migration:** Will replace `/create-checkout`, `/customer-portal`, and `/webhook` endpoints. Frontend calls stay identical (same URL redirect pattern).

---

## Known Limitations / To-Do

- **LemonSqueezy integration** — blocked on KYC approval
- **Mobile CSS** — recently fixed across all pages, may need additional polish
- **History sync** — done (Supabase), but `analyses` table has no `user_email` column yet — currently syncs all public analyses, not per-user
- **Domain** — still on `vettly-eight.vercel.app` / `vettly-production-63d5.up.railway.app`. After domain purchase: update `FRONTEND_URL` in Railway, update Supabase Auth URLs
- **Rename** — all user-facing copy updated to "Inflaid", but repo/Vercel/Railway project names still say "vettly"
- **Only beauty category** — fashion, food, fitness not yet supported
- **No admin panel** — no way to see failed scrapes or usage stats from a UI

---

## Deployment

**Frontend (Vercel):**
- Auto-deploys on every push to `main`
- No build step — static files served directly
- `vercel.json` routes all paths to their respective HTML files

**Backend (Railway):**
- Auto-deploys on every push to `main`
- `railway.toml` defines start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Free tier: ~$5/month credit. Current usage ~$0.54/month (very low traffic)
- If credits run out: migrate to Render.com (free tier, no credit card needed — ~30s cold start)
