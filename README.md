# norma-site

Support and legal pages for the [NORMA](https://getnorma.app) sports alerts app, served via GitHub Pages.

## Contents

| File | Description |
|---|---|
| `index.html` | Landing / support home page |
| `privacy-policy.html` | Privacy Policy |
| `terms-of-service.html` | Terms of Service |
| `styles.css` | Shared stylesheet |
| `robots.txt` | Crawler directives |
| `sitemap.xml` | Page index for search engines |

## Deployment

Every push to `main` triggers `.github/workflows/deploy-pages.yml`, which deploys the site to GitHub Pages automatically. Use `workflow_dispatch` in the Actions tab for a manual redeploy.

## Updating Legal Documents

Changes to `privacy-policy.html` and `terms-of-service.html` require a review by `@Bigtimedee` (enforced via `.github/CODEOWNERS`). Submit changes via pull request — direct pushes to `main` are not permitted.

When updating a legal document:
1. Update the **Effective Date** at the top of the file to today's date.
2. Update the `<lastmod>` date for the relevant URL in `sitemap.xml`.
3. If the change is material (affects user rights or data handling), plan to notify users through the app.

> **Note:** The Governing Law clause in `terms-of-service.html` currently specifies Texas. Verify this matches the actual jurisdiction of the operating entity before publishing.
