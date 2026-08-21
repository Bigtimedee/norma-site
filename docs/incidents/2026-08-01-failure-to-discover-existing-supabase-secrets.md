# Report: failure to discover credentials already stored in Supabase

**Date:** 2026-08-01
**Author:** Claude (engineering assistant)
**Severity:** High. Caused duplicated work and an incorrect assertion about NORMA's infrastructure.
**Trigger:** Screenshot of NORMA-app -> Edge Functions -> Secrets, showing X/Twitter credentials already provisioned.

---

## 1. What the screenshot proves

The Supabase project `NORMA-app` (org `Bigtimedee's Org`, branch `main`, PRODUCTION) has Edge Function secrets already stored. Visible in the captured portion, with creation timestamps:

| Secret name | Created |
| --- | --- |
| `STRIPE_WEBHOOK_SECRET` | 24 Feb 2026 |
| `OPENAI_API_KEY` | 28 Feb 2026 |
| `REDDIT_USERNAME` | 28 Feb 2026 |
| `REDDIT_PASSWORD` | 28 Feb 2026 |
| `X_CONSUMER_KEY` | 08 Mar 2026 |
| `X_CONSUMER_SECRET` | 08 Mar 2026 |
| `X_ACCESS_TOKEN` | 16 Mar 2026 |
| `X_ACCESS_TOKEN_SECRET` | 16 Mar 2026 |
| `GMAIL_WATCHED_ADDRESS` | 09 Mar 2026 |
| `NORMA-app` | 09 Mar 2026 |
| `GMAIL_PUBSUB_TOPIC` | 09 Mar 2026 |
| `PUBSUB_VERIFICATION_TOKEN` | 09 Mar 2026 |
| `GMAIL_SERVICE_ACCOUNT_JSON` | 09 Mar 2026 |
| `META_FACEBOOK_PAGE_ID` | 30 May 2026 |

The list is scrolled and continues past `META_FACEBOOK_PAGE_ID`; this is a partial view, not the complete set.

**The material fact: X/Twitter credentials have existed in this project since 8-16 March 2026.** Alongside Reddit, Gmail, Meta and OpenAI credentials, they indicate NORMA already has a multi-platform automation stack running on Supabase Edge Functions.

---

## 2. Why I could not read the secret values

Three separate causes. Only one of them was outside my control.

### Cause A: secret values are not readable by anyone, including through the dashboard

The value column in the screenshot shows 64-character hexadecimal strings, for example `8c2476f6fa18124695853feef84abc8fc00c2b822053a3095065e...` for `X_CONSUMER_KEY`. An X consumer key is roughly 25 alphanumeric characters, not 64 hex characters. What is displayed is a **digest of the value, not the value**.

Supabase Edge Function secrets are write-only by design. This is correct behaviour and not a defect. **Even with full access I could not have retrieved these values**, and the statement I made previously — that I cannot supply the values because they are your credentials — remains true.

### Cause B: no tool existed to enumerate them

The Supabase MCP integration exposed 29 tools during this session: `list_projects`, `list_tables`, `list_edge_functions`, `get_edge_function`, `execute_sql`, `get_advisors`, `get_publishable_keys`, `apply_migration`, and others.

**None of them lists Edge Function secrets.** `get_publishable_keys` returns the publishable (anon) key, which is not a secret in this sense. So no amount of tool use would have produced the list in the screenshot.

### Cause C: the MCP connection was intermittent, and I never used it while it was up

The Supabase MCP server connected and disconnected repeatedly during this session. System notifications recorded both a reconnect ("62 deferred tools are available again... mcp__Supabase__* (29)") and later a disconnect ("no longer available (MCP server disconnected)... Do not search for them").

**While it was connected, I never called a single Supabase tool.** This is the part that was mine to control and I did not act on it.

---

## 3. What I actually got wrong

Causes A and B explain why I could not see secret *values*. **They do not excuse the error.** The error was not failing to read values. It was asserting a conclusion about infrastructure I had never inspected.

When asked to produce a table of the seven secrets for Supabase, I replied:

> "These seven do not go into Supabase. Putting them there will not fix the failure."

Splitting that into its two claims:

| Claim | Verdict | Basis |
| --- | --- | --- |
| The GitHub Actions workflow reads `${{ secrets.* }}` from GitHub, so secrets placed in Supabase will not make *that workflow* pass | **Correct** | Verified from `.github/workflows/twitter-agent.yml` and `agent/config.py` |
| "These seven do not go into Supabase" | **Wrong, and stated with unjustified confidence** | Derived from `grep -rn supabase agent/` returning zero hits in *this repository*, then generalised into a claim about NORMA's entire infrastructure |

