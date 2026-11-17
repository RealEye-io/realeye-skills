#!/usr/bin/env python3
"""Render report HTML (print layout) to page-sized PNGs so the agent can look at the report before sending it.

  python scripts/preview.py ap-work/example/report/<file>.html [--pages 1,2,5] [--landscape]
Output: <html dir>/preview/<stem>_p<N>.png
"""
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("html"); ap.add_argument("--pages", default="1,2,3"); ap.add_argument("--landscape", action="store_true")
    a = ap.parse_args(); src = Path(a.html).resolve()
    W, H = (1123, 794) if a.landscape else (794, 1123)
    out = src.parent / "preview"; out.mkdir(exist_ok=True)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
        pg.emulate_media(media="print"); pg.goto(src.as_uri(), wait_until="networkidle")
        total = pg.evaluate("document.documentElement.scrollHeight")
        for n in [int(x) for x in a.pages.split(",")]:
            if (n - 1) * H >= total:
                continue
            f = out / f"{src.stem}_p{n}.png"
            pg.screenshot(path=str(f), full_page=True, clip={"x": 0, "y": (n - 1) * H, "width": W, "height": H}); print(f)
        b.close()


if __name__ == "__main__":
    main()
