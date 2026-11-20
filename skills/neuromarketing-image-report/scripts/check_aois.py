#!/usr/bin/env python3
"""Check proposed AOIs (Areas of Interest) for a design and draw a preview, before measuring them.

Usage:  python check_aois.py aois.json [-i stimulus.jpg] [-o preview.png]

aois.json:
  {"image_px": [1024, 1536],
   "aois": [{"name": "Tagline", "role": "the claim", "why": "must be read first", "shape": [[3.5, 3.4], [44.0, 3.8], [44.4, 31.1], [4.4, 31.1]]}, ...]}
  shape = polygon points in percent of the image (x, y), origin top-left; a rectangle is four points.

It prints warnings for AOIs that are likely to give weak or misleading numbers (see references/aoi-design.md):
out of bounds, too small for webcam eye tracking, too large, overlapping, duplicated names, no role, too few or too many AOIs.
With -i (and Pillow installed) it also writes a preview of the image with every outline and number, so you can look at it and confirm
each AOI sits on the element it is named after. Exit code 1 when there is an error, 0 otherwise (warnings do not fail).
"""
import argparse
import json
import sys
from pathlib import Path

MIN_SIDE_PCT = 6.0      # webcam eye tracking is imprecise: a side below ~6% of the image is likely below its precision
MAX_AREA_PCT = 55.0     # an AOI covering most of the image tells little
MAX_OVERLAP = 0.25      # share of the smaller AOI that another AOI may cover before it is flagged
GRID = (200, 300)       # raster used for areas and overlaps


def area_pct(shape):
    a = 0.0
    for i, (x1, y1) in enumerate(shape):
        x2, y2 = shape[(i + 1) % len(shape)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2 / 100.0   # percent of the image (shape is in % x %, so /100 gives % of the 100x100 square)


def mask(shape):
    from PIL import Image, ImageDraw
    m = Image.new("L", GRID, 0)
    ImageDraw.Draw(m).polygon([(x / 100 * (GRID[0] - 1), y / 100 * (GRID[1] - 1)) for x, y in shape], fill=255)
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("aois_json")
    ap.add_argument("-i", "--image")
    ap.add_argument("-o", "--output", default="aoi-preview.png")
    a = ap.parse_args()
    d = json.loads(Path(a.aois_json).read_text(encoding="utf-8"))
    W, H = d.get("image_px", [1024, 1536])
    aois = d["aois"]
    errors, warns = [], []
    names = [x["name"] for x in aois]
    for n in {n for n in names if names.count(n) > 1}:
        errors.append(f"duplicate name: {n}")
    if len(aois) < 3:
        warns.append(f"only {len(aois)} AOIs: add the elements the decision depends on (brand, product, claim, offer, call to action, face)")
    if len(aois) > 8:
        warns.append(f"{len(aois)} AOIs: more than 8 makes the report hard to read and the small ones noisy; merge or drop the least important")
    for x in aois:
        sh = x.get("shape") or []
        if len(sh) < 3:
            errors.append(f"{x['name']}: needs at least 3 points")
            continue
        if any(not (0 <= px <= 100 and 0 <= py <= 100) for px, py in sh):
            errors.append(f"{x['name']}: points outside 0-100%")
        xs, ys = [p[0] for p in sh], [p[1] for p in sh]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        ar = area_pct(sh)
        print(f"{x['name']}: box {min(xs):.1f},{min(ys):.1f} to {max(xs):.1f},{max(ys):.1f} % = {round(min(xs) / 100 * W)},{round(min(ys) / 100 * H)} to {round(max(xs) / 100 * W)},{round(max(ys) / 100 * H)} px; size {w:.1f} x {h:.1f} %; area {ar:.1f} % of the image")
        if min(w, h) < MIN_SIDE_PCT:
            warns.append(f"{x['name']}: a side is {min(w, h):.1f}% of the image, below {MIN_SIDE_PCT:.0f}%: webcam eye tracking may not resolve it. Grow it to include some surrounding space or merge it into a larger element")
        if ar > MAX_AREA_PCT:
            warns.append(f"{x['name']}: covers {ar:.0f}% of the image: too broad to tell where attention goes. Split it")
        if not x.get("role"):
            warns.append(f"{x['name']}: no 'role' (what the element is and why it matters)")
        if not x.get("why"):
            warns.append(f"{x['name']}: no 'why' (the question about the design this AOI answers)")
    try:
        masks = {x["name"]: mask(x["shape"]) for x in aois if len(x.get("shape") or []) >= 3}
        for i, n1 in enumerate(masks):
            for n2 in list(masks)[i + 1:]:
                from PIL import ImageChops
                inter = ImageChops.darker(masks[n1], masks[n2]).histogram()[255]
                small = min(masks[n1].histogram()[255], masks[n2].histogram()[255]) or 1
                if inter / small > MAX_OVERLAP:
                    warns.append(f"{n1} and {n2} overlap: {inter / small * 100:.0f}% of the smaller one. Fine if one is deliberately inside the other (say so in the role), otherwise separate them")
    except ImportError:
        warns.append("Pillow not installed: overlaps not checked (pip install pillow)")
    for e_ in errors:
        print("ERROR:", e_)
    for w_ in warns:
        print("WARNING:", w_)
    if a.image:
        try:
            from PIL import Image, ImageDraw
            im = Image.open(a.image).convert("RGB")
            iw, ih = im.size
            dr = ImageDraw.Draw(im, "RGBA")
            pal = [(215, 119, 50), (110, 200, 80), (50, 150, 215), (215, 50, 150), (150, 215, 50), (112, 72, 232), (240, 140, 0), (0, 160, 160)]
            for i, x in enumerate(aois):
                sh = x.get("shape") or []
                if len(sh) < 3:
                    continue
                pts = [(px / 100 * iw, py / 100 * ih) for px, py in sh]
                c = pal[i % len(pal)]
                dr.polygon(pts, fill=c + (40,), outline=c + (255,))
                dr.line(pts + [pts[0]], fill=c + (255,), width=max(2, iw // 250))
                tx, ty = min(p[0] for p in pts) + 4, min(p[1] for p in pts) + 4
                dr.rectangle([tx - 2, ty - 2, tx + 18 * len(str(i + 1)) + 6, ty + 20], fill=(33, 37, 41, 255))
                dr.text((tx + 3, ty + 2), str(i + 1), fill=(255, 255, 255, 255))
            im.save(a.output)
            print(f"preview written to {a.output} (numbers follow the order in the file): open it and check every outline sits on the element it is named after")
        except ImportError:
            print("Pillow not installed: no preview (pip install pillow)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
