# ProphetX integration — engineering notes

Read-only ProphetX market data for NORMA (Path A of the integration plan).
All facts below were verified on **30 July 2026**; sources are named so each
can be re-checked rather than taken on trust.

---

## Where this code belongs

This package lives in `norma-site` because that is the only repository the
authoring session could reach — `Bigtimedee/norma-agent`, `norma`, `norma-app`
and `norma-mobile` all returned *"repository not authorized"* through the
session proxy.

It is written to move. `prophetx/` depends only on `httpx` and the standard
library, imports nothing from NORMA, and knows nothing about Supabase or Expo.
Lifting it into the application repository should be a directory copy plus the
wiring in "Integrating into NORMA" below.

It is **not** part of the social-media agent in `agent/`, and nothing in
`agent/` imports it.

---

## Verified facts

| Fact | Value | How it was verified |
|------|-------|---------------------|
| API name | "External Affiliate API" — *"Provides data upon sport events, markets for Partners"* | OpenAPI `info` block |
| Sandbox base URL | `https://api-ss-sandbox.betprophet.co/partner` | OpenAPI `servers`; live probe returned 401 (not 404) |
| Auth scheme | `apiKey` in the `Authorization` header (securityScheme `Token`) | OpenAPI `components.securitySchemes`; confirmed live |
| Error body | `{"error": "...", "message": "..."}` | Live 401 response |
| Support contact | `support@betprophet.co` | OpenAPI `info.contact.email` |
| Endpoints | `GET /affiliate/get_tournaments`, `GET /affiliate/get_sport_events`, `GET /v4/affiliate/get_markets` | OpenAPI `paths` |
| `get_markets` required param | `event_id` (integer) | OpenAPI `parameters[].required` |
| `market_types` values | `moneyline`, `spread`, `total` (`market_type` singular is `@deprecated`) | OpenAPI enum |
| `event_ids` encoding | comma-separated single param (`style: form, explode: false`) | OpenAPI parameter style |
| `selections` shape | array **of arrays** of `v4.Selection` — liquidity levels | OpenAPI schema + v3 changelog: *"selections: support multiple levels of liquidity"* |
| Tournament IDs | MLB 109 · KBO 2541 · Professional Baseball 1036 · NFL Preseason 233 · NFL 31 · NHL 234 · NBA 132 | Documented in `get_sport_events` description |
| Regulatory | CFTC approved DCM **and** DCO on 11 Jun 2026; nationwide launch 18 Jun 2026 | ProphetX press release; trade press |

Note the API is hosted on **`betprophet.co`**, not `prophetx.co`. Allowlists and
egress rules need the former.

---

## Deliberate design decisions

**The client cannot place an order.** `prophetx/client.py` contains no `.post`,
`.put`, `.patch` or `.delete` call, and `_get` rejects any path outside
`/affiliate/` and `/v4/affiliate/` before opening a connection. Two tests
enforce this — one greps the source for mutating verbs, one asserts trading
paths raise. This implements NORMA's Terms of Service §3 ("does not facilitate,
process, or broker any wagers or bets") as code rather than as a convention
someone can forget.

**Availability fails closed.** `prophetx/availability.py` defaults to disabled
and requires remote config to turn ProphetX on. Rationale: federal/state
jurisdiction over sports prediction markets is unresolved and has flipped
repeatedly — the Third Circuit ruled for preemption on 6 Apr 2026, state
regulators won at the injunction stage in Nevada, Maryland and Ohio, and 44
states disputed CFTC authority on 28 Jul 2026. Whether NORMA surfaces ProphetX
must therefore be changeable without an app release. Wrongly hiding a market
costs a feature; wrongly showing one costs a compliance problem.

**No jurisdiction list is hard-coded.** ProphetX has not told us which states it
serves. `allowed_regions` ships empty, and empty + `region_gating: true` means
deny. Inventing a list would be worse than having none.

