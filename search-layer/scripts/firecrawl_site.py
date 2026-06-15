#!/usr/bin/env python3
"""Firecrawl site mapping/crawling helper.

Examples:
  python3 firecrawl_site.py map https://example.com --limit 50
  python3 firecrawl_site.py crawl https://example.com --limit 20
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import firecrawl_client as fc


def _list_arg(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def run_map(args) -> None:
    payload = {"url": args.url}
    if args.limit:
        payload["limit"] = args.limit
    if args.search:
        payload["search"] = args.search
    if args.sitemap is not None:
        payload["sitemap"] = args.sitemap
    if args.include_subdomains:
        payload["includeSubdomains"] = True
    try:
        resp = fc.post("map", payload, timeout=args.timeout)
    except Exception as e:
        print(f"[firecrawl-site map] error: {e}", file=sys.stderr)
        raise SystemExit(1)
    data = fc.coerce_data(resp)
    urls = []
    if isinstance(data, list):
        urls = data
    elif isinstance(data, dict):
        urls = data.get("links") or data.get("urls") or data.get("data") or []
    fc.json_dump({"mode": "map", "url": args.url, "count": len(urls) if isinstance(urls, list) else None, "urls": urls, "response": resp})


def run_crawl(args) -> None:
    payload = {
        "url": args.url,
        "limit": args.limit,
        "scrapeOptions": {"formats": _list_arg(args.formats) or ["markdown"]},
    }
    includes = _list_arg(args.include)
    excludes = _list_arg(args.exclude)
    if includes:
        payload["includePaths"] = includes
    if excludes:
        payload["excludePaths"] = excludes
    if args.max_depth is not None:
        payload["maxDepth"] = args.max_depth
    if args.allow_backward_links:
        payload["allowBackwardLinks"] = True
    if args.allow_external_links:
        payload["allowExternalLinks"] = True

    try:
        resp = fc.post("crawl", payload, timeout=args.timeout)
    except Exception as e:
        print(f"[firecrawl-site crawl] error: {e}", file=sys.stderr)
        raise SystemExit(1)

    out = {"mode": "crawl", "url": args.url, "submitted": resp}
    crawl_id = None
    if isinstance(resp, dict):
        crawl_id = resp.get("id") or (resp.get("data") or {}).get("id") if isinstance(resp.get("data"), dict) else None
    if args.wait and crawl_id:
        status_resp = None
        deadline = time.time() + args.wait_timeout
        while time.time() < deadline:
            try:
                status_resp = fc.get(f"crawl/{crawl_id}", timeout=args.timeout)
            except Exception as e:
                out["status_error"] = str(e)
                break
            status = status_resp.get("status") if isinstance(status_resp, dict) else None
            if status in {"completed", "failed", "cancelled", "canceled"}:
                break
            time.sleep(args.poll_interval)
        out["status"] = status_resp
    elif args.wait and not crawl_id:
        out["warning"] = "crawl id not found; cannot wait for status"

    fc.json_dump(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Firecrawl map/crawl helper for site research")
    sub = ap.add_subparsers(dest="command", required=True)

    map_ap = sub.add_parser("map", help="Map website URLs via Firecrawl /v2/map")
    map_ap.add_argument("url")
    map_ap.add_argument("--limit", type=int, default=100)
    map_ap.add_argument("--search", help="Optional search term to filter map results")
    map_ap.add_argument("--sitemap", action=argparse.BooleanOptionalAction, default=None)
    map_ap.add_argument("--include-subdomains", action="store_true")
    fc.add_common_args(map_ap)

    crawl_ap = sub.add_parser("crawl", help="Submit a crawl job via Firecrawl /v2/crawl")
    crawl_ap.add_argument("url")
    crawl_ap.add_argument("--limit", type=int, default=20)
    crawl_ap.add_argument("--formats", default="markdown", help="Comma-separated scrape formats")
    crawl_ap.add_argument("--include", help="Comma-separated include paths/patterns")
    crawl_ap.add_argument("--exclude", help="Comma-separated exclude paths/patterns")
    crawl_ap.add_argument("--max-depth", type=int)
    crawl_ap.add_argument("--allow-backward-links", action="store_true")
    crawl_ap.add_argument("--allow-external-links", action="store_true")
    crawl_ap.add_argument("--wait", action="store_true", help="Poll crawl status until completed/failed or timeout")
    crawl_ap.add_argument("--wait-timeout", type=int, default=180)
    crawl_ap.add_argument("--poll-interval", type=float, default=5)
    fc.add_common_args(crawl_ap)

    args = ap.parse_args()
    if args.command == "map":
        run_map(args)
    elif args.command == "crawl":
        run_crawl(args)


if __name__ == "__main__":
    main()
