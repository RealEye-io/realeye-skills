#!/usr/bin/env python3
"""One-time setup: Python packages, Chromium for Playwright, and a token check (the token is never printed)."""
import json, os, subprocess, sys, urllib.request


def run(cmd):
    print("$", " ".join(cmd)); return subprocess.call(cmd)


def main():
    if sys.version_info < (3, 9):
        raise SystemExit("Python 3.9+ required")
    run([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "playwright", "pillow"])
    run([sys.executable, "-m", "playwright", "install", "chromium"])
    tok = os.environ.get("ATTENTION_PREDICTOR_API_TOKEN") or os.environ.get("ATTENTION_PREDICTOR_TOKEN")
    if not tok:
        print("\nATTENTION_PREDICTOR_API_TOKEN is not set. Create a token at https://app.attentionpredictor.com/api and set it as an environment variable "
              "(do not paste it into chat).")
        return
    req = urllib.request.Request("https://app.attentionpredictor.com/check-auth", headers={"Authorization": "Bearer " + tok,
                                 "User-Agent": "Mozilla/5.0 (compatible; attention-benchmark-skill/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        print(f"\ntoken ok: {d.get('authenticated')} · workspace: {(d.get('company') or {}).get('name')} · role: {(d.get('user') or {}).get('role')}")
    except Exception as e:  # noqa: BLE001
        print(f"\ntoken check failed: {e}")


if __name__ == "__main__":
    main()
