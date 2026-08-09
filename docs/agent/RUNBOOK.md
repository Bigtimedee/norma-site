# NORMA Twitter Agent — Runbook

Scheduled via `.github/workflows/twitter-agent.yml`. Runs twice daily (9 AM ET game preview, 5 PM ET app highlight). Entry point: `agent/main.py`.

---

## Known failure modes

### 403 Forbidden on `create_tweet` — "You are not permitted to perform this action"

**Root cause:** `tweepy.Client.create_tweet()` defaults to `user_auth=False`, which uses the bearer token (app-only / read-only auth). Posting requires OAuth 1.0a user context.

**Fix (applied Aug 2026):** `post_tweet` in `agent/twitter_client.py` now always passes `user_auth=True`. All four OAuth 1.0a credentials (`TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`) must be present in GitHub Secrets — the bearer token alone is not enough.

**If this recurs:** Check that all four OAuth secrets are set (not just `TWITTER_BEARER_TOKEN`). The error handler now logs `e.response.json()` on every Forbidden/BadRequest, so the full API error body will appear in the Actions run log.

---

### Tweet posted with meta-commentary ("Here's a tweet:", "---", "**Character count: N**")

**Root cause:** Claude was returning the tweet wrapped in preamble and annotations. The raw API response was being posted verbatim.

**Fix (applied Aug 2026):**
- System prompt now includes an explicit `CRITICAL OUTPUT FORMAT` instruction.
- `sanitize_tweet()` in `agent/content_generator.py` strips preamble lines, `---` separators, and character-count annotations defensively before the text is used.
- `_call_claude()` logs the final char count on every run — check the Actions log line `Final tweet (N chars): ...` to verify clean output.

---

### Tweet exceeds 280 characters

`_call_claude()` sanitizes, then regenerates once if still over 280, then truncates at a word boundary as a last resort. The log will show `Tweet over 280 chars` / `Still over 280 after regen` warnings if either fallback fires.

If this becomes frequent, tighten the prompt's character cap (currently 240 to leave room for the attached image).

---

## Dry-run mode

Run the full pipeline without posting:

```bash
cd agent
DRY_RUN=1 python main.py game_preview
# or
python main.py --dry-run app_highlight
```

The log will show the generated tweet text and char count, then `DRY RUN — skipping Twitter API call`.

---

## Required GitHub Secrets

| Secret | Purpose |
|---|---|
| `TWITTER_API_KEY` | OAuth 1.0a consumer key |
| `TWITTER_API_SECRET` | OAuth 1.0a consumer secret |
| `TWITTER_ACCESS_TOKEN` | OAuth 1.0a access token |
| `TWITTER_ACCESS_TOKEN_SECRET` | OAuth 1.0a access token secret |
| `TWITTER_BEARER_TOKEN` | Used for v2 Client construction (not for posting) |
| `ANTHROPIC_API_KEY` | Tweet generation via Claude Haiku |
| `ODDS_API_KEY` | Live odds (optional — falls back to ESPN public API) |
