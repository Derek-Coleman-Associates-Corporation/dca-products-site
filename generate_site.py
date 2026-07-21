#!/usr/bin/env python3
"""Static site generator for products.dcassociatesgroup.com.

Reads the marketplace product configs in data/ (synced from the private
publishing repo — same copy that drives the actual AWS Marketplace listings)
and emits a fully static site into dist/: one landing page per product, an
index, a support page, sitemap and robots. No frameworks, no external
assets; analytics only if GA4_MEASUREMENT_ID is set at build time.
"""

import html
import json
import os
import urllib.parse
from pathlib import Path

BASE_URL = "https://products.dcassociatesgroup.com"
COMPANY = "Derek Coleman & Associates Incorporated"
SUPPORT_EMAIL = "support@dcassociatesgroup.com"
PRICING = [("c7i.xlarge", "4 vCPU / 8 GiB", "$0.46"),
           ("c7i.2xlarge", "8 vCPU / 16 GiB", "$0.92"),
           ("c7i.4xlarge", "16 vCPU / 32 GiB", "$1.84")]
GA4 = os.environ.get("GA4_MEASUREMENT_ID", "").strip()

# Products that had an equivalent image in Bitnami's (now-retired) free catalog.
# slug -> (name Bitnami used for the app, our app display name).
# Only slugs present here AND in data/ (with a product_id) get a
# /bitnami-alternative/<slug>/ landing page.
BITNAMI_APPS = {
    "haproxy": ("HAProxy", "HAProxy"),
    "httpd": ("Apache", "Apache HTTP Server"),
    "kafka": ("Kafka", "Apache Kafka"),
    "keycloak": ("Keycloak", "Keycloak"),
    "mariadb": ("MariaDB", "MariaDB"),
    "memcached": ("Memcached", "Memcached"),
    "nginx": ("NGINX", "NGINX"),
    "postgresql": ("PostgreSQL", "PostgreSQL"),
    "tomcat": ("Tomcat", "Apache Tomcat"),
    "valkey": ("Valkey", "Valkey"),
}
BITNAMI_TRADEMARK_NOTE = ("Bitnami is a trademark of Broadcom, Inc. Used for identification "
                          "only; no affiliation or endorsement implied.")

CSS = """
:root{--bg:#ffffff;--fg:#1a1f24;--muted:#5c6670;--card:#f5f7f9;--accent:#0972d3;
--border:#d9dee3}
@media(prefers-color-scheme:dark){:root{--bg:#0f1418;--fg:#e8edf2;--muted:#94a1ad;
--card:#1a2129;--accent:#54aaff;--border:#2c3640}}
*{box-sizing:border-box}body{margin:0;font:16px/1.6 -apple-system,BlinkMacSystemFont,
"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--fg)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:960px;margin:0 auto;padding:0 20px}
header.site{border-bottom:1px solid var(--border);padding:14px 0}
header.site .wrap{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.brand{font-weight:700;color:var(--fg)}
nav a{margin-left:18px;color:var(--muted)}
h1{font-size:1.7rem;line-height:1.25;margin:1.4em 0 .4em}
h2{font-size:1.15rem;margin:1.6em 0 .5em}
p.lede{color:var(--muted);font-size:1.05rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px;margin:24px 0}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px}
.card h3{margin:0 0 6px;font-size:1.02rem}.card p{margin:0;color:var(--muted);font-size:.9rem}
.btn{display:inline-block;background:var(--accent);color:#fff;padding:10px 18px;border-radius:8px;
font-weight:600;margin:6px 0}.btn:hover{text-decoration:none;opacity:.92}
ul.hl{padding-left:1.2em}ul.hl li{margin:.45em 0}
table{border-collapse:collapse;width:100%;margin:10px 0}
td,th{border:1px solid var(--border);padding:8px 12px;text-align:left;font-size:.95rem}
th{background:var(--card)}
.note{color:var(--muted);font-size:.85rem}
footer{border-top:1px solid var(--border);margin-top:48px;padding:22px 0;color:var(--muted);font-size:.85rem}
pre{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:12px;overflow-x:auto;font-size:.85rem}
"""


