# Plan: connect GitHub so this project runs without manual steps

**Date:** 2026-08-01
**Goal:** eliminate the manual steps you have been performing — opening pull requests by hand, pasting lint output, relaying CI failures from screenshots.

Every claim below is either a command output reproduced in this document, or a direct quote from Anthropic's documentation with its source named. Where I could not establish something, section 7 says so explicitly rather than filling the gap.

---

## 1. Measured capability, today

Run against `https://api.github.com` with the session's proxy-injected `GH_TOKEN`, 2026-08-01:

| Operation | Result | Message returned |
| --- | --- | --- |
| `git push` / `git fetch` via session proxy | **works** | Verified: 4 pushes this session |
| `GET /user` | **200** | — |
| `GET /rate_limit` | **200** | — |
| `GET /repos/Bigtimedee/norma-site` | **403** | "GitHub access is not enabled for this session. An org admin must connect the Claude GitHub App for this organization." |
| `GET /repos/{repo}/pulls` | **403** | same |
| `POST /repos/{repo}/pulls` | **403** | same |
| `GET /repos/{repo}/actions/runs` | **403** | same |
| `GET /user/repos` | **403** | "This GitHub API path is not available: sessions are bound to their connected repository" |
| `GET /user/installations` | **403** | same |

Git transport works. The GitHub REST API does not. That combination is why I can push branches but cannot open a pull request, read an Actions run, or fetch a workflow log.

---

## 2. There are two different blockers, not one

The two 403 messages above are distinct and have distinct causes. Conflating them would produce a plan that fixes the wrong thing.

### Blocker 1 — GitHub App not connected (fixable)

> "GitHub access is not enabled for this session. An org admin must connect the Claude GitHub App for this organization."

Returned by every `/repos/Bigtimedee/norma-site/*` path. The message names its own remedy. This is what sections 3 and 4 address.

### Blocker 2 — sessions are scoped to one repository (by design, not fixable)

> "This GitHub API path is not available: sessions are bound to their connected repository"

Returned by `/user/repos` and `/user/installations` — the cross-repository enumeration endpoints. This is a deliberate scoping rule, and it is a different mechanism from Blocker 1.

**This explains the `norma-agent` problem.** Earlier in this project, `git ls-remote` against `Bigtimedee/norma-agent`, `norma`, `norma-app` and `norma-mobile` all returned "repository not authorized" from the session proxy, while `norma-site` succeeded. That is the same scoping rule at the git layer.

Connecting the GitHub App will **not** give one session access to several repositories. To work on NORMA's application repository, start a session from that repository. Nothing in this plan changes that, and any plan claiming otherwise would be wrong.

---

## 3. Path A — connect the Claude GitHub App (primary)

This is the remedy the API error names.

**Who:** the docs state "You must be a repository admin to install the GitHub app and add secrets" (Claude Code GitHub Actions). The API error additionally says an **org admin** must connect it "for this organization", so `Bigtimedee` org-level authorization is involved, not only repository-level installation.

**How:** install from <https://github.com/apps/claude>.

**Permissions requested**, quoted from the documentation:

> * **Contents**: Read & write (to modify repository files)
> * **Issues**: Read & write (to respond to issues)
> * **Pull requests**: Read & write (to create PRs and push changes)

Grant it to `Bigtimedee/norma-site` at minimum. Selecting "Only select repositories" limits the blast radius; the docs describe that option for a custom app, and the same selector appears when installing the official app.

---

## 4. Path B — `/web-setup` (alternative)

The Claude Code on the web documentation describes two ways to grant GitHub access:

> | Method | How it works |
> | **GitHub App** | Authorize the Claude GitHub App during web onboarding |
> | **`/web-setup`** | Run `/web-setup` in your terminal to sync your local `gh` CLI token to your Claude account |

Path B requires the Claude Code CLI installed locally and `gh` already authenticated. It is listed as suitable for "Individual developers who already use `gh`".

Two documented constraints:

