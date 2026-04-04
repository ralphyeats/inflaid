# Vettly Project Configuration

## Project Overview
- **Name**: Vettly
- **Description**: Instagram influencer analysis platform for beauty brands (ROI scoring).
- **Tech Stack**: HTML/JS (Frontend), Supabase (Database/Auth), Railway (Backend), Vercel (Hosting).
- **Target User**: Beauty/skincare/makeup brand owners (Shopify).

## Architecture
- **Frontend**: Static HTML + Vanilla JS, hosted on Vercel.
- **Backend**: Python/FastAPI (Railway) — (verify if FastAPI).
- **Database**: PostgreSQL (Supabase) + Supabase Edge Functions.

## Development Standards

### Code Style
- Use standard HTML5 and Vanilla Javascript.
- Database: Use Supabase migrations (`supabase_migrations.sql`).
- SQL: snake_case for tables and columns.

### Naming Conventions
- **Frontend Files**: kebab-case (influencer-details.html).
- **Javascript**: camelCase for functions and variables.
- **Database Tables**: snake_case (influencer_scores, brand_users).

### Deployment
- Frontend: Automatically deployed via Vercel.
- Backend: Automatically deployed via Railway (`railway.toml`).

## Common Commands

| Command | Purpose |
|---------|---------|
| `npx supabase db push` | Push local migration to Supabase |
| `/optimize` | Analysis the current file for improvements (Claude Code) |
| `/pr` | Prepare a Pull Request summary (Claude Code) |

## Related Docs
- `PROJECT.md`: Project summary and features.
- `CONTEXT.md`: Context for developers and AI agents.
- `supabase_migrations.sql`: Current database schema.
