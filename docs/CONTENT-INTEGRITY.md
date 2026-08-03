# Content integrity rules and audit record

Standing rules for what may be written into this repository, and the record of
the 2026-08-01 audit that produced them.

---

## 1. The rules

### 1.1 Never invent an identifier

Domains, email addresses, URLs, company names, personal names, physical
addresses, phone numbers, account handles, and legal entity names are **facts
about the world**. They are either supplied by NORMA, read from an
authoritative source and cited, or **left as an explicit bracketed placeholder**
such as `[NORMA's website URL]`.

A plausible-looking identifier is worse than a blank, because a blank gets
filled in and a plausible one gets shipped.

### 1.2 Never name a private individual

Do not write a person's name into this repository unless they are a NORMA team
member being credited deliberately. This applies even when the name was
encountered in a fetched page, an HTTP response, or a document. There is no
engineering purpose served by it, and being incidentally readable somewhere does
not make republishing it appropriate.

### 1.3 Do not characterize third parties from a fetch

Outbound requests from the working environment pass through a proxy. What comes
back is not reliable evidence about who operates a domain or what a third party
does. Never write "domain X belongs to company Y" or "X is a different business"
on the strength of a fetch.

Permitted: "`example.com` returned HTTP 200 at `<time>`." That is an
observation about a request. Anything about ownership or identity requires a
source that establishes it, or it is left unstated.

### 1.4 Legal documents are read-only without explicit instruction

`privacy-policy.html` and `terms-of-service.html` are not edited to fix a
perceived problem. Contact details, effective dates, and disclosures are
business facts. Raise the concern; do not "correct" the document.

### 1.5 Scope every claim to its evidence

Absence in this repository is not absence in the world. State what was checked:
"nothing in `agent/` references Supabase" is supportable; "NORMA does not use
Supabase" is not.

### 1.6 Numbers are cited or absent

No revenue figures, user counts, conversion rates, timelines, valuations, or
percentages unless each is either a measurement taken here (with the command
shown) or a citation to a named source. Never an estimate presented as a fact.

---

## 2. Audit performed 2026-08-01

Scope: every tracked file. Searched for email addresses, URLs and domains,
phone-number and street-address patterns, personal names, and third-party
characterizations.

### 2.1 Removed

| Item | Where | Why |
| --- | --- | --- |
| Two personal names quoted from an HTML comment | `docs/tiktok-resubmission-plan.md` | Violates 1.2. Named private individuals with no engineering purpose. Removed with the surrounding characterization. |
| "serves a login page titled …", "a different company", "an unrelated AI analytics company" | `docs/tiktok-resubmission-plan.md` | Violates 1.3. Asserted third-party identity on the strength of proxied fetches. |
| "a live site belonging to an unrelated analytics company, and `norma-app.com` is likewise a different business" | `agent/media_generator.py` comment | Violates 1.3. Replaced with the verifiable point: the domain was never confirmed to be NORMA's. |
| `norma-app.com` suggested as the website in an outbound request template | `docs/prophetx/API-ACCESS-REQUEST.md` | Violates 1.1. A domain I had not confirmed, in a document intended to be sent to a third party. Now `[NORMA's website URL]`. |
| `norma.app` printed on every generated game alert card | `agent/media_generator.py` | Violates 1.1. Invented earlier in this project and shipped. Removed in commit `ba34068`; the footer now prints no URL. |

### 2.2 Verified clean

| Check | Result |
| --- | --- |
| `privacy-policy.html`, `terms-of-service.html` | **Byte-identical to commit `9c6b076`**, the repository's first commit. Never modified by this project's work. |
| `privacy@norma-app.com`, `support@norma-app.com` | Present since commit `9c6b076`, dated 2026-03-04. **Author-supplied content, not generated.** Not a finding, and not to be changed without instruction. |
| `index.html` | Every factual claim traced to `privacy-policy.html` or `terms-of-service.html`. Verified programmatically; all 11 checked claims present in source. Carries no contact address and no domain. |
| Phone numbers, street addresses | None anywhere in the repository. |
| Personal names in public-facing files | None. |
| `support@betprophet.co` | From ProphetX's published OpenAPI `info.contact.email`. Cited at each use. |
| `api-ss-sandbox.betprophet.co` | From the OpenAPI `servers` block; confirmed live (returns 401 with the documented error body, not 404). |
| `cfg.example` in tests | RFC 2606 reserved example domain. Correct for a fixture. |

### 2.3 Outstanding — requires your input

| Item | Why it cannot be resolved here |
| --- | --- |
| Whether `norma-app.com` is NORMA's domain and those mailboxes are monitored | A business fact. Rule 1.3 forbids me concluding it from a fetch. |
| Whether NORMA controls a domain suitable for hosting the policies | Same. Needed for the TikTok requirement that URLs be ownership-verified. |

### 2.4 Not in this repository, but published

Three documents were published as artifacts earlier in this project: a social
media strategy, a `$50M` acquisition playbook, and the ProphetX integration
plan. The first two contain **substantial invented material** produced before
these rules existed: audience personas, revenue and ARR figures, conversion
rates, unit economics, and `norma.app` used throughout as NORMA's domain.

They are private to the account holder and are not part of the codebase, so this
audit did not alter them. **They should not be circulated or used as a planning
input.** Say the word and I will retract or rewrite them.

---

## 3. Enforcement

Rules 1.1 through 1.6 are added to the pull request template's compliance
section. The check that matters most:

> Every domain, email address, company name, personal name, and number in this
> change is either supplied by NORMA, cited to a source, or an explicit
> bracketed placeholder. None is invented, and none characterizes a third party
> on the basis of a fetch.
