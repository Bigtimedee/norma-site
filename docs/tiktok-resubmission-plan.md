# TikTok app review — resubmission plan

**App ID:** 7646062068575160341
**Date:** 2026-08-01
**Status:** Blocking defects found and fixed in this repository. Two inputs still required from you (section 6).

---

## 1. What I could and could not see

`https://developers.tiktok.com/app/7646062068575160341/pending` returned **HTTP 401 Unauthorized**. That page is behind your developer account login, so **I have not seen the rejection reason**. Nothing in this plan claims to know what the reviewer wrote.

TikTok's own FAQ states that rejected applicants should consult "Review comments" in their app history for the specific feedback, so the reason exists and is visible to you.

What follows is therefore not a response to the stated rejection. It is an audit of NORMA's submission surfaces against TikTok's **published** requirements, which found defects that would fail review regardless of what the reviewer wrote.

---

## 2. TikTok's published requirements

Quoted from [TikTok Developer Guidelines](https://developers.tiktok.com/doc/our-guidelines-developer-guidelines):

> - "**Verify ownership of all configurations with a URL, including your Privacy Policy, Terms of Service, and more.**"
> - "Set an accurate description, title, and icon for your app."
> - "Disclose your app's Terms of Service and Privacy Policy."
> - "Make sure your app is functioning during our review process."
> - "Providing fake or incomplete data may lead to the rejection of your app and delays in your integration."
> - "For incomplete apps, beta or development versions, and test versions, you are encouraged to use Sandbox mode."

From the [App Review FAQ](https://developers.tiktok.com/doc/getting-started-faq):

> - "App review may take several days to two weeks after submission."
> - Mobile apps must "be available in the Apple and/or Google Play App Stores".

The first requirement is the one that fails today.

---

## 3. Audit findings

Every result below was measured on 2026-08-01, not inferred.

| URL | HTTP | What is actually served |
| --- | --- | --- |
| `bigtimedee.github.io/norma-site/privacy-policy.html` | 200 | NORMA's real privacy policy |
| `bigtimedee.github.io/norma-site/terms-of-service.html` | 200 | NORMA's real terms |
| `bigtimedee.github.io/norma-site/` | **404** | nothing — no index page existed |
| `norma-app.com/` | 200 | **"Norma - Report Writing Software"** login page |
| `norma-app.com/privacy-policy.html` | 200 | the same report-writing page, not NORMA's policy |
| `norma-app.com/this-path-does-not-exist-12345` | 200 | the same page again — the site soft-404s every path |
| `norma.app/` | 200 | **a different company**: "AI Powered Analytics… Rebuild your Data Stack" |

### Finding 1 — the contact domain in both legal documents is not NORMA's (critical)

`privacy-policy.html` directs users to `privacy@norma-app.com` and `terms-of-service.html` to `support@norma-app.com`.

`norma-app.com` serves a login page titled "Norma - Report Writing Software", carrying the HTML comment `Developed by Ruben Pena IV, for Norma Salazar. 1/4/2024` and a "© 2026 Report Writing Software" notice. It returns HTTP 200 for every path, including paths that cannot exist.

Whatever the registration status of that domain, the operative fact for review is this: **a TikTok reviewer who checks NORMA's stated contact address encounters a different company's product.** That is a direct failure of "Verify ownership of all configurations with a URL."

I have **not** changed these addresses. They are contact details in live legal documents and I do not know the correct replacement. See section 6.

### Finding 2 — the site root returned 404 (fixed)

The only working NORMA URLs were the two policy pages. `bigtimedee.github.io/norma-site/` had no index page. A reviewer navigating up from a policy URL, which is a normal verification step, would have hit a 404 and found no evidence the app exists.

### Finding 3 — generated marketing images printed a third party's domain (fixed)

`agent/media_generator.py` rendered the footer `"Track every alert on NORMA · norma.app"` onto every game alert card the social agent produces. `norma.app` is a live site belonging to an unrelated AI analytics company.

This was my error: I invented that domain earlier in this project and it reached committed code. Had the agent posted, every image would have directed viewers to another business.

### Finding 4 — neither legal document mentions TikTok (not fixed, blocked)

`privacy-policy.html` section 3 lists third-party services: Supabase, ESPN, SportsDataIO, Sportradar, The Odds API, Kalshi, Polymarket, Expo Push. **TikTok appears nowhere in either document.**

TikTok requires disclosure of the integration. Writing that disclosure requires knowing which TikTok products and scopes the app requested, and what data crosses the boundary. I will not draft privacy-policy text describing data flows I have not verified. See section 6.

### Finding 5 — app store availability (unverified)

TikTok's FAQ requires mobile apps to be "available in the Apple and/or Google Play App Stores". I have no way to confirm NORMA's store listings from here, and none of the reachable NORMA pages link to them. Flagged, not assumed.

---

## 4. What I changed

| Change | File | Why |
| --- | --- | --- |
| Added a real site index | `index.html` | Fixes Finding 2. Describes the app accurately, states what NORMA is and is not, and links both legal documents, satisfying "Set an accurate description" and "Disclose your app's Terms of Service and Privacy Policy". |
| Removed the third-party domain from generated images | `agent/media_generator.py` | Fixes Finding 3. The footer now reads "Track every alert on NORMA" with no URL. A URL returns only when NORMA controls a domain that resolves to NORMA. |

The new index page deliberately restates the constraint already in NORMA's terms: that NORMA "does not facilitate, process, or broker any wagers or bets" and "is not a sportsbook, betting exchange, or gambling operator". For a reviewer assessing a sports-and-wagering app, having that visible on the landing page rather than only in clause 3 of the terms is worth the space.

It also carries no contact email, because the only address I have is the one in Finding 1.

---

## 5. Known defect, logged not fixed

Generated cards render the sport emoji as a missing-glyph box. Cause: `agent/media_generator.py` draws emoji using Liberation Sans, which has no emoji glyphs. `NotoColorEmoji.ttf` is installed on the build image, so this is fixable, but it is a bitmap (CBDT) font that Pillow will only open at its single native strike size, so the fix means rendering emoji separately and compositing them rather than drawing them as text.

Out of scope for this task and unrelated to TikTok review. Recorded so it is not lost.

---

## 6. What is required from you

Two inputs. Both are things I cannot obtain: the first is behind your login, the second is a business fact.

**1. The rejection text.** From the app's Review comments. Without it, any further change is guesswork, and a resubmission that does not address the stated reason is likely to fail again and consume another review cycle of "several days to two weeks".

**2. The correct contact domain, and the TikTok scopes requested.** Specifically:
   - What email address should replace `privacy@norma-app.com` and `support@norma-app.com`?
   - Does NORMA control a domain that resolves to NORMA? If so, it should host the policies and be the submitted URL, and this repository should get a `CNAME` file so GitHub Pages serves it there.
   - Which TikTok products and scopes did the app request, for example Content Posting API or Login Kit, and which scopes?

Given those, I can finish without further involvement from you: update both legal documents, add the TikTok disclosure section, add the `CNAME` if applicable, and prepare the resubmission text.

---

## 7. Sequence once unblocked

1. Update the contact addresses in `privacy-policy.html` and `terms-of-service.html`, and bump both effective dates.
2. Add a TikTok entry to the privacy policy's Third-Party Services section describing the actual data flow for the requested scopes.
3. Add `CNAME` if a NORMA-controlled domain exists, and re-verify every submitted URL resolves to NORMA.
4. Draft the resubmission description explaining the integration's purpose, which TikTok asks be stated plainly.
5. Re-verify all URLs return 200 and serve NORMA content, then resubmit.

Steps 1 to 4 are mine. Step 5's final submission click is in the developer portal, which returns 401 to me.