**Production must be opted into.** ProphetX does not publish a production host,
so `PROPHETX_BASE_URL` defaults to sandbox. Silently serving sandbox prices as
real prices is the worst available failure, so going live is explicit.

**Liquidity levels are preserved, not flattened.** `Market.selections` stays
nested; `Market.best_selections` returns the top level for display. Flattening
would merge price levels and misstate the book. The ordering guarantee is
question 8 in `OPEN-QUESTIONS.md` — if the outer array is not sorted best-first,
`best_selections` is wrong and must change.

**Parsing is tolerant.** Unknown fields are ignored and missing fields become
`None`. ProphetX's own v2 and v3 changelogs show they add fields to existing
responses, and a new field should never take out a NORMA release.

---

## Usage

```python
from prophetx import client_from_env, AvailabilityGate

gate = AvailabilityGate()                      # PROPHETX_CONFIG_URL
if not gate.is_available(user_region):         # fails closed
    return None

with client_from_env() as px:
    tournaments = px.get_tournaments(has_active_events=True)
    events = px.get_sport_events(tournament_id=31)          # NFL
    markets = px.get_markets(events[0].event_id, market_types=["moneyline"])
    for sel in markets.markets[0].best_selections:
        print(sel.display_name, sel.display_price)          # render display_price
```

Render `display_price`, not a locally formatted `price`, so that what a user
sees in NORMA matches what they see on ProphetX.

### Configuration

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `PROPHETX_API_KEY` | yes | — | Server-side only. Static header key: shipping it in a mobile binary leaks it. |
| `PROPHETX_BASE_URL` | for production | sandbox | Must be set explicitly to go live. |
| `PROPHETX_CONFIG_URL` | to enable | unset | Remote availability config. Unset ⇒ ProphetX stays off. |

Sample availability config: `docs/prophetx/availability.sample.json`.

### Verifying

```bash
python3 -m pytest tests/test_prophetx.py -q     # 25 tests, no network, no key
PROPHETX_API_KEY=... python3 -m prophetx.smoke  # live read path
```

---

## Integrating into NORMA

1. Copy `prophetx/` into the application repository.
2. Store the key in the backend secret store; call ProphetX **server-side only**
   (Supabase edge function or equivalent). The device must never hold the key.
3. Host the availability config somewhere editable without an app release, and
   point `PROPHETX_CONFIG_URL` at it.
4. Cache responses. `get_markets` takes one call per `event_id`, so an
   uncached full slate multiplies fast — and rate limits are still unknown
   (question 3).
5. Map ProphetX markets into whatever shape NORMA already uses for The Odds API
   so the UI does not need a special case. **This mapping is not written**: it
   requires NORMA's actual model definitions, which were not reachable.

---

## Not done, and why

- **Path B (user-connected ProphetX accounts).** Blocked on question 1 —
  whether a user token can be scoped read-only. If the only available token can
  also trade and withdraw, NORMA would be custodying a credential that can move
  a user's money, which needs a decision before any code.
- **Mapping into NORMA's domain model.** Needs the application repository.
- **Privacy policy update.** `privacy-policy.html` names Kalshi and Polymarket
  as the prediction markets whose credentials NORMA stores. ProphetX must be
  added there **when Path B ships** — but not before, because until then the
  statement would be false. Path A stores no user credential and no user data,
  so it triggers no disclosure change.
- **The access request itself.** Needs a human: see `API-ACCESS-REQUEST.md`.

---

## Sources

- ProphetX OpenAPI definitions: `docs.prophetx.co/reference/get_affiliate-get-tournaments-2.md`,
  `…/get_affiliate-get-sport-events-2.md`, `…/get_v4-affiliate-get-markets.md`
- ProphetX developer hub: <https://docs.prophetx.co/>
- Requesting access: <https://docs.prophetx.co/docs/requesting-api-access>
- NORMA Terms of Service and Privacy Policy, effective 21 Feb 2026 (this repository)
- Regulatory timeline and citations: see the published integration plan
