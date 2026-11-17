#!/usr/bin/env python3
"""Review and correct the detected AOIs before scoring.

  python scripts/review.py ap-work/example                 # prints a summary + inventory hints, renders review_d.png / review_m.png
  python scripts/review.py ap-work/example --apply overrides.json   # applies corrections -> final_d.json / final_m.json (+ new review images)
  python scripts/review.py ap-work/example --inventory d   # lists every detected text block / button / media with its box

overrides.json format (per device "d" / "m"):
  {"d": {"visual": [635,100,1320,640],                 explicit box [x1,y1,x2,y2] in screenshot px
         "subhead": {"text": "Accept payments"},        box of the text block containing this text
         "cta_primary": {"btn": "Get started", "hd": 0},  box of the button with this label (hd 1 = in header)
         "trust": {"union": [{"text": "Trusted by"}, [100,700,1300,790]]},
         "rating": null,                                 remove an AOI
         "_info": {"headline.t": "Corrected headline", "visual.kind": "product UI"}},
   "m": {...}}
Without --apply, final_*.json are written from the raw probe so scoring can proceed when nothing needs fixing.
"""
import argparse, copy, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import CODE, DEVICES, load, save, nm, html_to_pdf, find_browser  # noqa: E402


def union(bs):
    return [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]


def resolve(probe, spec):
    inv = probe.get("inv", {})
    if spec is None:
        return None
    if isinstance(spec, list):
        return {"b": spec}
    if "union" in spec:
        rs = [resolve(probe, s) for s in spec["union"]]
        return {"b": union([r["b"] for r in rs]), "t": " ".join(r.get("t", "") for r in rs if r.get("t"))} if all(rs) else None
    if "text" in spec:
        s = str(spec["text"]).lower()
        c = sorted([x for x in inv.get("texts", []) if s in x["t"].lower()], key=lambda x: len(x["t"]))
        x = c[spec.get("nth", 0)] if len(c) > spec.get("nth", 0) else None
        return {"b": x["b"], "t": x["t"], "f": x.get("f")} if x else None
    if "btn" in spec:
        s = str(spec["btn"]).lower(); allb = inv.get("btns", [])
        if "hd" in spec:
            allb = [x for x in allb if bool(x.get("hd")) == bool(spec["hd"])]
        c = [x for x in allb if x["t"].lower() == s] or [x for x in allb if s in x["t"].lower()]
        x = c[spec.get("nth", 0)] if len(c) > spec.get("nth", 0) else None
        return {"b": x["b"], "t": x["t"], "fl": x.get("fl")} if x else None
    if "media" in spec:
        idx = spec["media"] if isinstance(spec["media"], list) else [spec["media"]]
        bs = [inv.get("media", [])[i]["b"] for i in idx if i < len(inv.get("media", []))]
        return {"b": union(bs)} if bs else None
    return None


def apply(probe, ov):
    o = {k: copy.deepcopy(probe.get(k)) for k in ("site", "vw", "vh", "url", "title", "aoi", "info", "err", "device")}
    o["err"] = o.get("err") or []
    for k, spec in (ov or {}).items():
        if k == "_info":
            for path, val in spec.items():
                t = o["info"]; ks = path.split(".")
                for kk in ks[:-1]:
                    if not isinstance(t.get(kk), dict):
                        t[kk] = {}
                    t = t[kk]
                t[ks[-1]] = val
            continue
        if spec is None:
            o["aoi"].pop(k, None); o["info"].pop(k, None); continue
        r = resolve(probe, spec)
        if not r:
            o["err"].append(f"override not found: {k} {spec}"); continue
        o["aoi"][k] = [round(v) for v in r["b"]]
        if r.get("t"):
            if k in ("headline", "subhead"):
                o["info"][k] = dict(o["info"].get(k) or {}, t=r["t"], words=len(r["t"].split()))
                if r.get("f"): o["info"][k]["f"] = r["f"]
            elif k in ("eyebrow", "micro", "announce", "rating"):
                o["info"][k] = r["t"]
            elif k in ("cta_primary", "cta_secondary", "nav_cta"):
                o["info"][k] = dict(o["info"].get(k) or {}, t=r["t"])
                if "fl" in r: o["info"][k]["filled"] = bool(r["fl"])
    # boxes must have positive size inside the screenshot
    W, H = o["vw"], o["vh"]
    for k, b in list(o["aoi"].items()):
        b = [max(0, min(W, b[0])), max(0, min(H, b[1])), max(0, min(W, b[2])), max(0, min(H, b[3]))]
        if b[2] - b[0] < 2 or b[3] - b[1] < 2:
            if b[3] - b[1] < 2 and b[1] < H - 2: b[3] = b[1] + 2
            if b[2] - b[0] < 2 and b[0] < W - 2: b[2] = b[0] + 2
        o["aoi"][k] = b
    return o


