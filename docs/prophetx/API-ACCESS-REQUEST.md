# ProphetX Market Data API — access request

**Status:** ready to send. Requires a human to submit; it asks for company
details and a support-portal account that cannot be created programmatically.

**Where to submit:** ProphetX's documented path is a support request at
<https://prophethelp.zendesk.com/hc/en-us/requests/new>. Their docs state the
team "will review your request and grant API access if your application is
approved."

**Contact address:** `support@betprophet.co`, taken from the `info.contact`
block of ProphetX's own published OpenAPI definitions. (The address rendered on
the *Requesting API Access* page is Cloudflare-obfuscated; this one is in plain
text in the spec, so it is the one to trust.)

**Fill in before sending** — anything in `[brackets]` is a fact only NORMA can
supply. Do not guess these.

---

## Draft message

> **Subject:** Market Data API access request — NORMA (sports alerts & wager tracking app)
>
> Hello,
>
> I'd like to request access to the ProphetX **Market Data API** (the External
> Affiliate API, `/affiliate/*` endpoints) for NORMA.
>
> **What NORMA is.** NORMA is a sports alerts and wager tracking application.
> Users follow teams, receive game alerts, and keep a personal record of wagers
> they have placed elsewhere. NORMA already integrates market data from ESPN,
> SportsDataIO, Sportradar and The Odds API, and already supports user-connected
> prediction market accounts for Kalshi and Polymarket.
>
> **What we want to build.** Two phases:
>
> 1. **Display ProphetX markets** (this request). Read-only use of
>    `get_tournaments`, `get_sport_events` and `v4/get_markets` so NORMA users
>    can see ProphetX pricing alongside the other sources we already show.
> 2. **User-connected positions** (later, subject to your answer on token
>    scoping). Letting a NORMA user link their own ProphetX account so NORMA can
>    display their open positions, exactly as we already do for Kalshi and
>    Polymarket.
>
> **What NORMA will not do.** NORMA does not place, broker, or process trades of
> any kind, and has no plans to. Our published Terms of Service state that NORMA
> "does not facilitate, process, or broker any wagers or bets" and "is not a
> sportsbook, betting exchange, or gambling operator." We are not requesting the
> Trading API or the ISV API. Our client implementation is physically incapable
> of issuing a non-GET request and is restricted to the `/affiliate/*` and
> `/v4/affiliate/*` namespaces, with an automated test enforcing both.
>
> **Technical readiness.** We have already built and tested our integration
> against your published OpenAPI definitions, including
> `affiliate.ListAffiliateResponseV4` and the nested `selections` liquidity
> levels. We are ready to test against sandbox
> (`https://api-ss-sandbox.betprophet.co/partner`) as soon as we have a key.
>
> **Details you may need:**
> - Legal entity: `[company legal name]`
> - Product: NORMA — `[iOS App Store / Google Play links]`
> - Website: `[NORMA's website URL]`
> - Technical contact: `[name, email]`
> - Business contact: `[name, email]`
> - Current monthly active users: `[figure]`
> - Expected request volume: `[estimate once rate limits are known — see below]`
> - Platform: React Native (Expo) client with a Supabase backend; all ProphetX
>   calls are made server-side, never from the device.
>
> I've attached a short list of technical questions (token scoping, production
> base URL, rate limits, display terms, and jurisdiction coverage) that affect
> how we build. Happy to get on a call.
>
> Thanks,
> `[name, title]`

---

## Attach

`docs/prophetx/OPEN-QUESTIONS.md` — ten questions, ordered by what blocks work.
Question 1 (read-only token scoping) determines whether phase 2 happens at all,
so flag it as the one that matters most.

## After access is granted

1. Put the key in the backend secret store. It is **not** an app-client secret —
   ProphetX auth is a static header key, so a key shipped in a mobile binary is
   a leaked key.
2. Set `PROPHETX_API_KEY`, and leave `PROPHETX_BASE_URL` unset to stay on
   sandbox until production is verified.
3. Run the live smoke check: `python3 -m prophetx.smoke` (see
   `docs/prophetx/INTEGRATION-NOTES.md`).