def ga_snippet() -> str:
    if not GA4:
        return ""
    gid = html.escape(GA4)
    return (f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>'
            '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}'
            f'gtag("js",new Date());gtag("config","{gid}");'
            'document.addEventListener("click",function(e){var a=e.target.closest("a[data-mp]");'
            'if(a){gtag("event","marketplace_click",{product:a.dataset.mp});}});</script>')


def page(title: str, desc: str, canonical: str, body: str, jsonld: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<style>{CSS}</style>
{jsonld}{ga_snippet()}
</head>
<body>
<header class="site"><div class="wrap">
<a class="brand" href="/">DCA Hardened Images</a>
<nav><a href="/">Products</a><a href="/support/">Support</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<p>{COMPANY} &middot; <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p>
<p>All product names, logos, and brands are property of their respective owners and are used for
identification purposes only. Use does not imply endorsement. Each page notes the relevant
open-source license; the underlying open-source software remains free.</p>
</div></footer>
</body>
</html>"""


def marketplace_url(p: dict) -> str:
    q = urllib.parse.quote(p["product_title"])
    return f"https://aws.amazon.com/marketplace/search/results?searchTerms={q}"


def product_jsonld(p: dict, canonical: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": p["product_title"],
        "operatingSystem": "Amazon Linux 2023",
        "applicationCategory": "DeveloperApplication",
        "description": p["short_description"],
        "url": canonical,
        "provider": {"@type": "Organization", "name": COMPANY},
        "offers": {
            "@type": "AggregateOffer",
            "priceCurrency": "USD",
            "lowPrice": "0.46",
            "highPrice": "1.84",
            "description": "Hourly usage pricing on AWS Marketplace, billed per running instance hour.",
        },
    }
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


def product_page(slug: str, p: dict) -> str:
    canonical = f"{BASE_URL}/{slug}/"
    mp = marketplace_url(p)
    hl = "".join(f"<li>{html.escape(h)}</li>" for h in p["highlights"])
    paras = "".join(f"<p>{html.escape(par)}</p>" for par in p["long_description"].split("\n\n"))
    rows = "".join(f"<tr><td>{t}</td><td>{s}</td><td>{pr}/hr</td></tr>" for t, s, pr in PRICING)
    rec = p.get("recommended_instance_type", "c7i.xlarge")
    body = f"""
<h1>{html.escape(p["product_title"])}</h1>
<p class="lede">{html.escape(p["short_description"])}</p>
<p><a class="btn" data-mp="{slug}" href="{mp}" rel="noopener">View on AWS Marketplace</a></p>
<h2>Why this image</h2>
<ul class="hl">{hl}</ul>
<h2>About</h2>
{paras}
<h2>Pricing (hourly usage, AWS Marketplace)</h2>
<table><tr><th>Instance type</th><th>Size</th><th>Software price</th></tr>{rows}</table>
<p class="note">Recommended: {rec}. AWS infrastructure charges are separate and billed by AWS.
Charges stop when instances are terminated. No subscription, no minimum.</p>
<h2>Getting started</h2>
<pre>{html.escape(p["usage_instructions"])}</pre>
<h2>Support</h2>
<p>Email <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a> — business-day response. Covers
image operation, the hardening baseline, and launch issues. See <a href="/support/">support</a>.</p>
"""
    return page(f'{p["product_title"]} — DCA Hardened Images',
                p["short_description"][:300], canonical, body,
                product_jsonld(p, canonical))


def bitnami_page(slug: str, p: dict) -> str:
    bn, app = BITNAMI_APPS[slug]
    canonical = f"{BASE_URL}/bitnami-alternative/{slug}/"
    mp = marketplace_url(p)
    title = f"Bitnami {bn} Alternative — Hardened {app} by DC Associates Group"
    valkey_note = ""
    if slug == "valkey":
        valkey_note = ("<p>Valkey is the Linux Foundation open-source fork of Redis, so this "
                       "image is also a common landing point for teams migrating from the "
                       "Bitnami Redis image.</p>")
    body = f"""
<h1>{html.escape(title)}</h1>
<p class="lede">A security-hardened, actively maintained {html.escape(app)} image for AWS,
published by {COMPANY} — a maintained path forward for teams moving off the retired free
Bitnami {html.escape(bn)} image.</p>
<p><a class="btn" data-mp="{slug}-bitnami-alt" href="{mp}" rel="noopener">View on AWS Marketplace</a></p>
<h2>Why Bitnami users are migrating</h2>
<p>In August 2025, Broadcom moved Bitnami's free image catalog to its Bitnami Secure Images
program, and the legacy free catalog was subsequently removed from Docker Hub. Existing
deployments keep running, but images from the old free channel no longer receive updates
there. Teams that relied on the free Bitnami {html.escape(bn)} image are therefore looking
for actively maintained, security-focused alternatives.</p>{valkey_note}
<h2>What our hardened {html.escape(app)} image provides</h2>
<ul class="hl">
<li>CIS-aligned hardening baseline: minimal package set, SSH key-only access with root login
disabled, IMDSv2 enforced, firewall enabled by default.</li>
<li>CVE-patched monthly: images are rebuilt, scanned for HIGH and CRITICAL CVEs, and
republished on a monthly cadence, so new launches start from a currently patched base.</li>
<li>Zero default credentials: no passwords anywhere in the image; keys are generated per
instance where needed.</li>
<li>Deployed in your own AWS account: launched from AWS Marketplace into your VPC on EC2
instances you control. Hourly usage pricing; charges stop when you terminate.</li>
</ul>
<h2>Migration notes</h2>
<ul class="hl">
<li>Configuration paths may differ: Bitnami images install under <code>/opt/bitnami</code>,
while this image uses the standard distribution layout on Amazon Linux 2023. See the
getting-started section on the <a href="/{slug}/">{html.escape(app)} product page</a> for
exact paths.</li>
<li>Migrate data with the application's standard tooling (dump/restore, replication, or file
copy, per the {html.escape(app)} documentation).</li>
<li>Services are systemd-managed and start on boot; validate your configuration on a fresh
instance before cutting over production traffic.</li>
</ul>
<h2>Links</h2>
<ul class="hl">
<li><a data-mp="{slug}-bitnami-alt" href="{mp}" rel="noopener">AWS Marketplace listing</a></li>
<li><a href="/{slug}/">{html.escape(p["product_title"])}</a> — full product details, pricing,
and getting started.</li>
<li><a href="/support/">Support</a> — included in the hourly software price.</li>
</ul>
<p class="note">{BITNAMI_TRADEMARK_NOTE}</p>
"""
    desc = (f"Bitnami {bn} alternative: security-hardened {app} image for AWS from {COMPANY}. "
            "CIS-aligned baseline, monthly CVE patching, zero default credentials, "
            "deployed in your own AWS account.")
    return page(title, desc, canonical, body)


def index_page(products: dict) -> str:
    cards = ""
    for slug, p in sorted(products.items(), key=lambda kv: kv[1]["product_title"]):
        short = p["short_description"].split("support. ", 1)[-1]
        cards += (f'<a class="card" href="/{slug}/"><h3>{html.escape(p["product_title"])}</h3>'
                  f'<p>{html.escape(short[:150])}…</p></a>')
    bn_links = "".join(
        f'<li><a href="/bitnami-alternative/{slug}/">Bitnami {html.escape(bn)} alternative</a></li>'
        for slug, (bn, _app) in sorted(BITNAMI_APPS.items(), key=lambda kv: kv[1][0].lower())
        if slug in products)
    bitnami_section = ""
    if bn_links:
        bitnami_section = f"""<h2 id="bitnami">Migrating from Bitnami?</h2>
