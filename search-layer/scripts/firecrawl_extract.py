#!/usr/bin/env python3
"""Firecrawl structured extraction helper.

Uses the current Firecrawl v2 recommendation: /v2/scrape with a JSON format
object, instead of the deprecated /v2/extract endpoint.

Examples:
  python3 firecrawl_extract.py --url https://example.com --prompt "提取公司名称、主营产品、联系方式"
  python3 firecrawl_extract.py --urls u1 u2 --prompt "提取政策名称、申报条件、截止时间"
  python3 firecrawl_extract.py --url https://example.com --prompt "..." --schema-file schema.json
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import firecrawl_client as fc


def _load_urls(args) -> list[str]:
    if args.url:
        return [args.url]
    if args.urls:
        return args.urls
    return [
        line.strip()
        for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _build_json_format(prompt: str, schema: dict | None) -> dict:
    fmt = {"type": "json", "prompt": prompt}
    if schema:
        fmt["schema"] = schema
    return fmt


def _extract_one(url: str, prompt: str, schema: dict | None,
                 timeout: int, include_markdown: bool = False,
                 only_clean_content: bool = False) -> dict:
    formats: list = [_build_json_format(prompt, schema)]
    if include_markdown:
        formats.append({"type": "markdown"})

    payload: dict = {
        "url": url,
        "formats": formats,
    }
    if only_clean_content:
        payload["onlyCleanContent"] = True

    try:
        resp = fc.post("scrape", payload, timeout=timeout)
    except Exception as e:
        return {"url": url, "success": False, "error": str(e)}

    data = resp.get("data") if isinstance(resp, dict) else None
    if not isinstance(data, dict):
        data = {}
    metadata = data.get("metadata") or {}

    return {
        "url": url,
        "success": bool(resp.get("success")) if isinstance(resp, dict) else False,
        "json": data.get("json"),
        "metadata": {
            "title": metadata.get("title") or metadata.get("ogTitle"),
            "description": metadata.get("description") or metadata.get("ogDescription"),
            "sourceURL": metadata.get("sourceURL") or metadata.get("url") or url,
            "statusCode": metadata.get("statusCode"),
            "creditsUsed": metadata.get("creditsUsed"),
            "cacheState": metadata.get("cacheState"),
        },
        "markdown_excerpt": (data.get("markdown") or "")[:1200] if include_markdown else None,
        "raw_response_id": resp.get("id") if isinstance(resp, dict) else None,
        "warnings": resp.get("warnings") if isinstance(resp, dict) else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract structured JSON from URLs with Firecrawl /v2/scrape formats=[json]"
    )
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Single URL to extract from")
    group.add_argument("--urls", nargs="+", help="Multiple URLs to extract from")
    group.add_argument("--urls-file", help="File containing one URL per line")
    ap.add_argument("--prompt", required=True, help="Natural language extraction prompt")
    ap.add_argument("--schema-file", help="Optional JSON schema file for structured extraction")
    ap.add_argument("--include-markdown", action="store_true", help="Also request markdown and include a short excerpt")
    ap.add_argument("--only-clean-content", action="store_true", help="Ask Firecrawl to run extra clean-content pass")
    ap.add_argument("--workers", type=int, default=3, help="Concurrent workers for multiple URLs")
    fc.add_common_args(ap)
    args = ap.parse_args()

    urls = _load_urls(args)
    schema = None
    if args.schema_file:
        schema = json.loads(Path(args.schema_file).read_text(encoding="utf-8"))

    results = []
    if len(urls) == 1:
        results.append(_extract_one(
            urls[0], args.prompt, schema, args.timeout,
            include_markdown=args.include_markdown,
            only_clean_content=args.only_clean_content,
        ))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.workers, len(urls)))) as pool:
            futures = {
                pool.submit(
                    _extract_one,
                    url,
                    args.prompt,
                    schema,
                    args.timeout,
                    args.include_markdown,
                    args.only_clean_content,
                ): url
                for url in urls
            }
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())

    fc.json_dump({
        "mode": "scrape-json-extract",
        "endpoint": "/v2/scrape",
        "urls": urls,
        "count": len(urls),
        "prompt": args.prompt,
        "results": results,
    })


if __name__ == "__main__":
    main()
