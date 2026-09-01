# Deploying to Cloudflare Pages

This is a static site (`index.html` at the repo root), so it needs **no build step**.
Pick whichever route is easier for you.

## Option A — Connect the GitHub repo (recommended, auto-deploys on push)

1. Go to the Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Select this repository (`infindigital/bluediamond-medhub`).
3. Build settings:
   - **Framework preset:** `None`
   - **Build command:** *(leave empty)*
   - **Build output directory:** `/`
4. Choose the production branch (e.g. `main`, or `claude/blue-diamond-staffing-site-sv2rjt` while previewing).
5. **Save and Deploy.** Every push to that branch redeploys automatically, and other branches get preview URLs.

## Option B — Deploy from your machine with Wrangler (one-off)

Requires a Cloudflare account and the CLI. Run locally (not from the Claude sandbox, which
can't reach the Cloudflare API):

```bash
npm install -g wrangler        # or: npx wrangler ...
wrangler login                 # opens a browser to authorize
wrangler pages deploy . --project-name=bluediamond-medhub
```

`wrangler.toml` in this repo already sets `pages_build_output_dir = "."`, so Wrangler
serves the site from the root.

## Notes

- **Tailwind CDN:** the page currently loads Tailwind from `cdn.tailwindcss.com` (the Play
  CDN). It works once deployed, but Tailwind logs a console warning that the Play CDN isn't
  meant for production. For a production build, compile Tailwind to a static stylesheet and
  drop the CDN `<script>`.
- **Images:** the hero/avatar images point at temporary Google-hosted URLs. Replace them with
  your own assets (committed to the repo, e.g. under `/assets`) before going live.
