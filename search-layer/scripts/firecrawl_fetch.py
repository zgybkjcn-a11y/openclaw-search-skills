#!/usr/bin/env python3
"""Firecrawl single-page scrape helper (known_url -> clean content).

Examples:
  python3 firecrawl_fetch.py https://example.com/article
  python3 firecrawl_fetch.py https://example.com --formats markdown,links
  python3 firecrawl_fetch.py https://example.com --max-chars 6000 --full
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import firecrawl_client as fc


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Scrape a single known URL via Firecrawl /v2/scrape"
    )
    ap.add_argument("url", help="URL to scrape")
    ap.add_argument("--formats", default="markdown",
                    help="Comma-separated formats: markdown,links,html,summary (default markdown)")
    ap.add_argument("--max-chars", type=int, default=4000,
                    help="Max characters of markdown to include in excerpt (default 4000)")
    ap.add_argument("--full", action="store_true",
                    help="Include full markdown instead of an excerpt")
    ap.add_argument("--only-clean-content", action="store_true",
                    help="Ask Firecrawl to run extra clean-content pass")
    fc.add_common_args(ap)
    args = ap.parse_args()

    fmt_names = fc.parse_formats(args.formats, ["markdown"])
    formats: list = [{"type": name} for name in fmt_names]

    payload: dict = {"url": args.url, "formats": formats}
    if args.only_clean_content:
        payload["onlyCleanContent"] = True

    try:
        resp = fc.post("scrape", payload, timeout=args.timeout)
    except Exception as e:
        print(f"[firecrawl-fetch] error: {e}", file=sys.stderr)
        raise SystemExit(1)

    data = resp.get("data") if isinstance(resp, dict) else None
    if not isinstance(data, dict):
        data = {}
    metadata = data.get("metadata") or {}
    markdown = data.get("markdown") or ""

    out = {
        "mode": "scrape",
        "endpoint": "/v2/scrape",
        "url": args.url,
        "success": bool(resp.get("success")) if isinstance(resp, dict) else False,
        "title": metadata.get("title") or metadata.get("ogTitle"),
        "description": metadata.get("description") or metadata.get("ogDescription"),
        "sourceURL": metadata.get("sourceURL") or metadata.get("url") or args.url,
        "statusCode": metadata.get("statusCode"),
        "creditsUsed": metadata.get("creditsUsed"),
        "word_count": len(markdown.split()) if markdown else 0,
    }
    if markdown:
        if args.full:
            out["markdown"] = markdown
        else:
            out["markdown_excerpt"] = markdown[:args.max_chars]
            out["truncated"] = len(markdown) > args.max_chars
    if "links" in fmt_names:
        out["links"] = data.get("links") or []
    if "summary" in fmt_names and data.get("summary"):
        out["summary"] = data.get("summary")
    if "html" in fmt_names and data.get("html"):
        out["html_chars"] = len(data.get("html") or "")

    fc.json_dump(out)


if __name__ == "__main__":
    main()
