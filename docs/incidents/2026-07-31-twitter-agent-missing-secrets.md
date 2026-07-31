# Incident: NORMA Twitter Agent fails on missing secrets

**Report date:** 2026-07-31
**Component:** `agent/` (NORMA X/Twitter publishing agent)
**Workflow:** `.github/workflows/twitter-agent.yml` (`name: NORMA Twitter Agent`, job `post`)
**Status:** Root cause identified and reproduced. Code fix implemented and tested. Operator action still required: the seven secrets must be added.

---

## Summary

The scheduled job `NORMA Twitter Agent / post` fails at the `Run NORMA agent` step with exit code 1. The agent requires seven API credentials supplied as GitHub repository secrets, and none of them have been added to the repository, so `Config.from_env()` raises before any work is done. This is a configuration gap in the repository, not a fault in the runner, the agent logic, or any third-party API.

---

## Impact

| Item | Status |
| --- | --- |
| Tweets published by the agent | None. The process exits before the Twitter client is constructed. |
| External API calls (Odds API, Anthropic, X) | None made. The failure occurs before the first network call. |
| Data loss or corruption | None. The agent is write-only to X and performs no persistence. |
| Other workflows | Not affected. `Tests` and `Deploy GitHub Pages` do not consume these secrets. |
| Number of failed runs | **Unknown.** See [Verification gap](#verification-gap). |
| First occurrence | **Unknown.** See [Verification gap](#verification-gap). |

The user-visible effect is that the NORMA account has not been posting via the agent. We cannot quantify how long that has been true or how many runs failed, because we could not read the Actions run history.

---

## Timeline

**We cannot construct a timeline.** GitHub API access for this repository is unavailable to us (HTTP 403, "GitHub access is not enabled for this session. An org admin must connect the Claude GitHub App for this organization"), so we have no run IDs, no run timestamps, no first-failure time, and no failure count.

What is known, and its source:

| Fact | Source |
| --- | --- |
| A run of `NORMA Twitter Agent / post` failed at step `Run NORMA agent` with exit code 1, output as quoted under Root cause | Captured job output provided with the report |
| The workflow and the agent were added in commit `94bbc5d`, dated 2026-05-05 | `git log -- .github/workflows/twitter-agent.yml` |

The commit date bounds the earliest possible run but is not evidence that runs occurred then. Do not read it as a start-of-impact time.

---

## Root cause

### 1. Seven required secrets were never added to the repository

`agent/config.py`, `Config.from_env()`, requires all of:

`TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`, `TWITTER_BEARER_TOKEN`, `ANTHROPIC_API_KEY`, `ODDS_API_KEY`

The workflow maps each one from `secrets.*` in the `env:` block of the `Run NORMA agent` step. When a GitHub repository secret does not exist, the `${{ secrets.NAME }}` expression resolves to an empty string. The environment variable is therefore present but empty. `from_env()` tests with `if not os.environ.get(key)`, which treats an empty string as missing, collects all seven, and raises.

Captured output:

```
INFO  Starting NORMA agent | post_type=app_highlight
Traceback (most recent call last):
  File "/home/runner/work/norma-site/norma-site/agent/main.py", line 79, in <module>
    main()
  File "/home/runner/work/norma-site/norma-site/agent/main.py", line 75, in main
    run(args.post_type)
  File "/home/runner/work/norma-site/norma-site/agent/main.py", line 33, in run
    cfg = Config.from_env()
  File "/home/runner/work/norma-site/norma-site/agent/config.py", line 39, in from_env
    raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")
OSError: Missing required env vars: TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET, TWITTER_BEARER_TO...
```

Reproduced locally: running `python3 main.py app_highlight` from a clean checkout of `agent/` at commit `744dfac` with those seven variables unset produces the identical traceback, the same frames and line numbers (`main.py` 79, 75, 33; `config.py` 39), and exit code 1. All seven names appear in the message, confirming that none of the secrets were set rather than only some.

### 2. The error type misdescribes the failure

`config.py` line 39 raises `EnvironmentError`. In Python 3, `EnvironmentError is OSError` evaluates to `True`; it is a deprecated alias retained for Python 2 compatibility. The traceback therefore prints `OSError`, which reads as an I/O or filesystem fault. The message body is accurate, but the exception type points a reader away from the actual problem, which is configuration.

---

## Contributing factors

These are design properties of the repository that turned a one-time setup gap into a repeating hard failure.

| # | Factor | Evidence |
| --- | --- | --- |
| 1 | The workflow has two cron schedules, `0 13 * * *` and `0 21 * * *`, and is now merged to `main`, so it fails twice per day until the secrets exist or the fix lands. | `.github/workflows/twitter-agent.yml` lines 4 to 8. See Scheduling status below. |
| 2 | There is no preflight check. The `Run NORMA agent` step goes straight to `run: python main.py`, so a missing-configuration state is discovered only by crashing. | `.github/workflows/twitter-agent.yml` lines 48 to 59 |
| 3 | The agent cannot signal "not configured yet" separately from "genuinely broken". Both produce exit code 1 and a red build, so the signal carries no diagnostic value and invites the failure to be ignored. | `agent/main.py`, `agent/config.py` |
| 4 | The repository already has the better convention and the Twitter agent does not use it. `prophetx/smoke.py` documents and implements exit `0` = worked, `1` = a call failed, `2` = not configured, and prints `NOT CONFIGURED: ...` rather than raising. The Twitter agent predates that convention and was never brought in line. | `prophetx/smoke.py` lines 13 to 17 and 32 to 36 |

### Scheduling status

An earlier draft of this report recorded that `twitter-agent.yml` existed only on the working branch, which would have meant the cron was not yet firing. **That is no longer true.** Pull request #1 was merged while this report was being written:

```
$ git log origin/main --format='%h %ad %s' --date=short -2
b8d8e25 2026-07-31 Merge pull request #1 from Bigtimedee/claude/norma-twitter-publishing-ViyCc
744dfac 2026-07-31 Add PR template and ProphetX PR description

$ git merge-base --is-ancestor 744dfac origin/main && echo merged
merged

$ git ls-tree -r --name-only origin/main | grep twitter-agent
.github/workflows/twitter-agent.yml
```

`origin/main` now contains `.github/workflows/twitter-agent.yml` and the whole `agent/` tree. `main` is the branch the pull request targeted as its base, which GitHub pre-selects from the repository default.

The practical consequence: **the two cron schedules are live on the default branch and the job is failing on each scheduled run** until the secrets are added or the fix below is merged. Factor 1 should be read as actively recurring, not pending.

One qualification, stated because it was not directly verifiable: we confirmed `main` is the merge target but could not query the GitHub API to confirm it is formally the default branch (`refs/remotes/origin/HEAD` is unset in this clone). If some other branch is the default, the cron fires from that branch instead. Anyone with repository access can confirm on the repository home page.

---

## Platform note

The incident was reported to us as a Railway failure. The evidence indicates the failing job is GitHub Actions:

- The traceback paths are prefixed `/home/runner/work/norma-site/norma-site/`, the GitHub Actions runner checkout convention (`/home/runner/work/<repo>/<repo>/`).
- `Error: Process completed with exit code 1.` is GitHub Actions step-failure output.
- The job title `NORMA Twitter Agent / post` matches `name: NORMA Twitter Agent` and job id `post` in `.github/workflows/twitter-agent.yml` exactly.

No reference to Railway appears anywhere in the repository. This is worth stating only because it changes where the fix goes: the credentials belong in GitHub repository secrets, and setting them in a Railway project would not affect this job.

---

## Resolution

### Operator action, required, not yet done

Add all seven secrets in the GitHub repository under **Settings -> Secrets and variables -> Actions -> New repository secret**:

| Secret | Source |
| --- | --- |
| `TWITTER_API_KEY` | X/Twitter developer portal |
| `TWITTER_API_SECRET` | X/Twitter developer portal |
| `TWITTER_ACCESS_TOKEN` | X/Twitter developer portal |
| `TWITTER_ACCESS_TOKEN_SECRET` | X/Twitter developer portal |
| `TWITTER_BEARER_TOKEN` | X/Twitter developer portal |
| `ANTHROPIC_API_KEY` | console.anthropic.com/settings/keys |
| `ODDS_API_KEY` | the-odds-api.com |

Names must match exactly; the workflow reads them by these names. `.env.example` documents the same set for local runs.

### Code changes, implemented

These make the failure mode legible and stop it recurring. They do **not** substitute for adding the secrets: with the fix in place and no secrets, the agent still posts nothing, it just says so clearly instead of failing the build.

| File | Change |
| --- | --- |
| `agent/config.py` | Add a `missing_env()` classmethod returning the list of missing variable names without raising, so callers can inspect configuration state instead of catching an exception. Replace the raised `EnvironmentError` with an explicit `ConfigurationError`, removing the misleading `OSError` label. |
| `agent/main.py` | When configuration is missing, log an actionable message naming the missing variables and where to set them, then exit with code 78 (`EX_CONFIG`, the BSD sysexits convention for a configuration error) instead of surfacing an unhandled traceback. |
| `.github/workflows/twitter-agent.yml` | Add a preflight step that checks whether the secrets are present. If absent, log a notice stating what to add and where, and end the job without failing the build. If present, proceed as now. This converts a recurring red build into an explicit, quiet, self-explaining skip. |
| `tests/test_agent_config.py` | Tests covering missing, partial, and complete configuration. |

### Behaviour after the fix, verified

Same command that produced the incident traceback, run against the fixed code with all seven variables still unset:

```
INFO  Starting NORMA agent | post_type=app_highlight
ERROR  NORMA agent is not configured - nothing was posted.
ERROR
ERROR  Missing 7 of 7 required secrets:
ERROR    TWITTER_API_KEY                from X/Twitter developer portal
ERROR    TWITTER_API_SECRET             from X/Twitter developer portal
ERROR    TWITTER_ACCESS_TOKEN           from X/Twitter developer portal
ERROR    TWITTER_ACCESS_TOKEN_SECRET    from X/Twitter developer portal
ERROR    TWITTER_BEARER_TOKEN           from X/Twitter developer portal
ERROR    ANTHROPIC_API_KEY              from console.anthropic.com/settings/keys
ERROR    ODDS_API_KEY                   from the-odds-api.com
ERROR
ERROR  Set them here: GitHub repository -> Settings -> Secrets and variables -> Actions -> New repository secret
ERROR  Names must match exactly. An unset secret becomes an empty string, which counts as missing.
exit code: 78
```

No traceback, no `OSError`, exit 78 instead of 1, and the fix location is named in the output. The workflow preflight turns this into a skip with a job-summary notice rather than a red build.

Test coverage: `tests/test_agent_config.py`, 13 tests, all passing. Full suite 38 passing. The preflight shell logic was simulated in both states (all secrets set, none set) and produces the correct `configured` output each way.

### Verification, after secrets are added

Trigger the workflow manually via `workflow_dispatch` (input `post_type`) and confirm the run reaches the posting steps and logs a tweet URL. Until then the preflight will skip the job, which is the intended behaviour and not a regression.

---

## Lessons learned

1. **A missing-configuration state is not a failure state, and the two must not share an exit code.** `prophetx/smoke.py` already encodes this in the same repository. Every entry point that reads credentials should adopt the same distinction so that "we have not set this up yet" never presents as "this is broken".
2. **Unset GitHub secrets are empty strings, not absent variables.** Any check written as `if "KEY" not in os.environ` would pass silently in Actions and fail later with a worse error. Configuration checks in this repo must test for emptiness, which `from_env()` does correctly today and the replacement preserves.
3. **Do not raise `EnvironmentError`.** It is an alias for `OSError` in Python 3 and mislabels configuration problems as I/O faults in every traceback. Use a domain-specific exception type.
4. **A scheduled job should validate its inputs before doing work.** A preflight step costs seconds and turns a twice-daily crash into a single readable notice.
5. **Error output should name the fix location.** The original message named the missing variables but not where to set them, so acting on it required reading the workflow file. The replacement names Settings -> Secrets and variables -> Actions directly.
6. **A workflow committed with credentials that were never provisioned is an incomplete change.** Landing a scheduled job and provisioning its secrets should happen together, or the job should ship disabled.

---

## Open items

| # | Item | Owner | Resolved by |
| --- | --- | --- | --- |
| 1 | Add the seven repository secrets (see Resolution). Nothing else unblocks posting. | Repository admin | Secrets present in Settings -> Secrets and variables -> Actions |
| 2 | Land the in-progress code changes to `config.py`, `main.py`, the workflow, and the new test file. | Engineer | Merged and `Tests` green |
| 3 | Confirm `main` is formally the repository default branch. `twitter-agent.yml` is confirmed present on `main`; the cron therefore fires from it if `main` is the default. | Repository admin | The branch shown on the repository home page |
| 4 | Rotate any of the seven credentials that were shared outside a secret store while debugging, if that happened. Unknown to us. | Repository admin | Confirmation, or rotation |
| 5 | Consider bringing other credential-reading entry points in `agent/` in line with the `prophetx/smoke.py` exit-code convention. | Engineer | Follow-up issue |

<a id="verification-gap"></a>

### Verification gap

GitHub API access for this repository returns HTTP 403: "GitHub access is not enabled for this session. An org admin must connect the Claude GitHub App for this organization."

Consequently we could **not** retrieve, and have **not** estimated:

- Actions run history for `NORMA Twitter Agent`
- Run IDs, including the run that produced the captured output
- The timestamp of the first failure
- The total number of failed runs, or any cost associated with them
- Whether the schedule has been auto-disabled for repository inactivity

Anyone with repository access can close this gap from the Actions tab, filtered to the `NORMA Twitter Agent` workflow. If those figures are needed for reporting, retrieve them there rather than inferring them from this document.

---

## Appendix: reproduction

From a clean checkout of `agent/` at commit `744dfac`, with the seven variables unset:

```
cd agent
env -u TWITTER_API_KEY -u TWITTER_API_SECRET -u TWITTER_ACCESS_TOKEN \
    -u TWITTER_ACCESS_TOKEN_SECRET -u TWITTER_BEARER_TOKEN \
    -u ANTHROPIC_API_KEY -u ODDS_API_KEY \
    python3 main.py app_highlight
```

Produces the traceback quoted under Root cause with matching frames and line numbers, and exits 1. Confirms the failure originates in repository code and configuration, not in the runner or the platform.
