#!/usr/bin/env python3
"""
Remote Ollama connectivity test script.

This script verifies connectivity to a remote Ollama server by:
1) Checking server version:   GET {BASE_URL}/api/version
2) Listing local models:      GET {BASE_URL}/api/tags
3) Sending a chat message:    POST {BASE_URL}/api/chat (using the first available model)

Usage:
  python scripts/connect_ollama_remote.py \
    --base-url https://latho.cbio.uct.ac.za/ollama \
    --api-key  <YOUR_API_KEY>

Environment variables (optional):
  OLLAMA_BASE_URL  (e.g., https://latho.cbio.uct.ac.za/ollama)
  OLLAMA_API_KEY   (token if your reverse proxy requires auth)

Notes:
- Some Ollama deployments are placed behind a reverse proxy that enforces auth.
  If required, this script sends both `Authorization: Bearer <token>` and
  `X-API-Key: <token>` headers. Adjust if your server expects different auth.
- Endpoints are based on official docs:
  - Version:        GET /api/version
  - List models:    GET /api/tags
  - Chat:           POST /api/chat
  Reference: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional

# Try to import requests with a friendly error if missing
try:
    import requests
except Exception as e:
    print("[ERROR] The 'requests' library is required. Install it with:\n  pip install requests\n", file=sys.stderr)
    raise


def build_headers(api_key: Optional[str]) -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if api_key:
        # Common patterns used by reverse proxies protecting Ollama
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-API-Key"] = api_key
    return headers


def http_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
    verify: Any = True,
) -> requests.Response:
    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=json_body,
            timeout=timeout,
            verify=verify,
        )
        return resp
    except requests.exceptions.SSLError as e:
        print(f"[SSL ERROR] {e}", file=sys.stderr)
        raise
    except requests.exceptions.RequestException as e:
        print(f"[NETWORK ERROR] {e}", file=sys.stderr)
        raise


def check_version(base_url: str, headers: Dict[str, str], verify: Any) -> Optional[Dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/version"
    print(f"- GET {url}")
    resp = http_request("GET", url, headers, verify=verify)
    if resp.status_code == 200:
        try:
            data = resp.json()
        except json.JSONDecodeError:
            print("  [FAIL] Non-JSON version response:", resp.text[:300])
            return None
        print("  [OK] Version:", data)
        return data
    else:
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:300]}")
        return None


def list_models(base_url: str, headers: Dict[str, str], verify: Any) -> Optional[list[Dict[str, Any]]]:
    url = f"{base_url.rstrip('/')}/api/tags"
    print(f"- GET {url}")
    resp = http_request("GET", url, headers, verify=verify)
    if resp.status_code == 200:
        try:
            data = resp.json()
        except json.JSONDecodeError:
            print("  [FAIL] Non-JSON list response:", resp.text[:300])
            return None
        # Expected format per docs: { "models": [ {"model": "...", ...}, ... ] }
        models = data.get("models") if isinstance(data, dict) else None
        if isinstance(models, list):
            names = [m.get("model") for m in models if isinstance(m, dict)]
            print(f"  [OK] Found {len(names)} model(s): {names}")
            return models
        print("  [FAIL] Unexpected response format:", data)
        return None
    else:
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:300]}")
        return None


def chat_hello(base_url: str, headers: Dict[str, str], model: str, verify: Any) -> Optional[str]:
    url = f"{base_url.rstrip('/')}/api/chat"
    print(f"- POST {url} (model={model})")
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hello from remote connectivity test. Please reply with: pong"}
        ],
        "stream": False,
    }
    resp = http_request("POST", url, headers, json_body=payload, timeout=120, verify=verify)
    if resp.status_code == 200:
        try:
            data = resp.json()
        except json.JSONDecodeError:
            print("  [FAIL] Non-JSON chat response:", resp.text[:300])
            return None
        # Expected (non-stream) format per docs: { "message": {"role": "assistant", "content": "..."}, ... }
        message = data.get("message") if isinstance(data, dict) else None
        if isinstance(message, dict):
            content = message.get("content")
            print("  [OK] Assistant response:", repr(content))
            return content
        print("  [FAIL] Unexpected chat response format:", data)
        return None
    else:
        print(f"  [FAIL] HTTP {resp.status_code}: {resp.text[:500]}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Test connectivity to a remote Ollama server")
    parser.add_argument("--base-url", default=os.getenv("OLLAMA_BASE_URL", "https://latho.cbio.uct.ac.za/ollama"), help="Base URL to Ollama (without trailing slash)")
    parser.add_argument("--api-key", default=os.getenv("OLLAMA_API_KEY"), help="API key if server requires auth (Authorization/X-API-Key)")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification (diagnostic only)")
    parser.add_argument("--ca-bundle", dest="ca_bundle", default=os.getenv("REQUESTS_CA_BUNDLE"), help="Path to custom CA bundle (PEM) for TLS verification")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    api_key = args.api_key
    # Determine verification mode
    verify: Any = True
    if args.ca_bundle:
        verify = args.ca_bundle
    elif args.insecure:
        verify = False

    print("=== Remote Ollama Connectivity Test ===")
    print(f"Base URL: {base_url}")
    print(f"API Key provided: {'yes' if api_key else 'no'}")
    if args.insecure and not args.ca_bundle:
        print("[WARNING] TLS verification disabled (--insecure). Use only for diagnostics.")
    if isinstance(verify, str):
        print(f"Using custom CA bundle: {verify}")
    headers = build_headers(api_key)

    print("\n[1/3] Checking server version...")
    ver = check_version(base_url, headers, verify)
    if ver is None:
        print("Aborting: failed to fetch version.")
        return 2

    print("\n[2/3] Listing available models...")
    models = list_models(base_url, headers, verify)
    if not models:
        print("Aborting: no models found or listing failed.")
        return 3

    # Pick a chat-capable model if possible (skip embedding-only models like nomic-embed-text)
    names: list[str] = []
    for m in models:
        if isinstance(m, dict) and isinstance(m.get("model"), str) and m["model"].strip():
            names.append(m["model"].strip())

    model_name = None
    if names:
        chat_candidates = [n for n in names if "embed" not in n.lower()]
        model_name = chat_candidates[0] if chat_candidates else names[0]

    if not model_name:
        print("Aborting: could not determine a model name from list response.")
        return 4

    print(f"Selected model: {model_name}")

    print("\n[3/3] Sending hello chat message...")
    reply = chat_hello(base_url, headers, model_name, verify)
    if reply is None:
        print("Chat test failed.")
        return 5

    # Simple success check
    success = "pong" in (reply or "").lower()
    print("\n=== RESULT ===")
    if success:
        print("Connectivity verified: received expected 'pong' token in reply.")
        return 0
    else:
        print("Connected successfully and got a reply, but it did not include 'pong'.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
