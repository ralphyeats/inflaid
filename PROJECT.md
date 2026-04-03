# Inflaid — Project Overview

**Inflaid** is a SaaS tool that helps beauty & skincare brands vet Instagram influencers before spending budget on collaborations. A brand enters any Instagram handle, the system pulls live data, scores the account across 7 ROI factors, and outputs a structured decision: verdict, campaign type, budget estimate, ROI forecast, and a personalized outreach message.

**Honest positioning:** Inflaid is a fast screening tool — it helps brands eliminate bad choices quickly and understand a profile's basics. It is NOT a precise ROI oracle. Scores indicate direction, not exact value. Best accuracy range: **10K–500K followers**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Static HTML/CSS/JS — deployed on **Vercel** |
| Backend | **FastAPI** (Python) — deployed on **Railway** |
| Database / Auth | **Supabase** (PostgreSQL + Auth) |
| Data Source | **Apify** (Instagram scraper — feed posts only) |
| Payments | **Stripe** (switching to LemonSqueezy — KYC pending) |
| AI Outreach | **Anthropic Claude Haiku** |
| Version Control | GitHub (`ralphyeats/vettly`) |

---

## Repository Structure

```
vettly/
├── index.html          # Landing page
├── dashboard.html      # Main app — analysis + history + campaigns
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

### Authentication
All protected endpoints require `Authorization: Bearer <token>` header. Token is a Supabase JWT verified via `sb.auth.get_user(token)`.

### Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/score` | ✅ | Analyze an Instagram handle |
| POST | `/outreach` | ✅ | Generate AI outreach message (Claude Haiku) |
| POST | `/create-checkout` | ✅ | Create Stripe checkout session |
| POST | `/customer-portal` | ✅ | Open Stripe billing portal |
| POST | `/webhook` | Stripe sig | Handle Stripe payment events |
| POST | `/campaign/create` | ✅ | Log a new campaign (spend tier + outcome) |
| GET | `/campaigns` | ✅ | List user's logged campaigns |
| POST | `/campaign/{id}/result` | ✅ | Update campaign with orders/notes |
| POST | `/referral/apply` | ❌ | Apply referral code (+5/+2 analyses) |
| GET | `/public/profile/{handle}` | ❌ | Public cached score (no auth) |
| GET | `/health` | ❌ | Health check |

### `/score` Flow
1. Verify JWT → get email
2. Look up user in `users` table — create on first use (plan: free, limit: 2)
3. Check `analyses_used >= analyses_limit` → 429 if over limit
4. Check Supabase `analyses` cache (7-day TTL) — return if found
5. Call Apify → fetch last 20 **feed posts**, follower count, engagement
6. Run 7-factor scorer → compute final score
7. Run verdict engine → campaign type, budget, risk, action items
8. Run ROI estimator → reach, conversion, revenue projection
9. Save to cache, increment usage counter
10. Return full `ScoreResponse`

### Scoring System

**Formula:** `score = round(weighted_sum × fraud_multiplier)`

| Factor | Weight | What it measures | Reliability |
|---|---|---|---|
| Engagement Quality | 30% | Like/comment ratio vs follower count, tier-adjusted | Medium |
| Content Rhythm | 20% | Feed post interval consistency | Low (see known issues) |
| Audience Reliability | 20% | Follower/following ratio, engagement vs expectation | Medium |
| Niche Depth | 15% | Beauty keyword coverage in captions + hashtags | Good |
| Authenticity | 10% | Sponsored signal ratio, engagement spike detection | Medium |
| Growth Momentum | 5% | Recent vs older post engagement | Low |
| Fraud Multiplier | modifier | Ghost follower signals, engagement spikes | Medium |

**Labels:** `elite` (85+) · `high` (70+) · `mid` (50+) · `risky` (30+) · `avoid` (<30)

**Optimal range: 10K–500K followers.** This is stated on the landing page as positioning, not disclaimer.

### Known Scoring Limitations

1. **Scraper only gets feed posts.** Instagram Reels and Stories are not scraped. Large accounts (100K+) that primarily post Reels will show 30+ day feed intervals → rhythm score returns neutral 50 instead of penalizing.

