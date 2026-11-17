#!/usr/bin/env python3
"""Capture a landing page's first screen on desktop (1440x900) and mobile (390x844) and detect its hero anatomy.

Usage:  python scripts/capture.py https://example.com [--name example] [--work ap-work] [--wait 7] [--click d:x,y] [--click m:x,y]
        python scripts/capture.py https://example.com --name example --image-d desk.png --image-m phone.png
               (no Playwright: import first-screen screenshots taken by any browser at 1440x900 and 390x844; they are
                scaled to that width and cropped to that height. No elements are detected - give every AOI box in
                overrides.json for review.py.)
Output: <work>/<slug>/d.png, m.png, probe_d.json, probe_m.json   (probe = AOI boxes + hero texts + inventory)
Needs:  pip install playwright && python -m playwright install chromium
"""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import JS_DIR, DEVICES, slug, save  # noqa: E402

UA_D = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
UA_M = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
PAUSE_VIDEOS = "(() => { try { scrollTo(0,0); document.querySelectorAll('video').forEach(v => { try { v.pause(); } catch (e) {} }); } catch (e) {} return 1; })()"


def capture(url, out_dir, name, wait=7, clicks=None):
    from playwright.sync_api import sync_playwright
    dismiss = (JS_DIR / "dismiss.js").read_text(encoding="utf-8")
    probe = (JS_DIR / "probe.js").read_text(encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    clicks = clicks or {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for dev, cfg in DEVICES.items():
            ctx = browser.new_context(viewport={"width": cfg["w"], "height": cfg["h"]}, device_scale_factor=1, is_mobile=(dev == "m"), has_touch=(dev == "m"),
                                      user_agent=UA_M if dev == "m" else UA_D, locale="en-US")
            ctx.route("**/accounts.google.com/gsi/**", lambda r: r.abort())  # Google one-tap sign-in popups cover the hero
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:  # noqa: BLE001
                print(f"[{dev}] navigation warning: {e}", file=sys.stderr)
            time.sleep(wait)
            log = [page.evaluate(dismiss)]
            for x, y in clicks.get(dev, []):
                page.mouse.click(x, y)
            time.sleep(2)
            log.append(page.evaluate(dismiss))
            page.evaluate(PAUSE_VIDEOS)
            time.sleep(2)
            log.append(page.evaluate(dismiss))
            page.evaluate(f"window.__AP_SITE = {json.dumps(name)}; window.__AP_FILE = '{dev}.png'; 1")
            res = json.loads(page.evaluate(probe))
            res["device"] = dev
            res["dismiss_log"] = log
            page.screenshot(path=str(out_dir / f"{dev}.png"), clip={"x": 0, "y": 0, "width": cfg["w"], "height": cfg["h"]})
            save(out_dir / f"probe_{dev}.json", res)
            print(f"[{dev}] ok {url} -> {out_dir / (dev + '.png')}  aois: {', '.join(res['aoi'].keys())}  banners: {log}")
            ctx.close()
        browser.close()


def import_images(url, out_dir, name, images):
    """Use screenshots from another browser: scale to the benchmark viewport width, crop to its height, empty probe."""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("--image-d/--image-m need Pillow: pip install pillow")
    for dev, src in images.items():
        if not src:
            print(f"[{dev}] no image given - this device is skipped", file=sys.stderr); continue
        cfg = DEVICES[dev]; im = Image.open(src).convert("RGB")
        if im.width != cfg["w"]:
            im = im.resize((cfg["w"], round(im.height * cfg["w"] / im.width)), Image.LANCZOS)
        if im.height < cfg["h"]:
            pad = Image.new("RGB", (cfg["w"], cfg["h"]), "white"); pad.paste(im, (0, 0)); im = pad
        im.crop((0, 0, cfg["w"], cfg["h"])).save(out_dir / f"{dev}.png")
        save(out_dir / f"probe_{dev}.json", {"site": name, "vw": cfg["w"], "vh": cfg["h"], "url": url, "title": "", "aoi": {}, "info": {},
                                               "inv": {"texts": [], "btns": [], "media": []}, "err": ["imported screenshot: no DOM probe"], "device": dev})
        print(f"[{dev}] imported {src} -> {out_dir / (dev + '.png')} (no elements detected: give every AOI box in overrides.json)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("--name"); ap.add_argument("--work", default="ap-work"); ap.add_argument("--wait", type=int, default=7)
    ap.add_argument("--click", action="append", default=[], help="d:x,y or m:x,y - click a point (e.g. a cookie banner's Reject) before capture")
    ap.add_argument("--image-d"); ap.add_argument("--image-m")
    a = ap.parse_args()
    url = a.url if a.url.startswith("http") else "https://" + a.url
    name = a.name or slug(url)
    clicks = {}
    for c in a.click:
        dev, xy = c.split(":"); x, y = xy.split(","); clicks.setdefault(dev, []).append((float(x), float(y)))
    if a.image_d or a.image_m:
        import_images(url, Path(a.work) / name, name, {"d": a.image_d, "m": a.image_m})
    else:
        capture(url, Path(a.work) / name, name, a.wait, clicks)
    meta = {"name": name, "url": url, "captured": time.strftime("%Y-%m-%d")}
    save(Path(a.work) / name / "meta.json", meta)


if __name__ == "__main__":
    main()
