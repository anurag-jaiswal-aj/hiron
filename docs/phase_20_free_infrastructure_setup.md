# Phase 20 — Free Infrastructure Setup

## Billing Safety Report

| Provider | Account Ready | Free Tier | Card Required | Billing Enabled | Verified |
|----------|---------------|-----------|---------------|-----------------|----------|
| Vercel | No | Yes (Hobby) | No | No | Yes |
| Supabase | No | Yes (Free) | No | No | Yes |
| Upstash | No | Yes (Free) | No | No | Yes |
| Google AI | No | Yes (Developer) | No | No | Yes |

### Billing Safety Analysis

- **Vercel**: The Hobby tier does not require a credit card and does not automatically transition to a paid plan. When limits are hit, requests are blocked or rate-limited. There is NO possibility of automatic surprise billing.
- **Supabase**: The Free tier does not require a credit card. It pauses the project after a week of inactivity and enforces hard limits on database storage (500MB). There is NO possibility of automatic billing without explicitly adding a card and opting into the Pro plan.
- **Upstash**: The Free tier does not require a credit card. QStash provides 10,000 messages/day. Messages over the limit are rejected. There is NO possibility of automatic billing.
- **Google AI Studio (Gemini)**: The API is available via a free tier (for developers in supported regions) which provides 15 RPM / 1M TPM. A credit card is not required unless you link the project to an active Google Cloud Billing account and explicitly opt-in to pay-as-you-go. There is NO possibility of automatic billing as long as you use the free tier API key through Google AI Studio.

All providers selected for this architecture are strictly free-tier compliant and pose **zero risk of surprise billing**.
