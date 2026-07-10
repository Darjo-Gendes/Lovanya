#!/usr/bin/env python3
"""Build an Artifact-ready, self-contained derivative of lovanya-app.html.

Claude "Artifacts" run in a strict CSP sandbox that blocks ALL external network
requests (font CDNs included), and the platform wraps the supplied file in its
own <!doctype><html><head></head><body>...</body></html> shell. This script
therefore produces a body-fragment that:

  * inlines every Google Font (as base64 woff2 data: URIs) so no external
    font fetch is needed, and
  * drops the source's document-level tags (<!doctype>/<html>/<head>/<meta>/
    <title>/<link>/</body>/</html>) that the Artifact shell supplies itself.

It is idempotent: downloaded woff2 files are cached under scripts/.font-cache/
and reused on re-run, so editing the source and re-publishing is a one-command
operation. Delete the cache to force a fresh download.

Run:  python.exe lovanya/scripts/build-artifact.py
"""
import base64
import re
import sys
import urllib.parse
from pathlib import Path

import requests

# --- paths -------------------------------------------------------------------
HERE = Path(__file__).resolve().parent                 # .../lovanya/scripts
CACHE = HERE / ".font-cache"
PROTO = HERE.parent / "public" / "prototype"
SRC = PROTO / "lovanya-app.html"
OUT = PROTO / "lovanya-app.artifact.html"

# Google serves woff2 + the correct unicode-range subsets ONLY to modern UAs.
# A default requests/urllib UA gets legacy ttf/eot links, which is wrong.
CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def log(msg):
    print(msg, flush=True)


def read_source():
    # newline='' keeps CRLF intact so retained content is byte-for-byte exact.
    with open(SRC, "r", encoding="utf-8", newline="") as f:
        return f.read()


def parse_font_link(html):
    """Return (family, weight) pairs from the source's Google Fonts <link>.

    A family with no ':wght@' segment (e.g. Parisienne) defaults to weight 400.
    Parsed from the link so a future source edit stays correct without changes.
    """
    m = re.search(
        r'<link[^>]*href="([^"]*fonts\.googleapis\.com/css2[^"]*)"', html, re.I
    )
    if not m:
        sys.exit("ERROR: no Google Fonts css2 <link> found in source")
    href = m.group(1)
    query = href.split("?", 1)[1] if "?" in href else ""

    pairs = []
    for part in query.split("&"):
        if not part.startswith("family="):
            continue
        # unquote_plus turns 'Playfair+Display' -> 'Playfair Display'
        value = urllib.parse.unquote_plus(part[len("family="):])
        if ":wght@" in value:
            family, weights = value.split(":wght@", 1)
            weight_list = [w.strip() for w in weights.split(";") if w.strip()]
        else:
            family, weight_list = value, ["400"]
        for weight in weight_list:
            pairs.append((family.strip(), weight))
    if not pairs:
        sys.exit("ERROR: font <link> parsed but yielded no (family, weight) pairs")
    return href, pairs


def get_woff2(family, weight):
    """Return (bytes, cache_hit) for the plain-Latin woff2 of a family/weight."""
    cache_path = CACHE / f"{family}-{weight}.woff2"
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_bytes(), True

    fam_url = family.replace(" ", "+")
    css_url = (
        f"https://fonts.googleapis.com/css2?family={fam_url}:wght@{weight}"
        "&display=swap"
    )
    resp = requests.get(css_url, headers={"User-Agent": CHROME_UA}, timeout=30)
    resp.raise_for_status()

    # Pick the @font-face whose unicode-range covers basic Latin (U+0000-00FF).
    latin_url = None
    for block in re.findall(r"@font-face\s*{[^}]*}", resp.text):
        ur = re.search(r"unicode-range:\s*([^;]+);", block)
        if ur and ur.group(1).strip().startswith("U+0000-00FF"):
            src = re.search(r"src:\s*url\(([^)]+)\)\s*format\('woff2'\)", block)
            if src:
                latin_url = src.group(1).strip().strip("'\"")
                break
    if not latin_url:
        sys.exit(f"ERROR: no basic-Latin woff2 @font-face for {family} {weight}")

    fbin = requests.get(latin_url, headers={"User-Agent": CHROME_UA}, timeout=30)
    fbin.raise_for_status()
    data = fbin.content
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(data)
    return data, False


def face_rule(family, weight, data):
    b64 = base64.b64encode(data).decode("ascii")
    return (
        f"@font-face {{ font-family: '{family}'; font-style: normal; "
        f"font-weight: {weight}; font-display: swap; "
        f"src: url(data:font/woff2;base64,{b64}) format('woff2'); }}"
    )


def extract_style_block(html):
    """The original <style>...</style> block, byte-for-byte (tags included)."""
    m = re.search(r"<style[^>]*>.*?</style>", html, re.DOTALL | re.I)
    if not m:
        sys.exit("ERROR: no <style> block found in source")
    return m.group(0)


def extract_body_inner(html):
    """Everything between <body...> and </body>, byte-for-byte."""
    m = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL | re.I)
    if not m:
        sys.exit("ERROR: no <body> block found in source")
    return m.group(1)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    html = read_source()

    href, pairs = parse_font_link(html)
    log(f"Font link: {href}")
    log(f"Parsed {len(pairs)} (family, weight) pairs.")

    faces, hits, downloads = [], 0, 0
    for family, weight in pairs:
        data, hit = get_woff2(family, weight)
        faces.append(face_rule(family, weight, data))
        if hit:
            hits += 1
            log(f"  cache-hit : {family} {weight}")
        else:
            downloads += 1
            log(f"  downloaded: {family} {weight}")

    font_style = "<style>\n" + "\n".join(faces) + "\n</style>\n"
    orig_style = extract_style_block(html)
    body_inner = extract_body_inner(html)

    output = font_style + orig_style + body_inner
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write(output)

    size_kb = OUT.stat().st_size / 1024
    log("")
    log("=== SUMMARY ===")
    log(f"Fonts: {hits} cache-hit, {downloads} downloaded ({len(pairs)} total)")
    log(f"@font-face rules emitted: {len(faces)}")
    log(f"Output file: {OUT}")
    log(f"Output size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
