# ProphetX integration — open questions

Send to ProphetX with the API access request. Questions are ordered by what
blocks the most work.

Four questions from the original plan were **answered** by ProphetX's published
OpenAPI definitions (retrieved 30 July 2026) and by a live probe of the sandbox
host. They are recorded at the bottom so nobody re-asks them.

---

## Blocking — answer before any user-facing work

### 1. Can a Market Data API key be scoped read-only, and is it separate from a user's trading credentials?

NORMA displays markets and reads a user's own positions. It does not place
orders, by its own published Terms of Service. Two sub-questions:

- **Partner key:** is the Market Data (`/affiliate/*`) key restricted to those
  endpoints server-side? Our client cannot construct a trading request, but we
  want the credential itself to be incapable of it.
- **User credentials (later phase):** ProphetX documents that users create
  tokens under Settings/Token, and the Trading API exposes order placement and
  wallet operations alongside read endpoints. **Can a user issue a token that
  can read positions and balances but cannot trade, deposit, or withdraw?**

This is the highest-priority question. If a user token capable of moving funds
is the only option, NORMA would be custodying a credential with materially
greater blast radius than its existing Kalshi and Polymarket connections, and
that changes the design and the risk review.

### 2. What is the production base URL?

The published OpenAPI `servers` block lists only
`https://api-ss-sandbox.betprophet.co/partner`. Our client requires the
production host to be set explicitly and refuses to guess, so we cannot ship
beyond sandbox without it.

### 3. What are the rate limits?

No limits are published. We currently pace requests conservatively and back off
on HTTP 429. We need the real ceiling to size caching and refresh intervals for
a mobile client. Specifically: requests/second and requests/day, whether limits
are per key or per IP, and whether `get_markets` is weighted differently
(it requires one call per `event_id`, so a full slate multiplies quickly).

---

## Commercial and legal

### 4. What are the terms of use for displaying ProphetX market data?

No display restrictions, attribution requirements, or logo/branding rules
appear in the documentation. We would rather follow your requirements than
discover them later. Is there an agreement to sign?

### 5. Is there an affiliate or revenue-share arrangement, and does it apply here?

The market data endpoints are namespaced `affiliate-*` and the API is titled
"External Affiliate API", which suggests they sit inside an affiliate
relationship. No affiliate terms were locatable. Please clarify whether access
requires enrolment and what, if anything, it obliges NORMA to do.

### 6. Current state-by-state availability, and how will we be notified of changes?

Launch was announced "throughout the U.S." on 18 June 2026. Given ongoing
federal/state litigation over prediction market jurisdiction, we have built a
remote-configuration gate that lets us enable or disable ProphetX per
jurisdiction without an app release. We need (a) the current list and (b) a
notification path when it changes. We would rather over-restrict than surface a
market in a state where it should not appear.

---

## Data semantics

### 7. What do "cash" and "play" denote, and which does the Affiliate API return?

The public site uses a `?currency=cash` parameter; one integration guide
references a "cash platform" hosted at `cash.api.prophetx.co`; the Trading API
endpoint titles use "play" ("Matched plays", "Play history"); and the Android
package identifier is `com.prophetxsweepstake`. If more than one currency mode
exists, NORMA must know which mode the Affiliate API describes — showing one as
the other would misrepresent a user's position.

### 8. Confirm the `selections` structure in `/v4/affiliate/get_markets`.

The v3 changelog states "selections: support multiple levels of liquidity", and
the v4 schema types `selections` as an array of arrays of `v4.Selection`. We
have implemented the outer array as liquidity depth, ordered best-first, and we
render only the top level by default. Please confirm the ordering guarantee —
if the outer array is not sorted best-first, our display is wrong.

### 9. What is the authoritative `updated_at` semantic, and is there a push/WebSocket option for market data?

`updated_at` appears as an integer on tournaments, events and selections. Is it
epoch seconds or milliseconds? Separately, your docs list WebSocket integration
pages; is streaming available to Market Data partners, or is it Trading-only?
Polling a full slate over REST is expensive for a mobile backend.

### 10. Access token lifetime (Trading API, for the later phase)

Two documents disagree: the odds-screen integration guide states a one-hour
`accessToken` with a 30-day `refreshToken`, while `llms.txt` states access
tokens expire after ten minutes. Which applies, and does it differ by product?

---

## Answered — do not re-ask

| # | Question | Answer | Source |
|---|----------|--------|--------|
| A | Does Market Data auth differ from Trading auth? | **Yes.** Market Data uses OpenAPI securityScheme `Token` = `apiKey` in the `Authorization` header — a static key, not the Trading API's `access_key`/`secret_key` login and refresh flow. | OpenAPI `components.securitySchemes` in all three `/affiliate` reference specs |
| B | Sandbox base URL | `https://api-ss-sandbox.betprophet.co/partner` | OpenAPI `servers`; confirmed live 30 Jul 2026 (returns HTTP 401, not 404, without a key) |
| C | Support contact | `support@betprophet.co` | OpenAPI `info.contact.email` |
| D | Error response shape | `{"error": "...", "message": "..."}` on 401 | Observed live from the sandbox, matching `response.ErrorResponse` |
