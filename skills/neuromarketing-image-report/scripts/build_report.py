#!/usr/bin/env python3
"""Render a neuromarketing report JSON file into one self-contained HTML report.

Usage:  python build_report.py report.json [-o report.html]

The report is styled after the RealEye dashboard (the AOI VAI report): light surface, white
square cards, Barlow type, orange accent, uppercase labels, best/lowest value pills. It uses
only RealEye's measured VAI (Visual Attention Index) and its components (Reach, Speed, Hold);
raw metrics such as time to first fixation are never shown. Standard library only (Pillow is
optional, only to shrink large screenshots). Images are embedded once as data URIs, so the
result is a single file. See references/html-report.md for the JSON schema.
"""
import argparse
import base64
import html
import json
import math
import mimetypes
import re
import struct
import sys
from pathlib import Path

VARIANT_COLORS = ["#fc7753", "#3b82e0", "#27a85a", "#ae3ec9"]
COMP_COLORS = {"vai": "#fc7753", "reach": "#3b82e0", "speed": "#e3ac1c", "hold": "#27a85a"}
AOI_COLORS = ["#d77732", "#6ec850", "#3296d7", "#d73296", "#96d732", "#7048e8", "#f08c00"]
MIN_N = 30
WIN = ["3", "5", "10"]
WIN_LABEL = {"3": "first 3 s", "5": "first 5 s", "10": "first 10 s"}
COMP = [("vai", "VAI"), ("reach", "Reach"), ("speed", "Speed"), ("hold", "Hold")]

e = lambda s: html.escape("" if s is None else str(s), quote=True)
vcolor = lambda i: VARIANT_COLORS[i % len(VARIANT_COLORS)]

CHECK = ('<svg class="chk" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M3 8.5l3.2 3L13 4.5" fill="none" '
         'stroke="#fc7753" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>')


# ------------------------------------------------------------------ images
IMAGES = {}


def reg_image(uri):
    if uri not in IMAGES:
        IMAGES[uri] = f"im{len(IMAGES)}"
    return IMAGES[uri]


def image_size(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            m = data[i + 1]
            if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


def load_image(base, ref):
    if not ref:
        return None, None
    if ref.startswith(("data:", "http://", "https://")):
        return ref, None
    p = (base / ref).resolve()
    data = p.read_bytes()
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    if len(data) > 250_000:
        try:
            import io
            from PIL import Image
            im = Image.open(io.BytesIO(data)).convert("RGB")
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=86, optimize=True)
            data, mime = buf.getvalue(), "image/jpeg"
        except Exception:
            pass
    return f"data:{mime};base64,{base64.b64encode(data).decode()}", image_size(data)


GLOSSARY = {
    "VAI Reach": "VAI Reach: the share of viewers who looked at the element at least once in the time window (0–100).",
    "VAI Speed": "VAI Speed: how soon the element is noticed after it becomes visible (0–100). Used to rank the viewing order.",
    "VAI Hold": "VAI Hold: how long attention stays on the element, relative to the time window (0–100).",
    "VAI": "VAI (Visual Attention Index): RealEye's attention score for an element, 0–100. It is the average of Reach, Speed and Hold. Use it to compare, not as a percentage of viewers.",
    "Reach": "Reach: the share of viewers who looked at the element at least once in the time window.",
    "Speed": "Speed: how soon the element is noticed after it becomes visible. Used to rank the viewing order.",
    "Hold": "Hold: how long attention stays on the element, relative to the time window.",
    "AOIs": "AOI (Area of Interest): a region of the image, such as the tagline, pack, face or logo, that is measured separately.",
    "AOI": "AOI (Area of Interest): a region of the image, such as the tagline, pack, face or logo, that is measured separately.",
}
_SKIP_TAGS = ("svg", "script", "style", "title", "option", "textarea")


def make_tips(spec):
    """Return a function that wraps every glossary term in the text of an HTML fragment in a tooltip span."""
    terms = dict(GLOSSARY)
    terms.update(spec.get("glossary", {}))
    rx = re.compile(r"\b(" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + r")\b")

    def wrap(m):
        return f'<span class="gl" data-tip="{e(terms[m.group(1)])}">{m.group(1)}</span>'

    def tips(fragment):
        out, depth = [], 0
        for tok in re.split(r"(<[^>]*>)", fragment):
            if tok.startswith("<"):
                mt = re.match(r"<(/?)([a-zA-Z0-9]+)", tok)
                if mt and mt.group(2).lower() in _SKIP_TAGS and not tok.endswith("/>"):
                    depth += -1 if mt.group(1) else 1
                out.append(tok)
            else:
                out.append(tok if depth > 0 else rx.sub(wrap, tok))
        return "".join(out)
    return tips


DESIGNS = {}   # design id -> {"name", "cls"}: filled in build() so every mention can show a thumbnail


def chip(did, label_html, cls="", style=""):
    d = DESIGNS.get(did)
    if not d:
        return label_html
    st = f' style="{style}"' if style else ""
    return (f'<span class="dref {cls}" tabindex="0" role="button" data-id="{e(did)}" data-name="{e(d["name"])}" data-cls="{d["cls"]}"{st}>{label_html}</span>')


def rich(text):
    """Escape free text and turn design mentions into chips that show the design thumbnail on hover or click.
    Recognised: {A}, "Design A", "(A)", "(A and B)", "in A", "than B", "A's", "A 14.3", "A: ...", "A and B"."""
    t = e(text)
    ok = lambda x: x in DESIGNS
    c = lambda x: chip(x, x) if ok(x) else x
    t = re.sub(r"\{([A-Z])\}", lambda m: c(m.group(1)), t)
    t = re.sub(r"\b([Dd]esign) ([A-Z])\b", lambda m: chip(m.group(2), m.group(0)) if ok(m.group(2)) else m.group(0), t)
    t = re.sub(r"\(([A-Z])( and ([A-Z]))?\)", lambda m: "(" + c(m.group(1)) + (" and " + c(m.group(3)) if m.group(3) else "") + ")", t)
    t = re.sub(r"\b((?:in|In|than|vs|favours|favors|for|of|to|from|between|versus|Keep|keep|Use|use|Test|test) )([A-Z])(?![\w'])",
               lambda m: m.group(1) + c(m.group(2)), t)
    t = re.sub(r"(?<![\w>;])([A-Z])(?=&#x27;s\b|:| [+\-\u2212]?\d| (?:and|or) [A-Z]\b)", lambda m: c(m.group(1)), t)
    t = re.sub(r"(?<= and )([A-Z])(?![\w'])", lambda m: c(m.group(1)) if m.group(1) != "A" else m.group(1), t)
    return t


def src_of(spec):
    return spec if isinstance(spec, str) else spec.get("src")


def figure(base, spec, alt, caption=""):
    """Plain figure; the image is embedded once through a CSS class, aspect ratio from the file."""
    if not spec:
        return ""
    uri, size = load_image(base, src_of(spec))
    ar = f"{size[0]}/{size[1]}" if size else "3/2"
    cap = caption or (spec.get("caption", "") if isinstance(spec, dict) else "")
    return (f'<figure><div class="pic {reg_image(uri)}" role="img" aria-label="{e(alt)}" style="aspect-ratio:{ar}"></div>'
            f'<figcaption>{e(cap)}</figcaption></figure>')


# ------------------------------------------------------------------ data access
def seg_of(v, label):
    return next((s for s in v["segments"] if s["label"] == label), None)


def val(seg, w, ai, k):
    wi = WIN.index(w)
    return seg["values"][wi * 20 + ai * 4 + [c for c, _ in COMP].index(k)]


def names(spec):
    return spec["aoi_order"]


def aoi_of(v, nm):
    return next(a for a in v["aois"] if a["name"] == nm)


def acolor(v, nm, i=0):
    return aoi_of(v, nm).get("color") or AOI_COLORS[i % len(AOI_COLORS)]


def rank_names(spec, seg, w, key="speed"):
    n = names(spec)
    return sorted(n, key=lambda nm: (-val(seg, w, n.index(nm), key), -val(seg, w, n.index(nm), "reach"), -val(seg, w, n.index(nm), "vai")))


def small(seg):
    return seg["n"] < MIN_N


def lst(words):
    words = list(words)
    if not words:
        return ""
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


# ------------------------------------------------------------------ RealEye dashboard links
def _flags(label):
    lab = label.strip()
    g = {"m": "true", "f": "true", "o": "true", "n": "true"}
    if lab.startswith("Men"):
        g = {"m": "true", "f": "false", "o": "false", "n": "false"}
        lab = lab[3:].strip()
    elif lab.startswith("Women"):
        g = {"m": "false", "f": "true", "o": "false", "n": "false"}
        lab = lab[5:].strip()
    lo, hi = 0, 99
    if lab and lab != "All":
        if lab.endswith("+"):
            lo, hi = int(lab[:-1]), 99
        elif "–" in lab:
            a, b = lab.split("–")
            lo, hi = int(a), int(b)
    return g, lo, hi


def dash_url(spec, v, kind, label="All", w=None):
    """Deep link into the RealEye dashboard with the audience filters applied (heatmap | aoi | vai | study)."""
    d = spec.get("dashboard")
    if not d or (kind != "study" and not v.get("item_id")):
        return None
    base = d.get("base", "https://app.realeye.io").rstrip("/")
    study, item = d.get("study_id"), v.get("item_id")
    if kind == "study":
        return f"{base}/dashboard/study/{study}/"
    if kind == "vai":
        return f"{base}/dashboard/study/{study}/item/{item}/aoi-vai-report"
    g, lo, hi = _flags(label)
    q = d.get("min_quality", 3)
    h = (f"itemId={item}&genderMale={g['m']}&genderFemale={g['f']}&genderOther={g['o']}&genderNotSpecified={g['n']}&ageMin={lo}&ageMax={hi}"
         "&participantTypeRealEye=true&participantTypeOwn=true&deviceDesktop=true&deviceSmartphone=true&deviceSmartphoneVertical=true"
         "&deviceSmartphoneHorizontal=true&deviceTablet=true&setupLocal=true&setupMouse=true&setupOpengaze=true&setupReWebcamV3=true"
         f"&participantQualityGradeItemMin={q}&participantQualityGradeItemMax=6")
    if kind == "heatmap":
        h += ("&participantId=all&viewType=fixations&heatmapType=heatmap&fineTuneAutoAdjustment=1"
              f"&itemTimeFrom=500&itemTimeTo={(w or 10) * 1000}&movingMedianRangeMs=200&minFixationDurationMs=80&maxFixationDurationMs=400"
              "&gazeVelocityThreshold=30&maxSaccadeDurationMs=150")
    h += "&filterAnswers=%5B%5D&includeAll=0"
    return f"{base}/dashboard/item/{item}/{'aoi' if kind == 'aoi' else ''}#{h}"