<p>In August 2025, Broadcom moved Bitnami's free image catalog to Bitnami Secure Images, and the
legacy free catalog was subsequently removed from Docker Hub. If you ran Bitnami images, we publish
hardened, actively maintained equivalents:</p>
<ul class="hl">{bn_links}</ul>
<p class="note">{BITNAMI_TRADEMARK_NOTE}</p>"""
    body = f"""
<h1>Security-hardened open-source server images for AWS</h1>
<p class="lede">Production-ready AMIs on Amazon Linux 2023: minimal package set, SSH key-only
access, IMDSv2-only, no default passwords anywhere, rebuilt and vulnerability-scanned on a
regular cadence. Hourly usage pricing on AWS Marketplace — no subscriptions, no lock-in.</p>
<div class="grid">{cards}</div>
<h2>The hardening baseline, on every image</h2>
<ul class="hl">
<li>Minimal package footprint; only what the application needs.</li>
<li>SSH key-only access — password authentication disabled, root login disabled.</li>
<li>IMDSv2 enforced; services bound to loopback or firewalled until you deliberately expose them.</li>
<li>No default credentials of any kind; keys are generated per instance where needed.</li>
<li>Rebuilt, scanned for HIGH and CRITICAL CVEs, and republished on a regular cadence.</li>
</ul>
{bitnami_section}
"""
    return page("DCA Hardened Images — security-hardened open-source AMIs for AWS Marketplace",
                "Production-ready, security-hardened open-source server images for AWS: "
                "web servers, databases, caches, proxies and more. Hourly pricing on AWS Marketplace.",
                f"{BASE_URL}/", body)


def support_page() -> str:
    body = f"""