def overlay_html(work, dev, pg):
    boxes = ""
    for k, b in pg["aoi"].items():
        if k == "header": continue
        c = CODE.get(k, (k[:2].upper(), "#000"))
        boxes += (f'<div class="b" style="border-color:{c[1]};left:{b[0]/pg["vw"]*100}%;top:{b[1]/pg["vh"]*100}%;'
                  f'width:{(b[2]-b[0])/pg["vw"]*100}%;height:{(b[3]-b[1])/pg["vh"]*100}%"><span style="background:{c[1]}">{c[0]} {k}</span></div>')
    w = 900 if dev == "d" else 390
    return (f'<html><body style="margin:0"><style>.w{{position:relative;width:{w}px}}.w img{{width:100%;display:block}}.b{{position:absolute;border:2px solid;box-sizing:border-box}}'
            f'.b span{{position:absolute;left:-2px;top:-2px;color:#fff;font:bold 10px sans-serif;padding:0 3px;white-space:nowrap}}</style>'
            f'<div class="w"><img src="{(work / (dev + ".png")).resolve().as_uri()}">{boxes}</div></body></html>')


def render_png(html_file, png_file, w, h):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(viewport={"width": w, "height": h})
            pg.goto(Path(html_file).resolve().as_uri()); pg.wait_for_timeout(500); pg.screenshot(path=str(png_file)); b.close()
        return True
    except Exception:  # noqa: BLE001
        br = find_browser()
        if not br: return False
        import subprocess, tempfile, shutil
        prof = tempfile.mkdtemp()
        subprocess.run([br, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files", f"--user-data-dir={prof}",
                        f"--window-size={w},{h}", f"--screenshot={Path(png_file).resolve()}", Path(html_file).resolve().as_uri()], timeout=120, capture_output=True)
        shutil.rmtree(prof, ignore_errors=True)
        return Path(png_file).exists()


