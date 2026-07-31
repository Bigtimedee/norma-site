## Summary

<!-- What changed and why. Lead with the reason, not the file list. -->

## Changes

<!-- The notable pieces. A table works well when several files change:
| Path | Purpose |
|------|---------|
-->

## Verification

<!-- How this was checked. Paste real output rather than describing it.

    pip install -r requirements-dev.txt
    python -m pytest tests/ -q
-->

- [ ] Tests pass locally
- [ ] No secrets, tokens, or API keys added to the repo or to `.env.example`
- [ ] `.env.example` updated if new configuration was introduced

## Scheduled jobs and configuration

<!-- Delete this section if the change adds no scheduled job and no new
required configuration.

From the 31 Jul 2026 incident: the Twitter agent workflow was merged with two
cron schedules but no secrets, so it raised an unhandled error and failed the
job on every scheduled run. See
docs/incidents/2026-07-31-twitter-agent-missing-secrets.md.
-->

- [ ] If this adds a **new required** environment variable, it is listed in
      `.env.example` **and** in the code's required-config list, and the error
      message names where to set it
- [ ] If this adds or changes a **scheduled** workflow, missing configuration
      **skips** the run (logs a notice, exits 0 or `78`/`EX_CONFIG`) rather than
      failing the job — a job that cannot succeed yet must not go red on a timer
- [ ] Configuration errors are distinguishable from real failures by exit code,
      and do not raise `EnvironmentError` (it is an alias of `OSError` and reads
      as an I/O fault)
- [ ] A preflight check verifies configuration **before** expensive setup steps
- [ ] Any secret this depends on is either already set in the repository, or
      the PR description names exactly which secrets an operator must add

## Compliance

<!-- Delete this section if the change touches neither of these.

NORMA's Terms of Service state NORMA "does not facilitate, process, or broker
any wagers or bets" and "is not a sportsbook, betting exchange, or gambling
operator." Any change touching sportsbooks, exchanges, or prediction markets
must stay read-only.
-->

- [ ] Read-only: introduces no order placement, deposit, or withdrawal path
- [ ] Privacy policy reviewed — updated if a new third-party service or a new
      category of stored user data was added, unchanged if not

## Notes for the reviewer

<!-- Anything deliberately left out, known limitations, or follow-up work.
     Say what is *not* done as explicitly as what is. -->
