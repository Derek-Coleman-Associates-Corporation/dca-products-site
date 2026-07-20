# DCA Hardened Images — product site

Static landing pages for the Derek Coleman & Associates Incorporated AWS Marketplace
fleet, served at https://products.dcassociatesgroup.com via GitHub Pages.

- `data/*.json` — product copy, synced from the (private) publishing repo's
  `scripts/publish/products/`. Only products with a non-null `product_id`
  (i.e., actually listed) get pages.
- `generate_site.py` — zero-dependency static generator → `dist/`.
- Deploys on every push to `main` via `.github/workflows/pages.yml`.
- Optional analytics: set the repo Actions variable `GA4_MEASUREMENT_ID`;
  outbound marketplace clicks fire a `marketplace_click` event.

Marketplace buttons currently link to exact-title marketplace search results;
swap to direct `prodview-…` URLs in `generate_site.py` once captured from AMMP.