def alink(url, text, cls="ext"):
    if not url:
        return e(text)
    return f'<a class="{cls}" href="{e(url)}" target="_blank" rel="noopener">{e(text)} ↗</a>'


def open_links(spec, v, label="All", w=None, parts=("heatmap", "aoi", "vai")):
    names_ = {"heatmap": "Heatmap", "aoi": "AOI report", "vai": "AOI VAI report"}
    return " · ".join(alink(dash_url(spec, v, k, label, w), names_[k]) for k in parts if dash_url(spec, v, k, label, w))


# ------------------------------------------------------------------ AOI stage (image with outlines)
def bbox(shape):
    xs, ys = [p[0] for p in shape], [p[1] for p in shape]
    return min(xs), min(ys), max(xs), max(ys)


def stage(base, v, numbers=None, outlines=True, cls=""):
    """The analysed image with its AOI outlines (SVG) and optional numbered markers."""
    uri, size = load_image(base, src_of(v["stimulus"]))
    ar = f"{size[0]}/{size[1]}" if size else "2/3"
    svg = ""
    if outlines:
        polys = "".join(
            f'<polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in a["shape"])}" fill="{a.get("color", "#fc7753")}" fill-opacity=".13" '
            f'stroke="{a.get("color", "#fc7753")}" stroke-width="2" vector-effect="non-scaling-stroke"/>' for a in v["aois"] if a.get("shape"))
        svg = f'<svg class="aoi-svg" viewBox="0 0 100 100" preserveAspectRatio="none">{polys}</svg>'
    mk = "".join(f'<span class="mk" style="left:{x:.2f}%;top:{y:.2f}%">{e(l)}</span>' for l, x, y in (numbers or []))
    return f'<div class="stage pic {reg_image(uri)} {cls}" role="img" aria-label="Analysed image with AOIs" style="aspect-ratio:{ar}">{svg}{mk}</div>'


def aoi_crop(base, v, a, target=1.7):
    """Fixed-shape crop of one AOI from the clean analysed image (cover-style, no distortion)."""
    uri, size = load_image(base, src_of(v["stimulus"]))
    if not a.get("shape") or not size:
        return ""
    W, H = size
    x0, y0, x1, y1 = bbox(a["shape"])
    pad = 1.5
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    bw, bh = x1 - x0, y1 - y0
    if (bw * W) / (bh * H) > target:           # too wide: grow the height
        bh2, bw2 = bw * W / target / H, bw
    else:                                      # too tall: grow the width
        bw2, bh2 = bh * H * target / W, bh
    bw2, bh2 = min(bw2, 100), min(bh2, 100)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    nx0 = min(max(cx - bw2 / 2, 0), 100 - bw2)
    ny0 = min(max(cy - bh2 / 2, 0), 100 - bh2)
    px = nx0 / (100 - bw2) * 100 if bw2 < 100 else 0
    py = ny0 / (100 - bh2) * 100 if bh2 < 100 else 0
    return (f'<div class="crop pic {reg_image(uri)}" style="aspect-ratio:{target};background-size:{100 / bw2 * 100:.2f}% {100 / bh2 * 100:.2f}%;'
            f'background-position:{px:.2f}% {py:.2f}%"></div>')


def order_markers(spec, v):
    seg = seg_of(v, "All")
    order = rank_names(spec, seg, "10")
    out = []
    for a in v["aois"]:
        if a.get("shape"):                      # badge on the top-left corner of the AOI, clear of the text
            x0, y0, _, _ = bbox(a["shape"])
            out.append((order.index(a["name"]) + 1, x0, y0))
        elif a.get("marker"):
            out.append((order.index(a["name"]) + 1, a["marker"][0], a["marker"][1]))
    return out


# ------------------------------------------------------------------ small components
def tile(label, value, sub=""):
    return f'<div class="tile"><span class="lab">{e(label)}</span><b>{rich(value)}</b><span class="sub">{rich(sub)}</span></div>'


def insight(text, lead=None):
    inner = (f"<b>{rich(lead)}</b> " if lead else "") + rich(text)
    return f'<div class="insight">{CHECK}<div>{inner}</div></div>'


def note(label, text):
    return f'<div class="note"><b>{e(label)}</b> {text}</div>'


def pill_vals(values, fmt="{:.1f}"):
    mx, mn = max(values), min(values)
    out = []
    for x in values:
        c = " best" if x == mx and mx != mn else (" worst" if x == mn and mx != mn else "")
        out.append(f'<span class="vp{c}">{fmt.format(x)}</span>')
    return out


def swatch(c):
    return f'<i class="sw" style="background:{c}"></i>'


def section(id_, title, body, cls=""):
    idattr = f' id="{id_}"' if id_ else ""
    return f'<section class="sec {cls}"{idattr}><h2>{title}</h2>{body}</section>'


# ------------------------------------------------------------------ charts (CSS and SVG)
def comp_bars(spec, v, seg, w):
    rows = ""
    for ai, nm in enumerate(names(spec)):
        bars = "".join(
            f'<div class="brow"><div class="track"><i style="width:{max(val(seg, w, ai, k), .6):.1f}%;background:{COMP_COLORS[k]}"></i></div><b>{val(seg, w, ai, k):.1f}</b></div>'
            for k, _ in COMP)
        rows += f'<div class="crow"><div class="cname">{swatch(acolor(v, nm, ai))}{e(nm)}</div><div class="cbars">{bars}</div></div>'
    leg = "".join(f'<span>{swatch(COMP_COLORS[k])}{lab}</span>' for k, lab in COMP)
    return f'<div class="legend">{leg}</div><div class="comp-chart">{rows}</div>'