- "Team and Enterprise Owners can disable `/web-setup` with the Quick web setup toggle at claude.ai/admin-settings/claude-code."
- "Organizations with Zero Data Retention enabled can't use `/web-setup` or other cloud session features."

**Path B does not replace Path A if you want Auto-fix.** The docs are explicit: "The GitHub App is required for Auto-fix, which uses the App to receive PR webhooks. If you connect with `/web-setup` and later want Auto-fix, install the App on those repositories."

---

## 5. What connecting unlocks

Directly ends manual steps you have performed in this project:

| Manual step you did | After connection |
| --- | --- |
| Opened PR #1 by hand on an iPad, pasting title and body | I create the PR directly |
| Screenshotted a failing Actions run so I could read the traceback | I read Actions runs and logs myself |
| Pasted Supabase lint JSON, then GitHub error text | Unchanged for Supabase; GitHub-side reading becomes direct |

Two documented capabilities become available that this project has concrete uses for:

**Auto-fix pull requests.** Quoted: "Claude can watch a pull request and automatically respond to CI failures and review comments." The `Tests` workflow and the `NORMA Twitter Agent` workflow both run on this repository; a failing run is exactly the event Auto-fix exists for. Requires the App per section 4.

**Routines.** Documented as automating "work on a schedule, via API call, or in response to GitHub events."

---

## 6. Verification — the exact checks I will run

Immediately after you connect, ask me to verify. I will run these and report the raw results, not a summary:

```bash
# Blocker 1 should clear: expect 200
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $GH_TOKEN" \
  https://api.github.com/repos/Bigtimedee/norma-site

# The capability that matters: expect a JSON array, not a 403
curl -sS -H "Authorization: Bearer $GH_TOKEN" \
  https://api.github.com/repos/Bigtimedee/norma-site/pulls

# The gap from the 2026-07-31 incident report: expect run history
curl -sS -H "Authorization: Bearer $GH_TOKEN" \
  "https://api.github.com/repos/Bigtimedee/norma-site/actions/runs?per_page=5"

# Blocker 2 is expected to STILL 403. If it does, that is correct, not a failure.
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $GH_TOKEN" https://api.github.com/user/repos
```

Then, as a real end-to-end test rather than a probe, I will open the pending pull request for the current branch via the API.

If any of these still fail, I will report the exact status and message rather than working around it. The proxy README states: "do not retry organization policy denials (403/407) — report them instead."

---

## 7. What I could not establish

Stated plainly because the plan should not imply more certainty than I have.

**The documentation and the error message do not agree.** The Claude Code on the web page says, of both auth methods:

> "With either method, a cloud session can access any repository the connecting GitHub account can see, not just the repositories the Claude GitHub App is installed on. App installation enables PR webhooks for Auto-fix; **it is not a session-level access control**."

That statement is in tension with the 403 this session actually returns, which says GitHub access is not enabled and names App connection as the fix. I cannot resolve the discrepancy from inside the session: I cannot query organization policy, and `/user/installations` is blocked by Blocker 2.

How I am treating it: the error message is authoritative for this session's actual state, because it is what the system returns when I make the call. So Path A is primary. If Path A is completed and the 403 persists, that is evidence the constraint is an organization policy beyond App installation, and the next step is Anthropic support rather than further attempts from here.

**I also cannot confirm** which specific admin role on the `Bigtimedee` organization is required, or whether the organization has policies (IP allowlisting, Zero Data Retention) that affect this. Those are visible to you and not to me.

---

## 8. Recommendation

Do Path A. It is named by the error, it is a single browser action, it is the only path that enables Auto-fix, and it does not require a local CLI.

Grant it to `norma-site` only for now. If it works, extend to NORMA's application repository — which is separately valuable, because the ProphetX integration in `prophetx/` is blocked on reading that codebase, and section 2 establishes that a second repository needs its own session rather than broader permissions on this one.

Tell me when it is done and I will run section 6 and report the raw output.
