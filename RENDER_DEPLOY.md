# Render backend deploy

Inflaid frontend stays on Vercel. This Render service replaces the old Railway backend.

## Create the service

1. Open Render.
2. Choose New > Blueprint.
3. Connect the GitHub repository `ralphyeats/inflaid`.
4. Select the blueprint from `render.yaml`.
5. Create the `inflaid-api` web service.

## Environment variables

Render will ask for these secret values. Copy the same values that were in Railway:

```text
SUPABASE_URL
SUPABASE_KEY
ANTHROPIC_API_KEY
APIFY_TOKEN
LEMONSQUEEZY_API_KEY
LEMONSQUEEZY_STORE_ID
LEMONSQUEEZY_WEBHOOK_SECRET
LEMONSQUEEZY_STARTER_VARIANT
LEMONSQUEEZY_GROWTH_VARIANT
LEMONSQUEEZY_PRO_VARIANT
```

These are already defined by the blueprint:

```text
PYTHON_VERSION=3.11.9
FRONTEND_URL=https://www.inflaid.com
FOUNDER_EMAILS=ralphyeats@gmail.com,ralphyeatss@gmail.com
```

## After deploy

1. Open the Render service URL.
2. Check `/health`; it should return `{"status":"ok"}`.
3. Send the Render URL back to Codex.
4. Replace the old Railway URL in frontend files with the Render URL.
5. In Lemon Squeezy, update the webhook URL to the new Render backend.