def lines(series, xlabels, title, w=380, h=200):
    left, right, top, bot = 34, 12, 12, 34
    pw, ph = w - left - right, h - top - bot
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{e(title)}">']
    for t in range(5):
        y = top + ph - ph * t / 4
        out.append(f'<line x1="{left}" x2="{w - right}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/><text x="{left - 5}" y="{y + 4:.1f}" text-anchor="end" class="axis">{25 * t}</text>')
    xs = [left + pw * i / (len(xlabels) - 1) for i in range(len(xlabels))]
    for x, lab in zip(xs, xlabels):
        out.append(f'<text x="{x:.1f}" y="{h - 12}" text-anchor="middle" class="axis">{e(lab)}</text>')
    for nm, (vals, c) in series.items():
        pts = " ".join(f"{x:.1f},{top + ph - ph * min(v, 100) / 100:.1f}" for x, v in zip(xs, vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.4"/>')
        out += [f'<circle cx="{x:.1f}" cy="{top + ph - ph * min(v, 100) / 100:.1f}" r="3" fill="{c}"/>' for x, v in zip(xs, vals)]
    out.append("</svg>")
    return "".join(out)


def hbars(cats, series, title, labelw=170):
    bh, gap, gg, width = 14, 3, 14, 760
    gh = len(series) * (bh + gap)
    h = len(cats) * (gh + gg) + 8
    plot = width - labelw - 60
    out = [f'<svg class="chart wide" viewBox="0 0 {width} {h}" role="img" aria-label="{e(title)}">']
    for t in range(5):
        x = labelw + plot * t / 4
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{h - 4}" class="grid"/>')
    for gi, c in enumerate(cats):
        y0 = gi * (gh + gg) + 4
        out.append(f'<text x="{labelw - 10}" y="{y0 + gh / 2 + 4}" text-anchor="end" class="axis">{e(c)}</text>')
        for si, (lab, col, vals) in enumerate(series):
            y = y0 + si * (bh + gap)
            w = max(1.5, plot * vals[gi] / 100)
            out.append(f'<rect x="{labelw}" y="{y}" width="{w:.1f}" height="{bh}" fill="{col}"/><text x="{labelw + w + 6:.1f}" y="{y + 11}" class="val">{vals[gi]:.1f}</text>')
    out.append("</svg>")
    return "".join(out)


def legend(items):
    return '<div class="legend">' + "".join(f"<span>{swatch(c)}{e(l)}</span>" for l, c in items) + "</div>"


# ------------------------------------------------------------------ tables
def cell(seg, w, ai):
    vai, r, s, h = (val(seg, w, ai, k) for k, _ in COMP)
    cls = " low" if small(seg) else ""
    return f'<td class="vc{cls}"><b>{vai:.0f}</b><small>{r:.0f} · {s:.0f} · {h:.0f}</small></td>'


def vai_summary(spec, v):
    seg = seg_of(v, "All")
    n = names(spec)
    cols = {k: pill_vals([val(seg, "10", i, k) for i in range(len(n))]) for k, _ in COMP}
    rows = "".join(
        f'<tr><td class="num">{i + 1}</td><td>{swatch(acolor(v, nm, i))}<b>{e(nm)}</b></td>' + "".join(f"<td>{cols[k][i]}</td>" for k, _ in COMP) + "</tr>"
        for i, nm in enumerate(n))
    return (f'<div class="tablewrap"><table class="re"><thead><tr><th class="num">#</th><th>Element</th><th>VAI</th><th>VAI Reach</th><th>VAI Speed</th><th>VAI Hold</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div><div class="legend small"><span><i class="sw best"></i>Best value in column</span><span><i class="sw worst"></i>Lowest value in column</span></div>')


def window_table(spec, v):
    seg = seg_of(v, "All")
    rows = ""
    for ai, nm in enumerate(names(spec)):
        rows += (f'<tr><td>{swatch(acolor(v, nm, ai))}<b>{e(nm)}</b><small>{e(aoi_of(v, nm).get("role", ""))}</small></td>'
                 + "".join(cell(seg, w, ai) for w in WIN) + "</tr>")
    lk = alink(dash_url(spec, v, "aoi"), "See this data in the RealEye AOI report")
    return (f'<div class="tablewrap"><table class="re seg"><thead><tr><th>Element</th>' + "".join(f"<th>{WIN_LABEL[w]}</th>" for w in WIN) + f'</tr></thead><tbody>{rows}</tbody></table></div>'
            f'<p class="hint">Each cell: <b>VAI</b> (large) and Reach · Speed · Hold (small), 0–100. {lk}</p>')


def segment_table(spec, v, kind, title):
    segs = [s for s in v["segments"] if s["kind"] == kind]
    if not segs:
        return ""
    head = "".join(f'<th>{alink(dash_url(spec, v, "aoi", s["label"]), s["label"])}<small>N = {s["n"]}{" †" if small(s) else ""}</small></th>' for s in segs)
    rows = ""
    for ai, nm in enumerate(names(spec)):
        for wi, w in enumerate(WIN):
            first = f'<th scope="row" rowspan="3">{swatch(acolor(v, nm, ai))}{e(nm)}</th>' if wi == 0 else ""
            rows += f'<tr class="{"grp" if wi == 0 else ""}">{first}<th class="w">{WIN_LABEL[w]}</th>' + "".join(cell(s, w, ai) for s in segs) + "</tr>"
    return f'<h5>{e(title)}</h5><div class="tablewrap"><table class="re seg"><thead><tr><th>Element</th><th>Window</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def gap_table(spec, variants, a_label, b_label, title):
    rows = ""
    for vi, v in enumerate(variants):
        sa, sb = seg_of(v, a_label), seg_of(v, b_label)
        if not sa or not sb:
            continue
        for ai, nm in enumerate(names(spec)):
            cells = ""
            for w in WIN:
                dv = val(sb, w, ai, "vai") - val(sa, w, ai, "vai")
                ds = val(sb, w, ai, "speed") - val(sa, w, ai, "speed")
                cells += f'<td class="vc{" big" if abs(dv) >= 10 else ""}"><b>{dv:+.1f}</b><small>Speed {ds:+.1f}</small></td>'
            rows += f'<tr><td>{chip(v["id"], e(v["id"]), "vtag", "background:" + vcolor(vi))} <b>{e(nm)}</b></td>{cells}</tr>'
    return (f'<h5>{e(title)}</h5><div class="tablewrap"><table class="re seg"><thead><tr><th>Design · element</th>' + "".join(f"<th>{WIN_LABEL[w]}</th>" for w in WIN) +
            f'</tr></thead><tbody>{rows}</tbody></table></div><p class="hint">VAI points (large) and VAI Speed points (small). Shaded cells differ by 10 or more VAI points.</p>')


# ------------------------------------------------------------------ main sections
def vai_guide(spec):
    g = spec["variants"][0]
    seg = seg_of(g, "All")
    n = names(spec)
    ai = min(range(len(n)), key=lambda i: val(seg, "10", i, "vai"))
    ex = {k: val(seg, "10", ai, k) for k, _ in COMP}
    brow = lambda lab, x, c: f'<div class="exrow"><span>{lab}</span><div class="track"><i style="width:{max(x, .6):.0f}%;background:{c}"></i></div><b>{x:.1f}</b></div>'
    example = ('<div class="example">' + f'<h5>Worked example: {e(n[ai])}, design {e(g["id"])}, {WIN_LABEL["10"]}</h5>'
               + brow("Reach", ex["reach"], COMP_COLORS["reach"]) + brow("Speed", ex["speed"], COMP_COLORS["speed"]) + brow("Hold", ex["hold"], COMP_COLORS["hold"])
               + f'<div class="exrow total"><span>VAI = average of the three</span><div></div><b>{ex["vai"]:.1f}</b></div>'
               f'<p class="hint">Only about {ex["reach"]:.0f}% of viewers reached it, those who did got there late (Speed {ex["speed"]:.0f}) and looked only briefly (Hold {ex["hold"]:.0f}). '
               "The low VAI is the combination of all three, which is why the three measures matter as much as the total.</p></div>")
    cards = "".join(f'<div class="cc" style="border-top-color:{COMP_COLORS[k]}"><span class="lab">{a}</span><h4>{b}</h4><p>{c}</p></div>' for k, a, b, c in (
        ("vai", "VAI", "Composite index", "The average of Reach, Speed and Hold. Higher means stronger overall attention on the element."),
        ("reach", "VAI Reach", "Breadth", "How many viewers looked at it at all. <i>Did people get there?</i>"),
        ("speed", "VAI Speed", "Speed", "How soon they noticed it. <i>How early in the viewing order?</i> Used here to rank the viewing order."),
        ("hold", "VAI Hold", "Hold", "How long attention stayed on it. <i>Did people stay?</i>")))
    patterns = [
        ("High", "High", "High", "Strong element: almost everyone reaches it, soon, and stays on it.", "Keep it. Protect its position and size."),
        ("High", "High", "Low", "Seen fast by most viewers but only glanced at. Normal for a logo; a problem for a claim that must be read.", "If it must be read, shorten it or give it more room."),
        ("High", "Low", "any", "Reached eventually, but late: it competes with elements ahead of it in the viewing order.", "Move it earlier in the order or make it more salient."),
        ("Low", "Low", "Low", "Blind spot: few viewers reach it, late, and briefly.", "Relocate, enlarge, raise contrast, or remove clutter around it."),
        ("Low", "any", "High", "Hard to find, but viewers who find it read it: a placement problem, not a content problem.", "Move it into the path viewers already follow."),
    ]
    prow = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{f}</td></tr>" for a, b, c, d, f in patterns)
    body = ("<p class=\"lead\">VAI is RealEye's attention score for an element of the image (the tagline, the pack, the face, the logo). It runs from 0 to 100 and is the average of three simple measures, "
            "computed from the webcam eye tracking. Values are indices over the time window; they are not predictions and not percentages of total attention across the image.</p>"
            f'<div class="cards4">{cards}</div>'
            + note("How to use it:", "compare like with like, and look at the three measures rather than just the total. VAI is for comparing elements, designs, time windows and audiences. "
                   "A higher score is not always better: a logo can do its job at a moderate score, and what matters is that each element scores as the design intends. "
                   "VAI shows attention, not outcome: it does not say whether viewers understood, liked or will buy, so confirm with a recall or choice test.")
            + '<h4>Component patterns and what to do</h4><div class="tablewrap"><table class="re"><thead><tr><th>Reach</th><th>Speed</th><th>Hold</th><th>Reading</th><th>Typical action</th></tr></thead>'
            f'<tbody>{prow}</tbody></table></div>{example}')
    return section("vai", "What the scores mean (VAI)", body)


def vai_tech_notes():
    return f"""<h3>Technical notes on VAI</h3><ul class="plain">
<li><b>Compare like with like:</b> the same element, the same time window and a similar number of viewers (N). Large elements, and elements that overlap others, naturally score higher.</li>
<li><b>Windows are cumulative.</b> "First 3 s" is 0.5–3 s, "first 5 s" is 0.5–5 s and "first 10 s" is 0.5–10 s. The first 0.5 s is skipped to reduce the effect of where viewers happened to be looking when the image appeared. Reach and Speed can only rise as the window grows; Hold is relative to the window, so it can fall even when viewers keep looking.</li>
<li><b>Small groups are noisy.</b> Audiences with fewer than {MIN_N} viewers are marked † and should be read as anecdotal.</li>
<li><b>VAI is the equal-weight mean of Reach, Speed and Hold</b> and is not a share of the image's attention.</li></ul>"""


def ochip(v, nm, ai=0):
    return f'<span class="ochip" style="--c:{acolor(v, nm, ai)}">{swatch(acolor(v, nm, ai))}{e(nm)}</span>'


def order_flow(spec, v):
    """Overall viewing order as a flow of numbered steps with Speed bars, for each time window."""
    n, seg, out = names(spec), seg_of(v, "All"), ""
    for w in WIN:
        steps = ""
        for i, nm in enumerate(rank_names(spec, seg, w)):
            ai = n.index(nm)
            sp = val(seg, w, ai, "speed")
            steps += (f'<div class="step" style="--c:{acolor(v, nm, ai)}"><span class="no">{i + 1}</span>{ochip(v, nm, ai)}'
                      f'<div class="track"><i style="width:{max(sp, .6):.0f}%;background:{acolor(v, nm, ai)}"></i></div><small>Speed {sp:.0f} · Reach {val(seg, w, ai, "reach"):.0f}%</small></div>')
            steps += '<span class="arr">›</span>' if i < len(n) - 1 else ""
        out += f'<h5>{WIN_LABEL[w]}</h5><div class="flow">{steps}</div>'
    return out


def order_by_audience(spec, v):
    """Viewing order for every audience and window: elements in the order they are noticed, differences from the overall order outlined."""
    n = names(spec)
    html_ = ""
    for w in WIN:
        base_order = rank_names(spec, seg_of(v, "All"), w)
        rows, differ = "", []
        for sg in v["segments"]:
            order = rank_names(spec, sg, w)
            same = order == base_order
            if not same and sg["label"] != "All":
                differ.append(sg["label"] + (" †" if small(sg) else ""))
            cells = "".join(
                f'<td class="oc{"" if order[i] == base_order[i] else " diff"}{" low" if small(sg) else ""}">{ochip(v, order[i], n.index(order[i]))}'
                f'<small>Speed {val(sg, w, n.index(order[i]), "speed"):.0f}</small></td>' for i in range(len(n)))
            status = '<span class="ok">same as overall</span>' if same else "differs"
            rows += (f'<tr><th scope="row">{e(sg["label"])}<small>N = {sg["n"]}{" †" if small(sg) else ""}</small></th>{cells}<td class="st">{status if sg["label"] != "All" else "overall"}</td></tr>')
        total = len(v["segments"]) - 1
        summary = (f'{total - len(differ)} of {total} audiences notice the elements in the same order as all viewers.'
                   + (f' Different order: {e(", ".join(differ))}.' if differ else ""))
        html_ += (f'<h5>{WIN_LABEL[w]}</h5><p class="hint">{summary}</p><div class="tablewrap"><table class="re ord"><thead><tr><th>Audience</th>'
                  + "".join(f"<th>{ordinal}</th>" for ordinal in ("1st", "2nd", "3rd", "4th", "5th")[:len(n)]) + f'<th></th></tr></thead><tbody>{rows}</tbody></table></div>')
    return html_


def order_section(spec):
    variants = spec["variants"]
    n = names(spec)
    base = spec["_base"]
    blocks, stable_all = "", True
    for vi, v in enumerate(variants):
        seg = seg_of(v, "All")
        orders = {w: rank_names(spec, seg, w) for w in WIN}
        stable = len({tuple(o) for o in orders.values()}) == 1
        stable_all &= stable
        rows = ""
        for nm in orders["10"]:
            ai = n.index(nm)
            tds = "".join(f'<td class="vc"><b class="rk">#{orders[w].index(nm) + 1}</b><small>Speed {val(seg, w, ai, "speed"):.0f} · Reach {val(seg, w, ai, "reach"):.0f}%</small></td>' for w in WIN)
            rows += f'<tr><td>{swatch(acolor(v, nm, ai))}<b>{e(nm)}</b></td>{tds}</tr>'
        reach = "".join(
            f'<li><b>{WIN_LABEL[w]}:</b> {lst([f"{nm} ({val(seg, w, n.index(nm), "reach"):.0f}%)" for nm in orders[w] if val(seg, w, n.index(nm), "reach") >= 50]) or "no element"} reached by half of the viewers or more.</li>'
            for w in WIN)
        blocks += (f'<div class="ordercol"><h4>{chip(v["id"], e(v["id"]), "vtag", "background:" + vcolor(vi))} {e(v["name"])}</h4>'
                   f'<div class="stagebox">{stage(base, v, order_markers(spec, v))}</div>'
                   f'<p class="hint">{"The order is the same in the first 3, 5 and 10 seconds." if stable else "The order changes between windows (see below)."}</p>{order_flow(spec, v)}'
                   f'<div class="tablewrap"><table class="re seg"><thead><tr><th>Element</th>' + "".join(f"<th>{WIN_LABEL[w]}</th>" for w in WIN) +
                   f'</tr></thead><tbody>{rows}</tbody></table></div><ul class="plain">{reach}</ul></div>')
    same = len({tuple(rank_names(spec, seg_of(v, "All"), "10")) for v in variants}) == 1
    lead = (f"In {'both designs' if len(variants) > 1 else 'the design'} viewers notice the elements in this order: <b>{' → '.join(rank_names(spec, seg_of(variants[0], 'All'), '10'))}</b>"
            + (", and the order does not change between the first 3, 5 and 10 seconds." if stable_all and same else ".")
            if same else "The viewing order differs between the designs (see below).")
    olinks = " · ".join(f'Design {e(v["id"])}: ' + open_links(spec, v, parts=("aoi", "vai")) for v in variants if open_links(spec, v, parts=("aoi", "vai")))
    body = (f'<p class="lead">{lead}</p>'
            '<p class="hint">The order in which viewers notice the elements, across all viewers (not one person\'s scan path). #1 is noticed soonest; it is ranked by VAI Speed. The numbered circles show the first-10-seconds order.</p>'
            f'<div class="two">{blocks}</div>' + (f'<p class="hint">See the data in RealEye. {olinks}</p>' if olinks else "")
            + '<h3>Viewing order by audience</h3><p class="hint">For every audience (all viewers, gender, age, gender × age) and time window: the elements in the order they are noticed (1st to 5th), ranked by VAI Speed. An outlined cell is an element in a different place than for all viewers. † marks a small audience (fewer than %d viewers).</p>' % MIN_N
            + "".join(f'<h4>{chip(v["id"], e(v["id"]), "vtag", "background:" + vcolor(vi))} {e(v["name"])}</h4>{order_by_audience(spec, v)}' for vi, v in enumerate(variants)))
    return section("order", "Viewing order", body)


def design_sections(spec, v, vi):
    base, n = spec["_base"], names(spec)
    seg = seg_of(v, "All")
    links = open_links(spec, v)
    head = (f'<section class="sec design-head"><div class="dh">{chip(v["id"], e(v["id"]), "badge", "background:" + vcolor(vi))}'
            f'<div><h2>Design {e(v["id"])}: {e(v["name"])}</h2><p class="muted">{e(v.get("description", ""))}</p>'
            + (f'<p class="links">Open in RealEye: {links}</p>' if links else "") + f'</div><div class="nbox"><b>{seg["n"]}</b><span>viewers</span></div></div></section>')
    toggle = (f'<div class="aoicard"><div class="stagebox">{stage(base, v)}</div><div class="legend2"><label class="switch"><input type="checkbox" class="sw-in" checked>'
              f'<span class="trk"></span><span>Show AOIs</span></label><p class="hint">AOI regions are highlighted directly on the image.</p>'
              + "".join(f'<div class="li">{swatch(a.get("color", "#999"))}{e(a["name"])}</div>' for a in v["aois"])
              + '<p class="box">Each element is an Area of Interest (AOI) measured separately; elements may overlap.</p></div></div>')
    image_card = section(None, "Image with AOIs", toggle)
    heat_card = section(None, "Measured heatmap", note("How to read it:", "warm colours (yellow, orange, red) mark where viewers looked most; cool colours (blue) mark where they looked least. "
                        "The heatmap is built from the webcam eye-tracking fixations of this study's viewers (first 10 seconds, all viewers).")
                        + f'<div class="heat">{figure(base, v.get("heatmap"), "Measured heatmap", "All viewers, first 10 seconds.")}</div>')
    best = lambda k: max(range(len(n)), key=lambda i: val(seg, "10", i, k))
    worst = lambda k: min(range(len(n)), key=lambda i: val(seg, "10", i, k))
    b = lambda i: f'<b>"{e(n[i])}"</b>'
    glance = "".join(f'<div class="xtile"><span class="lab">{lab}</span><p>{txt}</p></div>' for lab, txt in (
        ("Top element by VAI", f'{b(best("vai"))} has the highest VAI ({val(seg, "10", best("vai"), "vai"):.1f}/100).'),
        ("Highest VAI Speed", f'{b(best("speed"))} is noticed soonest ({val(seg, "10", best("speed"), "speed"):.1f}/100).'),
        ("Highest VAI Hold", f'{b(best("hold"))} holds attention longest ({val(seg, "10", best("hold"), "hold"):.1f}/100).'),
        ("Lowest VAI Reach", f'{b(worst("reach"))} is reached by the smallest share of viewers ({val(seg, "10", worst("reach"), "reach"):.1f}/100).')))
    glance_card = section(None, "At a glance", f'<div class="xgrid">{glance}</div><p class="hint">All viewers, first 10 seconds.</p>')
    insights = section(None, "What the data says", "".join(insight(t) for t in v.get("findings", [])))
    cards = "".join(
        f'<div class="aoicard2">{aoi_crop(base, v, a)}<div class="meta"><b>{e(a["name"])}</b><p>VAI <b>{val(seg, "10", i, "vai"):.1f}</b><span>·</span>Reach <b>{val(seg, "10", i, "reach"):.1f}</b>'
        f'<span>·</span>Speed <b>{val(seg, "10", i, "speed"):.1f}</b><span>·</span>Hold <b>{val(seg, "10", i, "hold"):.1f}</b></p></div><i class="cbar" style="background:{a.get("color", "#999")}"></i></div>'
        for i, a in enumerate(v["aois"]))
    overview = section(None, "AOIs overview", f'<div class="cards3">{cards}</div><p class="hint">All viewers, first 10 seconds. VAI and its components, 0–100.</p>')
    summary = section(None, "VAI summary", '<p class="hint">Measured VAI and its Reach / Speed / Hold per element, all viewers, first 10 seconds. Values are indices (0–100), not shares; elements overlap and do not need to total 100%.</p>'
                      + vai_summary(spec, v) + '<h4>VAI component averages per element</h4>' + comp_bars(spec, v, seg, "10") + '<h4>VAI by time window</h4>' + window_table(spec, v))
    series = lambda k: {nm: ([val(seg, w, i, k) for w in WIN], acolor(v, nm, i)) for i, nm in enumerate(n)}
    xl = ["first 3 s", "first 5 s", "first 10 s"]
    mini = "".join(f'<div><h5>{lab} by window</h5>{lines(series(k), xl, lab)}</div>' for k, lab in COMP)
    build_up = section(None, "How attention builds up over time", legend([(nm, acolor(v, nm, i)) for i, nm in enumerate(n)]) + f'<div class="grid2">{mini}</div>')
    aud = section(None, "By gender, age and gender × age",
                  '<p class="hint">Each cell is the VAI for that audience, element and window, with Reach · Speed · Hold underneath. † marks a small audience (fewer than %d viewers): read it as indicative.</p>' % MIN_N
                  + segment_table(spec, v, "gender", "By gender") + segment_table(spec, v, "age", "By age") + segment_table(spec, v, "gender_age", "By gender × age"))

    def sheet(w):
        ls = " · ".join(alink(dash_url(spec, v, "heatmap", sg["label"], int(w)), sg["label"], "ext s") for sg in v["segments"] if dash_url(spec, v, "heatmap", sg["label"], int(w)))
        return (f'<h5>Heatmaps, {WIN_LABEL[w]}</h5><div class="sheet">{figure(base, v["heatmap_sheets"][w], f"Heatmaps by audience, {WIN_LABEL[w]}")}</div>'
                + (f'<p class="links small">Open in the RealEye heatmap: {ls}</p>' if ls else ""))
    sheets = section(None, "Heatmaps by audience and time window", f'<p class="hint">{rich(v.get("heatmap_note", ""))}</p>' + "".join(sheet(w) for w in WIN if w in v.get("heatmap_sheets", {})))
    return head + image_card + heat_card + glance_card + insights + overview + summary + build_up + aud + sheets


def compare_section(spec):
    variants = spec["variants"]
    if len(variants) < 2:
        return ""
    A, B = variants[0], variants[1]
    n = names(spec)
    sa, sb = seg_of(A, "All"), seg_of(B, "All")
    charts = "".join(f'<h4>VAI by element, {WIN_LABEL[w]}</h4>' + hbars(n, [(f'{A["id"]} · {A["name"]}', vcolor(0), [val(sa, w, i, "vai") for i in range(len(n))]),
                                                                           (f'{B["id"]} · {B["name"]}', vcolor(1), [val(sb, w, i, "vai") for i in range(len(n))])], "VAI") for w in WIN)
    rows = ""
    for ai, nm in enumerate(n):
        tds = ""
        for w in WIN:
            d = {k: val(sb, w, ai, k) - val(sa, w, ai, k) for k, _ in COMP}
            na, nb = max(sa["n"], 1), max(sb["n"], 1)
            p1, p2 = round(val(sa, w, ai, "reach") / 100 * na) / na, round(val(sb, w, ai, "reach") / 100 * nb) / nb
            se = math.sqrt(p1 * (1 - p1) / na + p2 * (1 - p2) / nb)
            lo, hi = (p2 - p1) * 100 - 1.96 * se * 100, (p2 - p1) * 100 + 1.96 * se * 100
            ind = bool(se) and (lo > 0 or hi < 0)
            tds += (f'<td class="vc"><b>{d["vai"]:+.1f}</b><small>R {d["reach"]:+.1f} · S {d["speed"]:+.1f} · H {d["hold"]:+.1f}</small>'
                    f'<small class="{"ok" if ind else ""}">Reach gap {"indicative" if ind else "within noise"}</small></td>')
        rows += f'<tr><td>{swatch(acolor(A, nm, ai))}<b>{e(nm)}</b></td>{tds}</tr>'
    lk = ' · '.join('Design ' + e(x["id"]) + ': ' + open_links(spec, x, parts=("aoi", "heatmap")) for x in (A, B)) if open_links(spec, A) else ""
    body = (f'<p class="hint">Differences are {e(B["id"])} minus {e(A["id"])}, in VAI points. R, S and H are the Reach, Speed and Hold differences. "Indicative" means the Reach gap is larger than chance would explain; '
            'the viewer groups may overlap, so treat it as a signal, not proof.</p>'
            f'<div class="tablewrap"><table class="re seg"><thead><tr><th>Element</th>' + "".join(f"<th>{WIN_LABEL[w]}</th>" for w in WIN) + f'</tr></thead><tbody>{rows}</tbody></table></div>'
            + '<div class="legend">' + "".join(f'<span>{swatch(vcolor(i))}{chip(x["id"], e(x["id"]))} · {e(x["name"])}</span>' for i, x in enumerate((A, B))) + '</div>' + charts + (f'<p class="links small">Open in RealEye: {lk}</p>' if lk else ""))
    return section("compare", f"Head-to-head: design {e(B['id'])} versus design {e(A['id'])}", body)


def audience_section(spec):
    variants = spec["variants"]
    text = "".join(insight(x) for x in spec.get("segment_findings", []))
    ages = [s["label"] for s in variants[0]["segments"] if s["kind"] == "age"]
    ga = gap_table(spec, variants, "18–24", "25–34", "Viewers 25–34 minus viewers 18–24 (the 25–34 group is small: anecdotal)") if "18–24" in ages and "25–34" in ages else ""
    lk = ' · '.join('Design ' + e(x["id"]) + ': ' + open_links(spec, x, "Women", None, ("aoi", "heatmap")) + ' (women)' for x in variants) if open_links(spec, variants[0]) else ""
    body = (text + gap_table(spec, variants, "Men", "Women", "Women minus men (VAI points)") + gap_table(spec, variants, "Men 18–24", "Women 18–24", "Women 18–24 minus men 18–24 (the largest groups)") + ga
            + f'<p class="hint">† Small audiences (fewer than {MIN_N} viewers) are indicative only. Full tables and heatmaps are in each design\'s section.</p>' + (f'<p class="links small">Open in RealEye: {lk}</p>' if lk else ""))
    return section("audience", "Gender and age insights", body)


def dashboard_vai(spec, v, vi):
    d = v.get("dashboard_vai")
    if not d:
        return ""
    summ, wins, base = d["summary"], d["windows"], spec["_base"]
    nm = list(summ.keys())
    best = lambda k: max(nm, key=lambda x: summ[x][k])
    worst = lambda k: min(nm, key=lambda x: summ[x][k])
    ex = "".join(f'<div class="xtile"><span class="lab">{t}</span><p><b>{e(x)}</b> {e(s)}</p></div>' for t, x, s in (
        ("Top AOI by VAI", best("vai"), f'has the highest measured VAI index ({summ[best("vai")]["vai"]:.1f}/100).'),
        ("Highest VAI Speed", best("speed"), f'is noticed soonest ({summ[best("speed")]["speed"]:.1f}/100).'),
        ("Highest VAI Hold", best("hold"), f'holds attention longest ({summ[best("hold")]["hold"]:.1f}/100).'),
        ("Lowest VAI Reach", worst("reach"), f'is reached by the smallest share of participants ({summ[worst("reach")]["reach"]:.1f}/100).')))
    cols = {k: pill_vals([summ[x][k] for x in nm]) for k, _ in COMP}
    rows = "".join(f'<tr><td class="num">{i + 1}</td><td>{swatch(acolor(v, x, i))}<b>{e(x)}</b></td>' + "".join(f"<td>{cols[k][i]}</td>" for k, _ in COMP) + f'<td>{d["participants"]}</td></tr>' for i, x in enumerate(nm))
    tabs = ""
    for k, lab in COMP:
        r = "".join(f'<tr><td><b>{e(x)}</b></td><td><b>{summ[x][k]:.1f}</b></td>' + "".join(f"<td>{t:.1f}</td>" for t in d["by_window"][k][x]) + "</tr>" for x in nm)
        tabs += f'<h5>{lab} per cumulative window</h5><div class="tablewrap"><table class="re"><thead><tr><th>AOI</th><th>Average</th>' + "".join(f"<th>{e(w)}</th>" for w in wins) + f"</tr></thead><tbody>{r}</tbody></table></div>"
    ins = "".join(insight(x) for x in d.get("insights", []))
    return (f'<details class="dash"><summary>{chip(v["id"], e(v["id"]), "badge sm", "background:" + vcolor(vi))} Dashboard AOI VAI report, {chip(v["id"], "design " + e(v["id"]))} <small class="muted">· {e(d.get("scope", ""))}</small></summary>'
            f'<p class="box">{e(d.get("note", ""))} {alink(dash_url(spec, v, "vai"), "Open the AOI VAI report in RealEye")}</p>'
            f'<div class="two"><div class="stagebox">{stage(base, v)}</div><div><h5>Executive summary</h5><div class="xgrid one">{ex}</div></div></div>'
            f'<h5>VAI summary (average of the cumulative windows)</h5><div class="tablewrap"><table class="re"><thead><tr><th class="num">#</th><th>AOI name</th><th>VAI</th><th>VAI Reach</th><th>VAI Speed</th><th>VAI Hold</th><th>Participants</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'{tabs}' + (f'<h5>Actionable insights from the dashboard report</h5>{ins}' if ins else "") + "</details>")


def intro_section(spec):
    """Intro card: the tested images with their AOIs outlined, what each AOI covers, and links to the RealEye dashboard."""
    base = spec["_base"]
    cols = ""
    for vi, v in enumerate(spec["variants"]):
        seg = seg_of(v, "All")
        links = open_links(spec, v)
        items = "".join(f'<div class="li">{swatch(a.get("color", "#999"))}<div><b>{e(a["name"])}</b><span>{e(a.get("role", ""))}</span></div></div>' for a in v["aois"])
        cols += (f'<div class="aoitog tcol"><div class="thead">{chip(v["id"], e(v["id"]), "badge", "background:" + vcolor(vi))}'
                 f'<div><h4>Design {e(v["id"])}: {e(v["name"])}</h4><p class="muted">{e(v.get("description", ""))}</p></div></div>'
                 f'<div class="stagebox">{stage(base, v)}</div>'
                 '<label class="switch"><input type="checkbox" class="sw-in" checked><span class="trk"></span><span>Show AOIs</span></label>'
                 f'<div class="alist">{items}</div>'
                 f'<p class="links small">{seg["n"]} viewers' + (f" · Open in RealEye: {links}" if links else "") + "</p></div>")
    body = ('<p class="hint">The images tested in this study and the elements analysed. Each outlined element is an Area of Interest (AOI) that is measured separately; '
            'the same elements are used throughout the report. Switch the outlines off to see the clean image.</p>' + f'<div class="two">{cols}</div>')
    return section("tested", "Tested designs and the elements analysed", body)


def agent_prompt(spec):
    """A self-contained prompt for an AI agent: the whole report (method, definitions, designs, AOIs, every number, findings) plus rules for answering."""
    m, o, variants, n = spec["method"], spec["overall"], spec["variants"], names(spec)
    c = lambda t: re.sub(r"\{([A-Z])\}", r"\1", str(t))
    L = []
    add = L.append
    add("You are a senior neuromarketing and eye-tracking analyst. Below is the complete content of a report produced from a RealEye study. "
        "Read all of it. Then answer my questions about it, run further analyses on the data, and offer other insights you think are useful. "
        "Use only the data and context in this message; if something is not here, say so instead of guessing.")
    add("")
    add("=== STUDY ===")
    add(f"Title: {c(spec.get('title', ''))}")
    add(f"Date: {c(spec.get('date', ''))}")
    for k, lab in (("platform", "Platform"), ("tracking", "Eye tracking"), ("study", "Study"), ("participants", "Participants analysed"), ("quality_filter", "Participant quality filter"),
                   ("windows", "Time windows"), ("segments", "Audiences"), ("task", "Task and exposure"), ("source", "Source"), ("precision", "Tracker precision"), ("note", "Note")):
        if m.get(k):
            add(f"{lab}: {c(m[k])}")
    if spec.get("agent_context"):
        add(f"Extra context: {c(spec['agent_context'])}")
    add("")
    add("=== HOW TO READ THE METRICS ===")
    add("The report uses ONLY RealEye's VAI (Visual Attention Index, 0-100) and its three components. Never use or invent other metrics such as time to first fixation.")
    add("- VAI = equal-weight mean of Reach, Speed and Hold. It is a relative index, not a percentage of viewers or of attention. Compare like with like (same element, window, audience size).")
    add("- Reach: share of viewers who looked at the element at least once in the window.")
    add("- Speed: how soon the element is noticed after it becomes visible. Ranking elements by Speed gives the viewing order (a relative hierarchy across viewers, not one person's scan path).")
    add("- Hold: how long attention stays on the element relative to the window. It can fall as the window grows even when viewers keep looking.")
    add("- Windows are cumulative and start at 0.5 s: 'first 3 s' = 0.5-3 s, 'first 5 s' = 0.5-5 s, 'first 10 s' = 0.5-10 s.")
    add(f"- Audiences with fewer than {MIN_N} viewers are anecdotal (marked with a dagger in the report); say so when you use them. Viewers with other or unspecified gender, or no recorded age, are in 'All' but not in the gender or age cuts.")
    add("- VAI shows attention, not understanding, liking, recall or purchase. Never claim an effectiveness winner without outcome data.")
    add("")
    add("=== DESIGNS AND ELEMENTS (AOIs) ===")
    for v in variants:
        add(f"Design {v['id']}: {c(v['name'])}. {c(v.get('description', ''))} Viewers analysed: {seg_of(v, 'All')['n']}.")
        for a in v["aois"]:
            if a.get("shape"):
                x0, y0, x1, y1 = bbox(a["shape"])
                where = f" Location: x {x0:.0f}-{x1:.0f}%, y {y0:.0f}-{y1:.0f}% of the image (0,0 = top-left)."
            else:
                where = ""
            add(f"  - {a['name']}: {c(a.get('role', ''))}.{where}")
    add("")
    add("=== DATA: VAI / Reach / Speed / Hold (0-100) per element, design, audience and time window ===")
    add("Format per element: Name VAI/Reach/Speed/Hold")
    for v in variants:
        for sg in v["segments"]:
            add(f"Design {v['id']} | audience: {sg['label']} | N={sg['n']}{' (small, anecdotal)' if small(sg) else ''} | kind: {sg['kind']}")
            for w in WIN:
                cells = "; ".join(f"{nm} {val(sg, w, i, 'vai'):g}/{val(sg, w, i, 'reach'):g}/{val(sg, w, i, 'speed'):g}/{val(sg, w, i, 'hold'):g}" for i, nm in enumerate(n))
                add(f"  {WIN_LABEL[w]}: {cells}")
    dv = [v for v in variants if v.get("dashboard_vai")]
    if dv:
        add("")
        add("=== DASHBOARD AOI VAI REPORT (all participants with data, NOT quality-filtered; windows 0.5-3, 0.5-5, 0.5-10 s) ===")
        for v in dv:
            d = v["dashboard_vai"]
            add(f"Design {v['id']} | participants: {d['participants']}")
            for nm in d["summary"]:
                sm = d["summary"][nm]
                add(f"  {nm}: average VAI {sm['vai']:g}, Reach {sm['reach']:g}, Speed {sm['speed']:g}, Hold {sm['hold']:g}; "
                    + "; ".join(f"{k} by window {'/'.join(f'{x:g}' for x in d['by_window'][k][nm])}" for k in ("vai", "reach", "speed", "hold")))
    add("")
    add("=== THE REPORT'S FINDINGS AND CONCLUSIONS ===")
    add(f"Conclusion: {c(o.get('verdict_label', ''))}. {c(o.get('verdict_text', ''))}")
    add(c(o.get("summary", "")))
    for f in o.get("findings", []):
        add(f"- [{f.get('tag', '')}] {c(f['title'])}: {c(f['text'])}")
    for x in o.get("conclusions", []):
        add(f"- Conclusion: {c(x)}")
    for v in variants:
        for x in v.get("findings", []):
            add(f"- Design {v['id']}: {c(x)}")
    for x in spec.get("segment_findings", []):
        add(f"- Gender/age: {c(x)}")
    add("")
    add("=== RECOMMENDED ACTIONS AND RETEST PLAN ===")
    for a in spec.get("actions", []):
        add(f"- {c(a['title'])}: {c(a['text'])}" + (f" Preserve: {c(a['preserve'])}" if a.get("preserve") else ""))
    for k, x in spec.get("retest", {}).items():
        add(f"- Retest {k.replace('_', ' ')}: {c(x)}")
    add("")
    add("=== LIMITS OF THE EVIDENCE ===")
    for x in spec.get("limits", []):
        add(f"- {c(x)}")
    for x in spec.get("would_change", []):
        add(f"- Would change the recommendation: {c(x)}")
    links = [(v, u) for v in variants for u in (dash_url(spec, v, "heatmap"), dash_url(spec, v, "aoi"), dash_url(spec, v, "vai")) if u]
    if links:
        add("")
        add("=== RealEye DASHBOARD LINKS (need a signed-in RealEye account; use them only if you have browser access) ===")
        for v in variants:
            add(f"Design {v['id']}: heatmap {dash_url(spec, v, 'heatmap')} | AOI report {dash_url(spec, v, 'aoi')} | AOI VAI report {dash_url(spec, v, 'vai')}")
    add("")
    add("=== HOW TO ANSWER ===")
    add("1. Base every answer on the data above. Quote the numbers with the design, audience, time window and N (for example: 'Design A, Women, first 3 s, N=88: Tagline VAI 65.4').")
    add("2. Compute what I ask for: differences between designs, audiences and windows; rankings; viewing order per audience; gaps; build-up over time; which audiences behave differently. Show the arithmetic briefly.")
    add("3. Separate observation (the data), interpretation (what it likely means) and hypothesis (what to test). Do not present a hypothesis as a finding.")
    add("4. Flag small audiences and differences that may be noise. Do not over-read gaps of a few VAI points.")
    add("5. If I ask something the data cannot answer (recall, liking, sales, other metrics, audiences or windows not listed), say so and suggest how to measure it.")
    add("6. Be concise and plain-spoken: I may be a brand manager. Lead with the answer, then the evidence. Use tables when comparing.")
    add("7. Proactively suggest insights I did not ask for when they matter (blind spots, surprising audience differences, order changes, quick wins, test ideas).")
    add("")
    add("=== IDEAS TO EXPLORE (offer these, and any others you think of) ===")
    for q in ("Which element is the weakest blind spot overall and for each audience, and what would you change first?",
              "Where does the viewing order differ between audiences or designs, and why might that matter?",
              "Which audience pays the most and the least attention to the brand name and logo, in each window?",
              "How does attention build up from the first 3 s to the first 10 s for each element, and which element gains most?",
              "Compare the designs for one audience of my choice (for example women 18-24) in every window.",
              "Which differences between designs look real and which are probably noise, given the audience sizes?",
              "Draft a short brief for the creative team: what to keep, what to change, what to test.",
              "Design a recall and message-takeout survey to confirm what these attention results suggest.",
              "Propose three layout variants to test next, with the expected effect on each element's Reach, Speed and Hold.",
              "Write a one-slide summary and a five-bullet executive summary of this report."):
        add(f"- {q}")
    add("")
    add("First, confirm you have read everything: summarise the study and the main conclusion in five lines, list the data you can analyse, then ask me what I want to explore.")
    return "\n".join(L)


def agent_section(spec):
    prompt = agent_prompt(spec)
    body = ('<p class="lead">Want to go further? Copy the prompt below into your AI assistant (Claude, ChatGPT or similar). It carries the whole report: the study, how to read VAI, '
            'the designs and elements, every VAI, Reach, Speed and Hold number for every audience and time window, the findings, actions and limits. The assistant can then answer follow-up questions, '
            'run extra comparisons and suggest insights you did not think to ask for.</p>'
            '<div class="btnrow"><button class="btn" type="button" data-act="copy">Copy prompt</button><button class="btn" type="button" data-act="download">Download as .txt</button></div>'
            f'<textarea id="agent-prompt" readonly rows="18" spellcheck="false">{e(prompt)}</textarea>'
            f'<p class="hint">{len(prompt):,} characters. It contains your results, so share it only with tools you trust. The dashboard links in it work only for people signed in to RealEye.</p>')
    return section("agent", "Continue the analysis with an AI agent", body)


POP2 = ('<script>(function(){document.addEventListener("click",function(ev){var b=ev.target.closest&&ev.target.closest("[data-act]");if(!b)return;var t=document.getElementById("agent-prompt");if(!t)return;'
        'if(b.dataset.act==="copy"){var done=function(){var o=b.textContent;b.textContent="Copied to clipboard";setTimeout(function(){b.textContent=o},1800)};'
        'if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t.value).then(done,function(){t.select();document.execCommand("copy");done()})}else{t.select();document.execCommand("copy");done()}}'
        'else if(b.dataset.act==="download"){var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([t.value],{type:"text/plain"}));a.download="neuromarketing-report-ai-prompt.txt";document.body.appendChild(a);a.click();a.remove()}})})();</script>')


def method_block(spec):
    m = spec["method"]
    rows = "".join(f'<div><dt>{e(k)}</dt><dd>{rich(x)}</dd></div>' for k, x in (
        ("Platform", m.get("platform")), ("Eye tracking", m.get("tracking")), ("Study", m.get("study")), ("Participants analysed", m.get("participants")),
        ("Participant quality filter", m.get("quality_filter")), ("Time windows", m.get("windows")), ("Audiences", m.get("segments")),
        ("Task and exposure", m.get("task")), ("Source", m.get("source")), ("Tracker precision", m.get("precision"))) if x)
    return f'<h3>About this study</h3><dl class="ctx">{rows}</dl><p class="hint">{e(m.get("note", ""))}</p>'


POP = '<script>(function(){var p=document.createElement("div");p.id="dpop";document.body.appendChild(p);function show(el){while(p.firstChild)p.removeChild(p.firstChild);var t=document.createElement("div");t.className="th pic "+el.dataset.cls;var b=document.createElement("b");b.textContent="Design "+el.dataset.id;var s=document.createElement("small");s.textContent=el.dataset.name;p.appendChild(t);p.appendChild(b);p.appendChild(s);p.style.display="block";var r=el.getBoundingClientRect(),w=p.offsetWidth,h=p.offsetHeight,x=Math.min(Math.max(8,r.left),window.innerWidth-w-8),y=r.bottom+6;if(y+h>window.innerHeight-8)y=Math.max(8,r.top-h-6);p.style.left=x+"px";p.style.top=y+"px"}function hide(){p.style.display="none"}function ref(ev){return ev.target.closest&&ev.target.closest(".dref")}document.addEventListener("mouseover",function(ev){var el=ref(ev);if(el)show(el)});document.addEventListener("mouseout",function(ev){if(ref(ev))hide()});document.addEventListener("focusin",function(ev){var el=ref(ev);if(el)show(el)});document.addEventListener("focusout",function(ev){if(ref(ev))hide()});document.addEventListener("click",function(ev){var el=ref(ev);if(el)show(el);else hide()});document.addEventListener("keydown",function(ev){if(ev.key==="Escape"){hide();hg()}});})();(function(){var g=document.createElement("div");g.id="gpop";document.body.appendChild(g);function gl(ev){return ev.target.closest&&ev.target.closest(".gl")}function sg(el){g.textContent=el.dataset.tip;g.style.display="block";var r=el.getBoundingClientRect(),w=g.offsetWidth,h=g.offsetHeight,x=Math.min(Math.max(8,r.left),window.innerWidth-w-8),y=r.bottom+6;if(y+h>window.innerHeight-8)y=Math.max(8,r.top-h-6);g.style.left=x+"px";g.style.top=y+"px"}window.hg=function(){g.style.display="none"};document.addEventListener("mouseover",function(ev){var el=gl(ev);if(el)sg(el)});document.addEventListener("mouseout",function(ev){if(gl(ev))hg()});document.addEventListener("click",function(ev){var el=gl(ev);if(el)sg(el);else hg()});})();</script>'

CSS = """
:root{--bg:#f6f5f3;--card:#fff;--ink:#333;--strong:#1a1a1a;--muted:#5c5c5c;--soft:#8b8b8b;--line:#e7e4e0;--line2:#f0edea;--thbg:#fbfaf9;--accent:#fc7753;
--tag-bg:#ede3f7;--tag-fg:#6b3fa0;--best-bg:#e4f3e8;--best-fg:#17652f;--worst-bg:#fbe9e7;--worst-fg:#a12a1b;--insight:#fff1ec}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 Barlow,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.bar{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:16px;padding:0 24px;height:58px}
.logo{display:inline-flex;align-items:center;font-weight:700;font-size:19px;color:var(--strong);letter-spacing:-.2px}.logo b{background:var(--accent);color:#fff;border-radius:50%;width:27px;height:27px;display:grid;place-items:center;font-size:15px;margin-right:1px}
.bar .sep{width:1px;height:26px;background:var(--line)}.bar .study{font-weight:700;color:var(--strong);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px}
.bar nav{margin-left:auto;display:flex;gap:4px;overflow-x:auto;height:100%}.bar nav a{display:flex;align-items:center;padding:0 12px;color:var(--muted);text-decoration:none;font-weight:600;font-size:14px;white-space:nowrap;border-bottom:3px solid transparent}
.bar nav a:hover{color:var(--strong);border-bottom-color:var(--accent)}
.page{max-width:1000px;margin:0 auto;padding:30px 24px 70px}
.kicker{display:flex;align-items:center;gap:8px;margin-bottom:6px}.re-tag{background:var(--tag-bg);color:var(--tag-fg);font-size:11px;font-weight:700;padding:3px 8px;text-transform:uppercase;letter-spacing:.4px}
.kicker span.t{color:var(--tag-fg);font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.7px}
h1{font-size:34px;line-height:1.15;font-weight:700;color:var(--strong);margin:0 0 6px}
.hd{display:flex;gap:20px;align-items:flex-start;justify-content:space-between}.hd p{margin:0;color:var(--muted);font-size:15.5px;max-width:700px}
.btn{background:#fff;border:1px solid var(--line);padding:12px 18px;font:600 15px Barlow,sans-serif;color:var(--strong);cursor:pointer;display:inline-flex;gap:8px;align-items:center;white-space:nowrap}.btn:hover{border-color:var(--accent)}
.strip{display:flex;gap:14px;align-items:center;background:#fff;border:1px solid var(--line);padding:16px 20px;margin:18px 0 14px}.strip svg{flex:none}.strip b{color:var(--strong);display:block}.strip span{color:var(--muted)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:20px}
.tile{background:#fff;border:1px solid var(--line);padding:18px 18px 16px}.tile .lab,.lab{display:block;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.72px;color:var(--muted)}
.tile b{display:block;font-size:24px;line-height:1.2;color:var(--strong);margin:8px 0 4px;font-weight:700}.tile .sub{color:var(--muted);font-size:14px}
.sec{background:#fff;border:1px solid var(--line);padding:28px 32px;margin:0 0 20px}.sec>h2{font-size:22.5px;font-weight:700;color:var(--strong);margin:0 0 16px}
h3{font-size:18px;margin:28px 0 10px;color:var(--strong);padding-top:18px;border-top:1px solid var(--line)}h4{font-size:16px;margin:22px 0 8px;color:var(--strong)}h5{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.72px;color:var(--muted);margin:20px 0 8px}
.lead{font-size:16.5px;margin:0 0 14px;color:var(--ink)}.muted{color:var(--muted)}.hint{color:var(--muted);font-size:13.5px;margin:8px 0}.small{font-size:13px}
.callout{background:var(--insight);border-left:4px solid var(--accent);padding:16px 20px;margin:0 0 16px}.callout .lab{color:var(--accent)}.callout p{margin:6px 0 0;font-size:17px;color:var(--strong)}
.note{background:var(--bg);padding:14px 16px;margin:14px 0;color:var(--muted)}.note b{color:var(--strong)}.box{background:var(--bg);padding:12px 14px;color:var(--muted);font-size:13.5px;margin:12px 0}
.insight{display:flex;gap:12px;background:var(--insight);padding:14px 16px;margin:0 0 8px;align-items:flex-start}.insight .chk{flex:none;margin-top:3px}.insight b{color:var(--strong)}
.xgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.xgrid.one{grid-template-columns:1fr}.xtile{border:1px solid var(--line);padding:14px 16px}.xtile p{margin:6px 0 0}
.cards4{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:14px 0}.cc{border:1px solid var(--line);border-top:3px solid var(--accent);padding:14px 16px 16px}.cc h4{margin:8px 0 6px;font-size:20px}.cc p{margin:0;color:var(--muted)}
.cards3{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}.aoicard2{border:1px solid var(--line);position:relative;background:#fff}.aoicard2 .meta{padding:12px 14px 14px}.aoicard2 .meta p{margin:6px 0 0;color:var(--muted);font-size:14px}.aoicard2 .meta p b{color:var(--strong)}.aoicard2 .meta span{margin:0 6px;color:#c9c5bf}.aoicard2 .cbar{display:block;height:3px}
.crop{width:100%;background-repeat:no-repeat;background-color:#eee}
.pic{background-repeat:no-repeat;background-size:100% 100%;width:100%}.stage{position:relative;max-width:520px}.aoi-svg{position:absolute;inset:0;width:100%;height:100%}.stagebox{max-width:520px}
.aoicard{display:grid;grid-template-columns:minmax(220px,520px) 1fr;gap:24px;align-items:start}.legend2 .li{display:flex;align-items:center;gap:8px;margin:6px 0}.aoicard:has(.sw-in:not(:checked)) .aoi-svg,.aoitog:has(.sw-in:not(:checked)) .aoi-svg{display:none}
.switch{display:flex;align-items:center;gap:10px;font-weight:600;color:var(--strong);cursor:pointer;position:relative}.switch input{position:absolute;opacity:0}.switch .trk{width:44px;height:24px;background:#d9d5cf;position:relative;flex:none}.switch .trk:after{content:"";position:absolute;top:3px;left:3px;width:18px;height:18px;background:#fff}
.switch input:checked+.trk{background:var(--accent)}.switch input:checked+.trk:after{left:23px}
.mk{position:absolute;transform:translate(-50%,-50%);width:30px;height:30px;border-radius:50%;background:#212529;color:#fff;font-weight:700;font-size:15px;display:grid;place-items:center;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.45)}
.heat{max-width:520px}.sheet{margin:6px 0}figure{margin:0}figcaption{font-size:13px;color:var(--muted);margin-top:6px}
.design-head{padding:22px 32px}.dh{display:flex;gap:16px;align-items:center;flex-wrap:wrap}.dh>div:nth-child(2){flex:1;min-width:220px}.dh h2{margin:0;font-size:22.5px}.dh p{margin:4px 0 0}
.badge{width:42px;height:42px;color:#fff;font-weight:700;display:grid;place-items:center;font-size:20px;flex:none}.badge.sm{width:24px;height:24px;font-size:13px;display:inline-grid;vertical-align:middle;margin-right:6px}
.vtag{display:inline-block;min-width:22px;padding:0 6px;color:#fff;font-weight:700;text-align:center;font-size:12.5px}.nbox{text-align:right}.nbox b{display:block;font-size:26px;color:var(--strong)}.nbox span{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.7px}
.tablewrap{overflow-x:auto}table.re{width:100%;border-collapse:collapse;font-size:15px;border:1px solid var(--line)}
table.re th,table.re td{padding:11px 12px;border-bottom:1px solid var(--line2);text-align:left;vertical-align:middle}table.re thead th{background:var(--thbg);font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.72px;color:var(--muted);border-bottom:1px solid var(--line)}
table.re tbody th{font-weight:600;color:var(--strong)}table.re .num{width:48px;color:var(--muted)}table.re small{display:block;color:var(--soft);font-weight:400;font-size:12px}table.re thead small{text-transform:none;letter-spacing:0}
table.seg td,table.seg thead th{text-align:center}table.seg td:first-child,table.seg thead th:first-child,table.seg tbody th{text-align:left}table.seg th.w{font-weight:400;color:var(--muted);font-size:13px;white-space:nowrap}
tr.grp th,tr.grp td{border-top:2px solid var(--line)}td.vc b{font-size:16px;color:var(--strong)}td.low{opacity:.55}td.big{background:var(--insight)}.rk{font-size:17px}small.ok{color:var(--best-fg)!important;font-weight:600}
.sw{display:inline-block;width:12px;height:12px;margin-right:8px;vertical-align:-1px}.sw.best{background:var(--best-bg);border:1px solid var(--best-fg)}.sw.worst{background:var(--worst-bg);border:1px solid var(--worst-fg)}
.vp{display:inline-block;padding:3px 9px;font-weight:600}.vp.best{background:var(--best-bg);color:var(--best-fg)}.vp.worst{background:var(--worst-bg);color:var(--worst-fg)}
.comp-chart .crow{display:grid;grid-template-columns:200px 1fr;gap:14px;padding:12px 0;border-bottom:1px solid var(--line2);align-items:center}.cname{font-weight:600;color:var(--strong)}
.brow{display:grid;grid-template-columns:1fr 46px;gap:10px;align-items:center;margin:3px 0}.brow b{font-size:13px;color:var(--strong)}.track{height:9px;background:#ece9e5}.track i{display:block;height:100%}
.gl{cursor:help;border-bottom:1px dotted var(--soft)}
#gpop{position:fixed;z-index:101;display:none;max-width:300px;background:#1a1a1a;color:#fff;padding:9px 12px;font-size:13px;line-height:1.4;box-shadow:0 6px 22px rgba(0,0,0,.3);pointer-events:none;text-transform:none;letter-spacing:0;font-weight:400}
.dref{cursor:help;border-bottom:1px dotted var(--soft)}.dref.vtag,.dref.badge{border-bottom:0}.dref:focus{outline:2px solid var(--accent);outline-offset:1px}
#dpop{position:fixed;z-index:100;display:none;background:#fff;border:1px solid var(--line);box-shadow:0 8px 28px rgba(0,0,0,.2);padding:8px;width:152px;pointer-events:none}#dpop .th{width:136px;aspect-ratio:2/3}#dpop b{display:block;margin-top:6px;color:var(--strong)}#dpop small{display:block;color:var(--muted);line-height:1.25}
.flow{margin:4px 0 6px}.step{display:grid;grid-template-columns:26px minmax(130px,170px) 1fr 108px;gap:10px;align-items:center;border-left:3px solid var(--c);background:#fff;padding:7px 10px;margin:4px 0;border-top:1px solid var(--line2);border-bottom:1px solid var(--line2);border-right:1px solid var(--line2)}.step .no{display:grid;place-items:center;width:24px;height:24px;background:#212529;color:#fff;font-weight:700;font-size:13px}.step small{color:var(--muted);font-size:12px;text-align:right;white-space:nowrap;margin:0}.step .track{margin:0}.arr{display:none}
.ochip{display:inline-flex;align-items:center;font-weight:600;color:var(--strong);font-size:14px;line-height:1.2}
table.ord td.oc{text-align:left;padding:9px 10px;min-width:118px}table.ord td.oc.diff{box-shadow:inset 0 0 0 2px var(--accent);background:var(--insight)}table.ord td.oc small{margin-top:2px}table.ord td.st{font-size:13px;color:var(--muted);white-space:nowrap}table.ord td.st .ok{color:var(--best-fg);font-weight:600}table.ord th[scope=row]{white-space:nowrap}
.btnrow{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}#agent-prompt{width:100%;height:360px;font:12.5px/1.5 ui-monospace,Consolas,Menlo,monospace;color:var(--ink);background:var(--thbg);border:1px solid var(--line);padding:14px;resize:vertical}
.thead{display:flex;gap:12px;align-items:center;margin-bottom:12px}.thead h4{margin:0}.thead p{margin:2px 0 0}.tcol .switch{margin-top:12px}.alist{margin-top:10px}.alist .li{display:flex;gap:8px;margin:7px 0;align-items:flex-start}.alist .li .sw{margin-top:4px;flex:none}.alist .li span{display:block;color:var(--muted);font-size:13.5px}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0;font-size:13.5px;color:var(--muted)}.legend.small{font-size:13px}.legend span{display:inline-flex;align-items:center}
.chart{width:100%;height:auto;display:block;max-width:440px}.chart.wide{max-width:none}.chart .grid{stroke:var(--line);stroke-width:1}.chart text{fill:var(--ink);font-size:12px}.chart .axis{fill:var(--soft)}.chart .val{font-weight:600}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:28px}
.seq{font-size:16px;font-weight:700;color:var(--strong);margin:12px 0 2px}ul.plain{padding-left:20px;margin:10px 0}ul.plain li{margin:5px 0}
.example{background:var(--bg);padding:6px 18px 16px;margin-top:18px;max-width:600px}.exrow{display:grid;grid-template-columns:170px 1fr 48px;gap:12px;align-items:center;margin:8px 0}.exrow.total{border-top:1px solid var(--line);padding-top:10px;font-weight:700}.exrow b{text-align:right}
.links{margin:6px 0 0;color:var(--muted);font-size:14px}a.ext{color:#d9532f;text-decoration:none;white-space:nowrap;font-weight:600}a.ext:hover{text-decoration:underline}a.ext.s{font-size:13px}table.re thead a.ext{font-size:12px;text-transform:none;letter-spacing:0}
dl.ctx{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px 24px;margin:0}dl.ctx dt{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.72px;color:var(--muted)}dl.ctx dd{margin:3px 0 0}
dl.kv{display:grid;grid-template-columns:220px 1fr;gap:10px 18px;margin:0}dl.kv dt{font-weight:600;color:var(--strong)}dl.kv dd{margin:0;color:var(--muted)}
details.dash{border:1px solid var(--line);padding:14px 18px;margin:12px 0}details summary{cursor:pointer;font-weight:600;color:var(--strong)}
footer{color:var(--soft);font-size:13px;text-align:center;padding:10px 0 30px}
@media(max-width:700px){.sec{padding:20px 16px}.aoicard{grid-template-columns:1fr}.xgrid{grid-template-columns:1fr}dl.kv{grid-template-columns:1fr}.hd{flex-direction:column}.comp-chart .crow{grid-template-columns:1fr}.bar nav{display:none}}
@media print{#dpop,#gpop,.btnrow{display:none!important}#agent-prompt{height:auto}.bar{position:static}.bar nav,.btn{display:none}body{background:#fff}.sec{break-inside:avoid;border-color:#ddd}details{display:block}}
"""


def build(spec, base):
    spec["_base"] = base
    for v in spec["variants"]:
        uri, _ = load_image(base, src_of(v["stimulus"]))
        DESIGNS[v["id"]] = {"name": v["name"], "cls": reg_image(uri)}
    m, o, variants = spec["method"], spec["overall"], spec["variants"]
    tiles = "".join([
        tile("Designs compared", str(len(variants)), " · ".join("{" + v["id"] + "}: " + v["name"].split("(")[0].strip() for v in variants)),
        tile("Viewers analysed", " · ".join("{" + v["id"] + "} " + str(seg_of(v, "All")["n"]) for v in variants), "all viewers, by design"),
        tile("Time windows", "3", "first 3, 5 and 10 seconds"),
        tile("Primary metric", "VAI", "Composite of Reach, Speed, Hold")])
    kp = "".join(tile(k["label"], k["value"], k.get("note", "")) for k in o.get("kpis", []))
    finds = "".join(f'<div class="xtile"><span class="lab">{e(f.get("tag", "").replace("-", " "))}</span><p><b>{rich(f["title"])}</b></p><p class="muted">{rich(f["text"])}</p></div>' for f in o.get("findings", []))
    actions = "".join(insight(a["text"] + (f' Preserve: {a["preserve"]}' if a.get("preserve") else ""), a["title"] + ".") for a in spec.get("actions", []))
    concl = "".join(insight(x) for x in o.get("conclusions", []))
    overall = section("overall", "Overall findings and conclusions",
                      f'<div class="callout"><span class="lab">{rich(o.get("verdict_label", "Conclusion"))}</span><p>{rich(o.get("verdict_text", ""))}</p></div><p>{rich(o.get("summary", ""))}</p>'
                      f'<div class="tiles">{kp}</div><h4>Key findings</h4><div class="xgrid">{finds}</div>'
                      + (f"<h4>Conclusions</h4>{concl}" if concl else "") + f"<h4>What to do next</h4>{actions}"
                      '<p class="hint">The detailed analysis follows: what the scores mean, the viewing order, each design, gender and age. Technical details are in the appendix at the end.</p>')
    retest = section("actions", "How to test it next", '<dl class="kv">' + "".join(f"<dt>{e(k.replace('_', ' ').title())}</dt><dd>{rich(x)}</dd>" for k, x in spec.get("retest", {}).items()) + "</dl>")
    limits = "".join(f"<li>{rich(x)}</li>" for x in spec.get("limits", []))
    changes = "".join(f"<li>{rich(x)}</li>" for x in spec.get("would_change", []))
    sources = "".join(f"<li>{rich(x)}</li>" for x in spec.get("sources", []))
    defs = "".join(f"<dt>{e(k)}</dt><dd>{e(x)}</dd>" for k, x in {
        "VAI": "RealEye's Visual Attention Index (0–100): the equal-weight mean of Reach, Speed and Hold. A relative score, not a share of viewers or of attention.",
        "Reach": "Share of viewers who looked at the AOI at least once in the window.", "Speed": "How soon the AOI is noticed after it becomes visible. Used to rank the viewing order.",
        "Hold": "How long attention stays on the AOI relative to the window.", "Viewing order": "AOIs ranked by VAI Speed: a relative hierarchy across viewers, not one person's scan path.",
        "AOI": "Area of Interest: a saved region of the image (tagline, pack, face, logo, brand name).", "Windows": "First 3, 5 and 10 s are cumulative and start at 0.5 s.",
        "Webcam eye tracking": "Gaze estimated from participants' own webcams in the RealEye platform. It shows where attention concentrates, with less precision than lab trackers.",
        "Quality filter": m.get("quality_filter", "Only viewers with data quality Average or better.")}.items())
    appendix = section("technical", "Technical appendix",
                       '<p class="muted">For analysts and researchers: how the study was run, the data used, and the limits of the evidence.</p>' + method_block(spec) + vai_tech_notes()
                       + f'<h3>Evidence and limits</h3><ul class="plain">{limits}</ul>' + (f'<h4>What would change the recommendation</h4><ul class="plain">{changes}</ul>' if changes else "")
                       + f'<h3>Definitions</h3><dl class="kv">{defs}</dl><h3>Sources</h3><ul class="plain">{sources}</ul><h3>Dashboard AOI VAI report (unfiltered copy)</h3>'
                       + "".join(dashboard_vai(spec, v, i) for i, v in enumerate(variants)))
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t in (("tested", "Designs tested"), ("overall", "Findings"), ("vai", "VAI"), ("order", "Viewing order"), ("design-A", "Analysis"), ("compare", "Comparison"),
                                                          ("audience", "Gender and age"), ("actions", "Next steps"), ("technical", "Appendix"), ("agent", "Ask an AI")))
    body = "".join(('<a id="design-A"></a>' if i == 0 else "") + design_sections(spec, v, i) for i, v in enumerate(variants))
    study = spec.get("app_title") or m.get("study") or spec.get("title", "")
    printer = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="1.8"><path d="M6 9V3h12v6M6 18H4v-7h16v7h-2M7 14h10v7H7z"/></svg>'
    info = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#5c5c5c" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></svg>'
    page = (f'<div class="kicker"><span class="re-tag">Report</span><span class="t">Neuromarketing report</span></div>'
            f'<div class="hd"><div><h1>{e(spec.get("title", ""))}</h1><p>{e(spec.get("subtitle", ""))} {e(spec.get("date", ""))}{" · " + e(spec["prepared_for"]) if spec.get("prepared_for") else ""}</p></div>'
            f'<button class="btn" onclick="window.print()">{printer} Print / Save as PDF</button></div>'
            f'<div class="strip">{info}<div><b>How this was measured</b><span>{e(m.get("banner", "RealEye platform, webcam eye tracking."))}</span></div></div>'
            f'{intro_section(spec)}<div class="tiles">{tiles}</div>{overall}{vai_guide(spec)}{order_section(spec)}{body}{compare_section(spec)}{audience_section(spec)}{retest}{appendix}{agent_section(spec)}'
            '<footer>Generated with the RealEye neuromarketing-image-report skill. Eye tracking shows where people looked, not what they understood, liked or will buy.</footer>')
    tips = make_tips(spec)
    nav, page = tips(nav), tips(page)
    css_imgs = "".join(f".{c}{{background-image:url('{u}')}}" for u, c in IMAGES.items())
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{e(spec.get("title", "Neuromarketing report"))}</title>'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&display=swap" rel="stylesheet">'
            f'<style>{CSS}</style></head><body><div class="bar"><span class="logo"><b>Re</b>alEye</span><span class="sep"></span><span class="study">{e(study)}</span><nav>{nav}</nav></div>'
            f'<main class="page">{page}</main><style>{css_imgs}</style>' + POP + POP2 + '</body></html>')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_file")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()
    src = Path(a.json_file).resolve()
    spec = json.loads(src.read_text(encoding="utf-8"))
    out = Path(a.output) if a.output else src.with_suffix(".html")
    out.write_text(build(spec, src.parent), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    sys.exit(main())
