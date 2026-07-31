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