<h1>Support</h1>
<p class="lede">Support for every DCA hardened image is included in the hourly software price.</p>
<h2>How to reach us</h2>
<p>Email <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>. We respond on business days
(US Eastern). Include the product name, AWS region, and instance type; never include
credentials or key material.</p>
<h2>What support covers</h2>
<ul class="hl">
<li>Image operation: boot, systemd services, first-boot initialization.</li>
<li>The hardening baseline: SSH policy, firewall defaults, IMDSv2, service bind policy.</li>
<li>Launch issues: 1-Click and EC2 console launches, security-group recommendations.</li>
</ul>
<p>Application-level engineering (query tuning, cluster design, custom configuration) is outside
image support scope.</p>
<h2>Security reports</h2>
<p>Report a suspected vulnerability in any image to
<a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a> with subject "SECURITY". Images are rebuilt,
scanned for HIGH and CRITICAL CVEs, and republished on a regular cadence; verified reports are
prioritized into the next rebuild.</p>
<h2>Refunds</h2>
<p>Usage-based hourly billing; charges stop when instances are terminated. Contact
<a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a> for billing questions.</p>
"""
    return page("Support — DCA Hardened Images",
                "Support for DCA hardened images on AWS Marketplace: email support, "
                "business-day response, security reports, refund policy.",
                f"{BASE_URL}/support/", body)


def main() -> None:
    root = Path(__file__).parent
    dist = root / "dist"
    products = {}
    for f in sorted((root / "data").glob("*.json")):
        p = json.loads(f.read_text())
        if p.get("product_id"):
            products[f.stem] = p

    dist.mkdir(exist_ok=True)
    (dist / "index.html").write_text(index_page(products))
    (dist / "404.html").write_text(page("Not found — DCA Hardened Images", "Page not found.",
                                        f"{BASE_URL}/", "<h1>Page not found</h1>"
                                        '<p><a href="/">Browse all products</a></p>'))
    for slug, p in products.items():
        d = dist / slug
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(product_page(slug, p))
    bn_slugs = sorted(s for s in BITNAMI_APPS if s in products)
    for slug in bn_slugs:
        d = dist / "bitnami-alternative" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(bitnami_page(slug, products[slug]))
    d = dist / "support"
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text(support_page())

    urls = ([f"{BASE_URL}/", f"{BASE_URL}/support/"]
            + [f"{BASE_URL}/{s}/" for s in sorted(products)]
            + [f"{BASE_URL}/bitnami-alternative/{s}/" for s in bn_slugs])
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    (dist / "sitemap.xml").write_text(sitemap)
    (dist / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")
    (dist / "CNAME").write_text("products.dcassociatesgroup.com\n")
    print(f"generated {len(products)} product pages + {len(bn_slugs)} bitnami-alternative pages "
          "+ index/support/sitemap into dist/")


if __name__ == "__main__":
    main()
