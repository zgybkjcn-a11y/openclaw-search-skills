#!/usr/bin/env python3
"""Shared Firecrawl client helpers for search-layer scripts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests


def find_credentials() -> Path | None:
    script_dir = Path(__file__).resolve().parent
    candidates: list[Path] = []

    for env_name in ("SEARCH_LAYER_CREDENTIALS", "OPENCLAW_SEARCH_CREDENTIALS"):
        if v := os.environ.get(env_name):
            candidates.append(Path(v).expanduser())

    if v := os.environ.get("OPENCLAW_CREDENTIALS_DIR"):
        candidates.append(Path(v).expanduser() / "search.json")

    candidates.extend([
        script_dir.parent / "credentials" / "search.json",
        script_dir.parents[2] / "credentials" / "search.json",
        Path.cwd() / "credentials" / "search.json",
        Path.home() / ".openclaw" / "credentials" / "search.json",
    ])

    seen = set()
    for p in candidates:
        rp = p.resolve() if not p.is_absolute() else p
        key = str(rp)
        if key in seen:
            continue
        seen.add(key)
        if rp.is_file():
            return rp
    return None


def get_firecrawl_config() -> dict:
    """Load Firecrawl config from search.json and environment variables.

    Supported shapes:
    - {"firecrawl": "fc-..."}
    - {"firecrawl": {"apiKey": "fc-...", "apiUrl": "https://api.firecrawl.dev"}}
    - legacy top-level firecrawlApiKey / firecrawlApiUrl
    - env FIRECRAWL_API_KEY / FIRECRAWL_API_BASE / FIRECRAWL_API_URL
    """
    cfg: dict = {}
    cred_path = find_credentials()
    if cred_path:
        try:
            data = json.loads(cred_path.read_text(encoding="utf-8"))
            fc = data.get("firecrawl")
            if isinstance(fc, dict):
                if v := fc.get("apiKey"):
                    cfg["apiKey"] = v
                if v := (fc.get("apiUrl") or fc.get("baseUrl") or fc.get("apiBase")):
                    cfg["apiUrl"] = v
            elif isinstance(fc, str) and fc:
                cfg["apiKey"] = fc
            if v := (data.get("firecrawlApiKey") or data.get("firecrawl_api_key")):
                cfg["apiKey"] = v
            if v := (data.get("firecrawlApiUrl") or data.get("firecrawlApiBase") or data.get("firecrawlBaseUrl")):
                cfg["apiUrl"] = v
        except Exception as e:
            print(f"[firecrawl-client] warning: failed to read credentials: {e}", file=sys.stderr)

    if v := os.environ.get("FIRECRAWL_API_KEY"):
        cfg["apiKey"] = v
    if v := (os.environ.get("FIRECRAWL_API_BASE") or os.environ.get("FIRECRAWL_API_URL")):
        cfg["apiUrl"] = v

    cfg.setdefault("apiUrl", "https://api.firecrawl.dev")
    return cfg


def require_firecrawl_config() -> dict:
    cfg = get_firecrawl_config()
    key = cfg.get("apiKey")
    if not key or key.startswith("YOUR_"):
        raise SystemExit("Firecrawl apiKey is not configured. Set FIRECRAWL_API_KEY, SEARCH_LAYER_CREDENTIALS, OPENCLAW_CREDENTIALS_DIR/search.json, package-local credentials/search.json, or ~/.openclaw/credentials/search.json.")
    return cfg


def endpoint_url(base_url: str | None, endpoint: str) -> str:
    """Resolve base URL to /v2/<endpoint>. endpoint may start with slash."""
    endpoint = endpoint.strip("/")
    parsed = urlparse((base_url or "https://api.firecrawl.dev").rstrip("/"))
    path = parsed.path.rstrip("/")
    suffix = f"/{endpoint}"
    if not path.endswith(suffix):
        if path.endswith("/v2"):
            path = f"{path}{suffix}"
        elif path:
            path = f"{path}/v2{suffix}"
        else:
            path = f"/v2{suffix}"
    return urlunparse(parsed._replace(path=path))


def post(endpoint: str, payload: dict, timeout: int = 60, cfg: dict | None = None) -> dict:
    cfg = cfg or require_firecrawl_config()
    url = endpoint_url(cfg.get("apiUrl"), endpoint)
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {cfg['apiKey']}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def get(endpoint: str, timeout: int = 60, cfg: dict | None = None) -> dict:
    cfg = cfg or require_firecrawl_config()
    url = endpoint_url(cfg.get("apiUrl"), endpoint)
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {cfg['apiKey']}"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()


def coerce_data(response: dict):
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def json_dump(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def parse_formats(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    return [x.strip() for x in value.split(",") if x.strip()]


def add_common_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--timeout", type=int, default=60, help="HTTP timeout seconds")