2. **Instagram hides likes on large accounts.** When `likesCount = 0`, fraud detector uses comment-only threshold instead of full engagement threshold.

3. **Weights are not data-validated.** The 30/20/20/15/10/5 split was designed by intuition. No real campaign outcome data has been used to validate these weights yet. Campaign Tracker will eventually fix this.

4. **ROI estimates are heuristic.** Revenue = conversions × AOV ($45 default). Conversions are estimated from engagement rate tiers, not real data. Show confidence levels honestly.

5. **Macro/mega influencers (500K+) are unreliable.** Engagement rate naturally drops at scale. Tier-based multipliers partially compensate but not fully validated.

6. **Tier multipliers (engagement.py):**
   - 5M+: ×80
   - 1M–5M: ×58
   - 500K–1M: ×52
   - 100K–500K: ×42
   - 10K–100K: ×22
   - <10K: ×12

   These were set by calibrating against industry-average ER benchmarks, not real campaign data.

### Plan Limits

| Plan | Analyses/month |
|---|---|
| free | 2 |
| trial | 2 |
| starter | 20 |
| growth | 75 |
| pro | 200 |

### Environment Variables (Railway)

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
FRONTEND_URL              # update after domain purchase
```

---

## Frontend

### Pages

#### `index.html` — Landing Page
- Headline: "Stop guessing which influencer will convert."
- Hero sub: decision-focused copy (Gift / Paid / Avoid in 30 seconds)
- Stats bar: 7 factors · Real data · AI fraud detection · Free to start · **10K–500K optimal range**
- Features: Instant Decision · Real Data · Outreach · Campaign Tracker (coming soon)
- "How it works": 3 steps ending with "track the result"
- Testimonials section
- Pricing grid ($29 / $79 / $199)
- Animated dashboard mockup (18s loop, mouse cursor, full product flow)
- All copy is beauty & skincare specific

#### `dashboard.html` — Main App
- Tabs: Discovery · Outreach · Analytics · **Campaigns** (new)
- Discovery: influencer cards with score, verdict, per-card Delete button, Clear History button
- Outreach: select influencer → generate AI outreach (Claude Haiku)
- Analytics: charts, score distribution, totals
- **Campaigns tab:** log campaign in 3 fields (handle, spend tier, outcome), localStorage persistence, "worth it" % summary
- Usage bar + upgrade/manage subscription in sidebar
- History: localStorage + Supabase sync (cross-device)

#### `influencer.html` — Detail View
- **Decision bar at top:** big clear verdict ("✓ Worth Working With" / "→ Proceed Carefully" / "✗ Do Not Work With") before any data
- Below verdict: campaign type badge, action bullets, reason
- Pills: Budget / Risk / Est. Sales
- ROI Forecast: spend vs return, adjustable AOV, break-even, worst case
- Key Signals: 2×2 grid (Biggest Strength, Biggest Risk)
- Campaign Plan: 3-week checklist
- Score breakdown (left column)
- Outreach template (AI or static)
- Niche warning if niche score < 30

#### `auth.html` — Auth
- Sign in / Sign up tabs
- Forgot password → reset email → `?mode=update` recovery
- After login with `?plan=` param → immediately calls `/create-checkout`

#### `legal.html` — Legal
- Tabbed: Terms of Service + Privacy Policy

### Supabase Tables

**`users`**
| Column | Type | Notes |
|---|---|---|
| id | uuid | |
| email | text | |
| plan | text | free / starter / growth / pro |
| analyses_used | int4 | Incremented on each analysis |
| analyses_limit | int4 | Set by plan |
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

**`campaigns`** *(must be created manually in Supabase)*
| Column | Type | Notes |
|---|---|---|
| id | uuid | |
| user_email | text | |
| handle | text | |
| spend_tier | text | gifted / under100 / 100-500 / 500-2k / 2k+ |
| outcome | text | worth_it / meh / waste |
| campaign_date | date | |
| orders_range | text | 0 / 1-5 / 5-20 / 20+ (optional, added later) |
| notes | text | optional |
| status | text | logged / completed |
| created_at | timestamptz | |

**RLS: disabled on all tables.** Backend uses service_role key (bypasses RLS). Frontend never queries tables directly. Anon key IS exposed in frontend JS — acceptable risk since anon key is read-only and tables are not directly queryable without RLS policies.

---

## Campaign Tracker

### Status: Frontend + Backend built. Supabase table needs manual creation.

### Purpose
Close the feedback loop: users log campaign outcomes → system eventually learns what actually works.

### Current implementation
- **Frontend (dashboard.html):** 3-field form (handle, spend tier, outcome). Data saved to localStorage. Badge shows campaign count.
- **Backend (main.py):** `/campaign/create`, `/campaigns`, `/campaign/{id}/result` endpoints — ready but localStorage is used for now.
- **Not yet wired:** frontend doesn't call backend campaign endpoints yet. Uses localStorage only. Cross-device sync for campaigns not implemented.

### Future: Feedback Loop
When enough campaign data exists (target: 50+ campaigns):
- campaigns table → aggregate by follower_tier + outcome
- Update `roi_calibration` table with real ROAS data
- Show "calibrated from X real campaigns" badge on ROI estimates
- This is the moat: real outcome data that competitors don't have

---

## Payments

Currently **Stripe** (test/live mode). Switching to **LemonSqueezy** when KYC approved (no registered company required — Merchant of Record model).

**Stripe flow:**
1. User clicks upgrade → `POST /create-checkout` with plan + JWT
2. Backend creates Stripe Checkout Session
3. User pays → `checkout.session.completed` webhook
4. Backend updates `users` table: plan + analyses_limit
5. Redirect to `/dashboard.html?upgraded=1`

---

## Positioning

| What Inflaid IS | What Inflaid is NOT |
|---|---|
| Fast screening tool | Precise ROI oracle |
| Decision helper (Gift/Paid/Avoid) | Replacement for human judgment |
| Best for 10K–500K creators | Reliable for 500K+ accounts |
| Outreach generator | Campaign management platform |
| Early feedback tracker | Validated ML model |

---

## Known Issues / To-Do

### Blocking (must fix before launch)
- [ ] **Domain** — still on `vettly-eight.vercel.app` / `vettly-production-63d5.up.railway.app`. After purchase: update `FRONTEND_URL` in Railway + Supabase Auth URLs (Site URL + Redirect URLs)
- [ ] **LemonSqueezy** — blocked on KYC. Will replace `/create-checkout`, `/customer-portal`, `/webhook`
- [ ] **`campaigns` Supabase table** — must be created manually (SQL in this file above)
- [ ] **Rename infrastructure** — repo name, Vercel project, Railway project still say "vettly"

### Important (pre-growth)
- [ ] **`analyses` table has no `user_email` column** — Supabase history sync fetches all public analyses, not per-user. Add `user_email` column and filter by it in `syncHistoryFromSupabase()`
- [ ] **Campaign tracker not wired to backend** — currently localStorage only. Wire `/campaign/create` call when user saves a campaign
- [ ] **OG image** — `og-image.png` referenced in meta tags but doesn't exist
- [ ] **Mobile polish** — fixed across all pages but may need additional review on real devices

### Future / Growth
- [ ] **ROI calibration from real campaigns** — when 50+ campaigns logged, build `roi_calibration` table and feed real ROAS into estimates
- [ ] **Email reminders** — "How did @handle go? (2 clicks)" 7 days after campaign log
- [ ] **Per-user analysis history** — requires `user_email` column in `analyses` table
- [ ] **Fashion / food / fitness categories** — `categories/config.py` has placeholder entries, just needs keywords
- [ ] **Admin panel** — no visibility into failed scrapes or usage stats
- [ ] **Confidence scoring UI** — backend can compute data confidence level; not yet shown in UI
- [ ] **Team seats** — Pro plan mentions team seats but not implemented

---

## Deployment

**Frontend (Vercel):**
- Auto-deploys on push to `main`
- No build step — static files
- `vercel.json` routes all paths to HTML files

**Backend (Railway):**
- Auto-deploys on push to `main`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Credit: ~$4-5/month at current traffic
- Fallback if credits run out: Render.com (free tier, ~30s cold start)