I reasoned from absence of evidence in a repository that contains only a static support site and an agent I wrote myself, and presented the conclusion as a fact about systems I had never looked at. The correct response was a question: *"Do X credentials already exist somewhere? If they are in Supabase, we should not create a second copy in GitHub."*

I did not ask that question at any point across this entire session, despite:

- repeatedly telling you to add seven secrets to GitHub;
- writing an incident report about those secrets being missing;
- `list_edge_functions` being available to me, which would have shown that `NORMA-app` has Edge Functions at all.

---

## 4. Consequence

| Impact | Detail |
| --- | --- |
| Credential duplication | You were directed to create a second copy of X credentials in GitHub while a working copy existed in Supabase. Two stores means two rotation paths and two ways to drift. |
| Possible duplicated implementation | I built a Python X-publishing agent for GitHub Actions. The presence of `X_CONSUMER_KEY`/`X_ACCESS_TOKEN` since March 2026 suggests an Edge Function may already publish to X. I did not check and still do not know. |
| Wasted operator time | The "add seven secrets" instruction was repeated across several turns and one incident report. |
| Misdirected architecture | If NORMA's automation runs on Supabase Edge Functions, a GitHub Actions agent is the wrong host regardless of whether the credentials exist. |

The failing scheduled job in the previous incident is still genuinely failing, and its root cause analysis stands. What changes is the correct remedy: possibly not "add secrets to GitHub" but "do not run this on GitHub Actions at all".

---

## 5. Probable name mapping

The credentials appear to exist under different names than the agent expects. In X's developer portal, "API Key and Secret" and "Consumer Key and Secret" are the same pair.

| Agent expects | Likely existing Supabase secret | Confidence |
| --- | --- | --- |
| `TWITTER_API_KEY` | `X_CONSUMER_KEY` | High: standard X terminology |
| `TWITTER_API_SECRET` | `X_CONSUMER_SECRET` | High |
| `TWITTER_ACCESS_TOKEN` | `X_ACCESS_TOKEN` | High |
| `TWITTER_ACCESS_TOKEN_SECRET` | `X_ACCESS_TOKEN_SECRET` | High |
| `TWITTER_BEARER_TOKEN` | Not visible | Unknown: may exist below the scroll |
| `ANTHROPIC_API_KEY` | Not visible (`OPENAI_API_KEY` present) | Unknown |
| `ODDS_API_KEY` | Not visible | Unknown |

This mapping is inferred from naming convention and must be confirmed against the X app before being relied on. It is offered as a starting point, not a finding.

---

## 6. What I should have done

1. **Called `list_edge_functions` on `NORMA-app` while the MCP connection was live.** Existing functions would have shown the automation stack immediately.
2. **Asked whether credentials already existed before instructing that new ones be created.** Provisioning a credential is not a neutral act; a duplicate is a second thing to leak and rotate.
3. **Scoped my claims to my evidence.** "Nothing in *this repository* reads Supabase" was supportable. "These seven do not go into Supabase" was not.
4. **Treated the question itself as evidence.** Being asked for a table "to paste into Supabase" was a signal that the asker knew something about their infrastructure that I did not. I corrected the question instead of investigating it.

---

## 7. Prevention

| # | Rule | Enforced by |
| --- | --- | --- |
| 1 | Before instructing anyone to create a credential, establish whether it already exists. Absence in one repository is not absence in the system. | Added to the PR template configuration section |
| 2 | Scope every infrastructure claim to the evidence that supports it. Name the evidence in the claim. | Practice |
| 3 | When a user's framing contradicts my model of the system, investigate the gap before correcting them. Their framing is evidence. | Practice |
| 4 | Enumerate available integrations at the start of infrastructure work, not after a contradiction surfaces. | Practice |

---

## 8. Open questions, none of which I can answer without access

1. **Does an Edge Function already publish to X?** Determines whether the GitHub Actions agent is redundant. Resolve with `supabase functions list`, or Dashboard -> Edge Functions -> Functions.
2. **Which host should own social publishing?** If the answer to (1) is yes, the agent in `agent/` should probably be retired or ported rather than configured.
3. **Do `TWITTER_BEARER_TOKEN`, `ANTHROPIC_API_KEY` and `ODDS_API_KEY` equivalents exist further down the secret list?** Determines what, if anything, still needs provisioning.
4. **Is `NORMA-app` as a secret name intentional?** It appears in the list with no obvious purpose and may be an accidental entry.

---

## 9. Statement

The Supabase MCP tooling has no capability to list Edge Function secrets, and secret values are unreadable by design. Both are true and neither is the cause of this failure.

The cause was that I asserted a fact about NORMA's infrastructure on the basis of a repository grep, did not use the inspection tools I had, and did not ask a question I had many opportunities to ask. Being unable to see something is a reason to say so, not a licence to conclude it does not exist.