def checks(pg):
    """Plausibility warnings for the AOIs - a substitute for looking at the review image, not a replacement."""
    W, H = pg["vw"], pg["vh"]; a = pg["aoi"]; i = pg.get("info") or {}; out = []
    area = lambda b: max(0, b[2] - b[0]) * max(0, b[3] - b[1])  # noqa: E731
    def ov(b1, b2):
        x = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0])); y = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1])); return x * y
    if "headline" not in a:
        out.append("no headline box - find the main hero sentence (--inventory) and add it")
    elif (i.get("headline") or {}).get("f") and (i["headline"]["f"] < (28 if W > 600 else 22)):
        out.append(f"headline font is only {i['headline']['f']} px - check that the box is the real hero headline, not a kicker or a card title")
    if "cta_primary" not in a and "form" not in a:
        out.append("no hero CTA or sign-up form - if a button is visible in the hero, add cta_primary")
    hd = a.get("header")
    for k in ("cta_primary", "cta_secondary"):
        if k in a and hd and a[k][3] <= hd[3] + 2:
            out.append(f"{k} sits inside the header - header buttons are nav_cta; hero CTAs are below the header")
    if "visual" in a:
        v = a["visual"]
        if area(v) > .7 * W * H:
            out.append("hero visual covers over 70% of the screen - probably a background; box only the image/product area or remove it")
        for k in ("headline", "cta_primary", "trust"):
            if k in a and area(a[k]) and ov(v, a[k]) > .3 * area(a[k]):
                out.append(f"hero visual box overlaps the {k} box - boxes should not contain other elements")
    for k, b in a.items():
        if area(b) < .0005 * W * H and k not in ("logo", "nav_cta", "micro", "eyebrow", "rating"):
            out.append(f"{k} box is tiny ({b}) - check it")
        if b[3] > H or b[1] >= H - 2:
            out.append(f"{k} box is at or below the fold - only first-screen elements count")
    if "micro" in a and any(ch.isdigit() for ch in str(i.get("micro", ""))) and len(str(i.get("micro", ""))) > 40:
        out.append("microcopy looks like a stats/proof row - stats and logo rows are trust")
    return out


def summary(pg):
    i = pg["info"]; L = [f"## {pg.get('site')} [{pg['vw']}x{pg['vh']}] theme={i.get('theme')}" + (f"  ERR {pg['err']}" if pg.get("err") else "")]
    h = i.get("headline") or {}
    L.append(f"  H1 \"{h.get('t','-')}\" {h.get('f','-')}px | eyebrow \"{i.get('eyebrow','-')}\"")
    L.append(f"  subhead \"{(i.get('subhead') or {}).get('t','-')}\"")
    L.append(f"  CTA1 \"{(i.get('cta_primary') or {}).get('t','-')}\" | CTA2 \"{(i.get('cta_secondary') or {}).get('t','-')}\" | order \"{i.get('cta_order','-')}\" | micro \"{i.get('micro','-')}\"")
    L.append(f"  nav {(i.get('nav') or {}).get('labels','-')} | nav CTA {(i.get('nav_cta') or {}).get('all','-')} | announce \"{i.get('announce','-')}\"")
    L.append(f"  visual {i.get('visual')} | trust {i.get('trust')}")
    L.append("  AOIs: " + ", ".join(f"{k}{v}" for k, v in pg["aoi"].items()))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("--apply"); ap.add_argument("--inventory")
    a = ap.parse_args(); work = Path(a.work)
    if a.inventory:
        p = load(work / f"probe_{a.inventory}.json")
        for x in p["inv"].get("texts", []): print("T", x["b"], f'{x.get("f")}px', ("(btn) " if x.get("k") else "") + x["t"][:90])
        for x in p["inv"].get("btns", []): print("B", x["b"], ("filled " if x.get("fl") else "plain ") + ("hdr " if x.get("hd") else "") + x["t"])
        for i, x in enumerate(p["inv"].get("media", [])): print(f"M#{i}", x["b"], x["g"])
        return
    ov = load(a.apply) if a.apply else {}
    for dev, cfg in DEVICES.items():
        probe = load(work / f"probe_{dev}.json")
        if not probe: continue
        final = apply(probe, ov.get(dev, {}))
        save(work / f"final_{dev}.json", final)
        hf = work / f"review_{dev}.html"; hf.write_text(overlay_html(work, dev, final), encoding="utf-8")
        w = 900 if dev == "d" else 390
        ok = render_png(hf, work / f"review_{dev}.png", w, int(w * cfg["h"] / cfg["w"]))
        warn = checks(final); final["checks"] = warn; save(work / f"final_{dev}.json", final)
        print(summary(final)); print("\n".join("  CHECK: " + w for w in warn) or "  CHECK: no obvious problems found"); print(f"  review image: {work / ('review_' + dev + '.png')} {'ok' if ok else '(open review_' + dev + '.html instead)'}\n")


if __name__ == "__main__":
    main()
