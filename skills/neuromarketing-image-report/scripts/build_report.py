#!/usr/bin/env python3
"""Render a Visual Attention Report JSON file into one self-contained HTML report.

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
import datetime
import html
import json
import math
import mimetypes
import re
import struct
import sys
from pathlib import Path

VARIANT_COLORS = ["#c2410c", "#2563c4", "#1b7d42", "#ae3ec9"]   # dark enough for white text (contrast 4.5:1 or more)
COMP_COLORS = {"vai": "#fc7753", "reach": "#3b82e0", "speed": "#e3ac1c", "hold": "#27a85a"}
AOI_COLORS = ["#d77732", "#6ec850", "#3296d7", "#d73296", "#96d732", "#7048e8", "#f08c00"]
MIN_N = 30        # under this many viewers a group is anecdotal (†)
CERTAIN_N = 100   # a group needs at least this many viewers for a result to be certain; 30 to 99 is indicative (‡)
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
GLOSSARY["RealEye"] = ("RealEye: an online research platform for webcam eye tracking. Participants take a study in their own browser, RealEye estimates where they look, and its dashboard turns that into heatmaps, "
                       "AOI statistics and the VAI. Click to open www.RealEye.io.")
for _k in list(GLOSSARY):
    if _k.startswith(("VAI", "Reach", "Speed", "Hold")):
        GLOSSARY[_k] += " A higher score means the element is better at attracting visual attention."
_SKIP_TAGS = ("svg", "script", "style", "title", "option", "textarea")


def make_tips(spec):
    """Return a function that wraps every glossary term in the text of an HTML fragment in a tooltip span."""
    terms = dict(GLOSSARY)
    terms.update(spec.get("glossary", {}))
    rx = re.compile(r"\b(" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + r")\b")

    state = {"a": 0}

    def wrap(m):
        t_ = m.group(1)
        if t_ == "RealEye" and not state["a"]:
            return f'<a class="gl" href="https://www.realeye.io" target="_blank" rel="noopener" data-tip="{e(terms[t_])}">RealEye</a>'
        return f'<span class="gl" data-tip="{e(terms[t_])}">{t_}</span>'

    def tips(fragment):
        out, depth = [], 0
        state["a"] = 0
        for tok in re.split(r"(<[^>]*>)", fragment):
            if tok.startswith("<"):
                mt = re.match(r"<(/?)([a-zA-Z0-9]+)", tok)
                if mt and mt.group(2).lower() in _SKIP_TAGS and not tok.endswith("/>"):
                    depth += -1 if mt.group(1) else 1
                if mt and mt.group(2).lower() == "a" and not tok.endswith("/>"):
                    state["a"] = max(0, state["a"] + (-1 if mt.group(1) else 1))
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


def mk(seg):
    # sample-size marker: † anecdotal (under 30), ‡ indicative (30 to 99), none when the group has at least 100 viewers
    return "†" if seg["n"] < MIN_N else ("‡" if seg["n"] < CERTAIN_N else "")


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
    return (f'<div class="crop pic {reg_image(uri)}" role="img" aria-label="{e(a["name"])} in design {e(v["id"])}" style="aspect-ratio:{target};background-size:{100 / bw2 * 100:.2f}% {100 / bh2 * 100:.2f}%;'
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


def hbars(cats, series, title, labelw=170, bh=14, gap=3):
    gg, width = 14, 760
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


# ------------------------------------------------------------------ charts for audiences and gaps
_WCOUNT = [0]


def aud_color(label, idx=0):
    if label.startswith("Men "):
        return ["#1d4ed8", "#3b82e0", "#93c5fd"][idx % 3]
    if label.startswith("Women "):
        return ["#c2410c", "#fc7753", "#fdba9c"][idx % 3]
    if label == "Men":
        return "#3b82e0"
    if label == "Women":
        return "#fc7753"
    return ["#0f766e", "#14b8a6", "#7dd3c8", "#5eead4"][idx % 4]


def window_tabs(panes, default="10"):
    """CSS-only tabs (first 3 s / 5 s / 10 s): panes = {window: html}."""
    _WCOUNT[0] += 1
    gid = f"wt{_WCOUNT[0]}"
    radios = "".join(f'<input type="radio" name="{gid}" id="{gid}-{w}" value="{w}"{" checked" if w == default else ""}>' for w in WIN)
    labels = "".join(f'<label for="{gid}-{w}" data-w="{w}">{WIN_LABEL[w]}</label>' for w in WIN)
    body = "".join(f'<div class="wpane" data-w="{w}">{panes[w]}</div>' for w in WIN)
    return f'<div class="wtabs">{radios}<div class="tabs">{labels}</div>{body}</div>'


def segment_chart(spec, v, kind, title):
    segs = [sg for sg in v["segments"] if sg["kind"] == kind]
    if not segs:
        return ""
    n = names(spec)
    panes = {}
    for w in WIN:
        series = []
        for i, sg in enumerate(segs):
            idx = i % 3 if kind == "gender_age" else i
            series.append((f'{sg["label"]} (N={sg["n"]}{(", " + mk(sg)) if mk(sg) else ""})', aud_color(sg["label"], idx), [val(sg, w, k, "vai") for k in range(len(n))]))
        leg = '<div class="legend">' + "".join(f"<span>{swatch(c)}{e(l)}</span>" for l, c, _ in series) + "</div>"
        panes[w] = leg + hbars(n, series, f"VAI by audience, {WIN_LABEL[w]}", bh=9 if len(series) > 3 else 12, gap=2)
    return f'<h5>{e(title)}: chart (VAI per element)</h5>' + window_tabs(panes)


def gap_chart(spec, v, vi, a_label, b_label, title):
    sa, sb = seg_of(v, a_label), seg_of(v, b_label)
    if not sa or not sb:
        return ""
    n = names(spec)
    data = {w: [val(sb, w, i, "vai") - val(sa, w, i, "vai") for i in range(len(n))] for w in WIN}
    mx = max(10, max(abs(x) for w in WIN for x in data[w]))
    mx = math.ceil(mx / 5) * 5
    width, labelw, bh, gap, gg = 760, 170, 11, 2, 14
    plot = width - labelw - 40
    zero = labelw + plot / 2
    h = len(n) * (3 * (bh + gap) + gg) + 26
    shades = {"3": "#fdba9c", "5": "#fc7753", "10": "#c2410c"} if vi == 0 else {"3": "#93c5fd", "5": "#3b82e0", "10": "#1d4ed8"}
    out = [f'<svg class="chart wide" viewBox="0 0 {width} {h}" role="img" aria-label="{e(title)}">']
    for t in range(-2, 3):
        x = zero + plot / 2 * t / 2
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{h - 18}" class="grid"/><text x="{x:.1f}" y="{h - 4}" text-anchor="middle" class="axis">{(f"{mx * t / 2:+g}" if t else "0")}</text>')
    out.append(f'<line x1="{zero:.1f}" x2="{zero:.1f}" y1="0" y2="{h - 18}" stroke="#8b8b8b" stroke-width="1.5"/>')
    for gi, nm in enumerate(n):
        y0 = gi * (3 * (bh + gap) + gg) + 4
        out.append(f'<text x="{labelw - 10}" y="{y0 + 20}" text-anchor="end" class="axis">{e(nm)}</text>')
        for wi, w in enumerate(WIN):
            d = data[w][gi]
            y = y0 + wi * (bh + gap)
            wd = plot / 2 * abs(d) / mx
            x = zero if d >= 0 else zero - wd
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(wd, 1):.1f}" height="{bh}" fill="{shades[w]}"/>'
                       f'<text x="{(zero + wd + 5) if d >= 0 else (zero - wd - 5):.1f}" y="{y + 9}" text-anchor="{"start" if d >= 0 else "end"}" class="val s">{d:+.1f}</text>')
    out.append("</svg>")
    leg = '<div class="legend">' + "".join(f'<span>{swatch(shades[w])}{WIN_LABEL[w]}</span>' for w in WIN) + "</div>"
    return f'<h5>{chip(v["id"], e(v["id"]), "vtag", "background:" + vcolor(vi))} {e(title)}</h5>{leg}{"".join(out)}'


# ------------------------------------------------------------------ study facts and participants
def _fmt_date(iso):
    import datetime
    try:
        return datetime.date.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")
    except Exception:
        return iso


def collection_range(spec):
    ps = spec.get("participants") or {}
    firsts = [x["collected_from"] for x in ps.values() if x.get("collected_from")]
    lasts = [x["collected_to"] for x in ps.values() if x.get("collected_to")]
    if not firsts:
        return ""
    return f"{_fmt_date(min(firsts))} – {_fmt_date(max(lasts))}"


def pbars(title, items, total, color):
    """Horizontal share bars (count and percentage) for one participant breakdown."""
    rows = "".join(
        f'<div class="prow"><span class="pl">{e(k)}</span><div class="track"><i style="width:{(c / total * 100 if total else 0):.1f}%;background:{color}"></i></div><b>{c}</b><span class="pp">{(c / total * 100 if total else 0):.0f}%</span></div>'
        for k, c in items if c is not None)
    return f'<div class="pbars"><h5>{e(title)}</h5>{rows}</div>'


def participants_section(spec):
    ps = spec.get("participants")
    if not ps:
        return ""
    cols = ""
    for vi, v in enumerate(spec["variants"]):
        x = ps.get(v["id"])
        if not x:
            continue
        tot = x["analysed"]
        age = x.get("age", {})
        bands = list(age.get("bands", {}).items())
        no_age = tot - age.get("with_age", 0)
        if no_age > 0:
            bands.append(("No age given", no_age))
        facts = [f'{tot} viewers analysed' + (f' (of {x["collected"]} collected)' if x.get("collected") else "")]
        if age.get("median") is not None:
            facts.append(f'median age {age["median"]:g} (self-reported, {age.get("with_age", 0)} viewers)')
        if x.get("collected_from"):
            facts.append(f'collected {_fmt_date(x["collected_from"])} – {_fmt_date(x["collected_to"])}')
        cols += (f'<div class="pcol"><h4>{chip(v["id"], e(v["id"]), "vtag", "background:" + vcolor(vi))} {e(v["name"])}</h4><p class="muted small">{e(" · ".join(facts))}</p>'
                 + pbars("Gender", list(x.get("gender", {}).items()), tot, vcolor(vi)) + pbars("Age", bands, tot, vcolor(vi)) + pbars("Device", list(x.get("device", {}).items()), tot, vcolor(vi)) + "</div>")
    note = spec.get("participants_note", "Gender and age are self-reported by the viewers; some viewers did not give them. Percentages are of the viewers analysed.")
    return section("who", "Who took part", f'<p class="hint">{rich(note)}</p><div class="two">{cols}</div>')


def study_tiles(spec):
    si = spec.get("study_info") or {}
    out = []
    if si.get("created"):
        out.append(tile("Study created", si["created"], si.get("status", "")))
    rng = collection_range(spec)
    if rng:
        out.append(tile("Data collected", rng, "when the viewers took part"))
    if si.get("realeye_version"):
        out.append(tile("RealEye version", si["realeye_version"], si.get("version_note", "dashboard version at analysis")))
    return out


def participants_appendix(spec):
    ps = spec.get("participants")
    if not ps and not spec.get("study_info"):
        return ""
    si = spec.get("study_info") or {}
    rows = "".join(f'<div><dt>{e(lab)}</dt><dd>{rich(si[k])}</dd></div>' for k, lab in (
        ("created", "Study created"), ("status", "Study status"), ("type", "Study type"), ("realeye_version", "RealEye version (dashboard at analysis)"), ("tracker", "Eye tracker"),
        ("analysed_on", "Data analysed on"), ("settings", "Stimulus settings"), ("panel", "Participants")) if si.get(k))
    out = f'<h3>Study and platform</h3><dl class="ctx">{rows}</dl>' if rows else ""
    for vi, v in enumerate(spec["variants"]):
        x = (ps or {}).get(v["id"])
        if not x:
            continue
        tot = x["analysed"]
        quality = list(x.get("quality", {}).items())
        qrows = "".join(f'<tr><td>{e(k)}</td><td>{c}</td><td>{(c / x["collected"] * 100 if x.get("collected") else 0):.0f}%</td><td>{"analysed" if k not in ("Very low", "Low") else "removed"}</td></tr>' for k, c in quality)
        extra = "".join(f'<tr><th scope="row">{e(k)}</th><td colspan="3">{rich(str(val_))}</td></tr>' for k, val_ in (
            ("Eye tracker", x.get("tracker_text")), ("Participant type", x.get("participant_type_text")), ("Browser window (median)", x.get("screen_text")),
            ("Age (self-reported)", x.get("age_text")), ("Collected from / to", f'{_fmt_date(x["collected_from"])} – {_fmt_date(x["collected_to"])}' if x.get("collected_from") else None)) if val_)
        out += (f'<h4>{chip(v["id"], e(v["id"]), "vtag", "background:" + vcolor(vi))} {e(v["name"])}: data quality and set-up</h4>'
                + pbars("Data quality of the collected viewers (Average or better are analysed)", quality, x.get("collected", tot), vcolor(vi))
                + f'<div class="tablewrap"><table class="re"><thead><tr><th>Data quality</th><th>Viewers</th><th>Share</th><th>Used</th></tr></thead><tbody>{qrows}</tbody></table></div>'
                + (f'<div class="tablewrap"><table class="re"><tbody>{extra}</tbody></table></div>' if extra else ""))
    return out



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
    head = "".join(f'<th>{alink(dash_url(spec, v, "aoi", s["label"]), s["label"])}<small>N = {s["n"]}{(" " + mk(s)) if mk(s) else ""}</small></th>' for s in segs)
    rows = ""
    for ai, nm in enumerate(names(spec)):
        for wi, w in enumerate(WIN):
            first = f'<th scope="row" rowspan="3">{swatch(acolor(v, nm, ai))}{e(nm)}</th>' if wi == 0 else ""
            rows += f'<tr class="{"grp" if wi == 0 else ""}">{first}<th class="w">{WIN_LABEL[w]}</th>' + "".join(cell(s, w, ai) for s in segs) + "</tr>"
    return f'<h5>{e(title)}: table (VAI, with Reach · Speed · Hold)</h5><div class="tablewrap"><table class="re seg"><thead><tr><th>Element</th><th>Window</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


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
                   "Higher is better at attracting visual attention: a higher VAI, Reach, Speed or Hold means the element does that job better. Judge each element against its role, because a logo can do its job at a moderate score. "
                   "VAI shows attention, not outcome: it does not say whether viewers understood, liked or will buy, so confirm with a recall or choice test. "
                   "Heatmaps are only a picture of the same data: analyse the VAI numbers, not how a heatmap looks.")
            + '<h4>Component patterns and what to do</h4><div class="tablewrap"><table class="re"><thead><tr><th>Reach</th><th>Speed</th><th>Hold</th><th>Reading</th><th>Typical action</th></tr></thead>'
            f'<tbody>{prow}</tbody></table></div>{example}')
    return section("vai", "What the scores mean (VAI)", body)


def vai_tech_notes():
    return f"""<h3>Technical notes on VAI</h3><ul class="plain">
<li><b>Compare like with like:</b> the same element, the same time window and a similar number of viewers (N). Large elements, and elements that overlap others, naturally score higher.</li>
<li><b>Windows are cumulative.</b> "First 3 s" is 0.5–3 s, "first 5 s" is 0.5–5 s and "first 10 s" is 0.5–10 s. The first 0.5 s is skipped to reduce the effect of where viewers happened to be looking when the image appeared. Reach and Speed can only rise as the window grows; Hold is relative to the window, so it can fall even when viewers keep looking.</li>
<li><b>Group size decides how certain a result is.</b> To be certain, every group you want to analyse needs at least {CERTAIN_N} viewers. Groups of {MIN_N} to {CERTAIN_N - 1} viewers are marked ‡ (indicative, not certain) and groups under {MIN_N} are marked † (anecdotal).</li>
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
                differ.append(sg["label"] + (" " + mk(sg) if mk(sg) else ""))
            cells = "".join(
                f'<td class="oc{"" if order[i] == base_order[i] else " diff"}{" low" if small(sg) else ""}">{ochip(v, order[i], n.index(order[i]))}'
                f'<small>Speed {val(sg, w, n.index(order[i]), "speed"):.0f}</small></td>' for i in range(len(n)))
            status = '<span class="ok">same as overall</span>' if same else "differs"
            rows += (f'<tr><th scope="row">{e(sg["label"])}<small>N = {sg["n"]}{(" " + mk(sg)) if mk(sg) else ""}</small></th>{cells}<td class="st">{status if sg["label"] != "All" else "overall"}</td></tr>')
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
            + '<h3 id="order-audience">Viewing order by audience</h3><p class="hint">For every audience (all viewers, gender, age, gender × age) and time window: the elements in the order they are noticed (1st to 5th), ranked by VAI Speed. An outlined cell is an element in a different place than for all viewers. † marks a small audience (fewer than %d viewers).</p>' % MIN_N
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
    image_card = section(f'd{v["id"]}-aois', "Image with AOIs", toggle)
    heat_card = section(f'd{v["id"]}-heat', "Measured heatmap", note("How to read it:", "warm colours (yellow, orange, red) mark where viewers looked most; cool colours (blue) mark where they looked least. "
                        "The heatmap is built from the webcam eye-tracking fixations of this study's viewers (first 10 seconds, all viewers).") + note("Illustration only:", HEATMAP_NOTE)
                        + f'<div class="heat">{figure(base, v.get("heatmap"), "Measured heatmap", "All viewers, first 10 seconds.")}</div>')
    best = lambda k: max(range(len(n)), key=lambda i: val(seg, "10", i, k))
    worst = lambda k: min(range(len(n)), key=lambda i: val(seg, "10", i, k))
    b = lambda i: f'<b>"{e(n[i])}"</b>'
    glance = "".join(f'<div class="xtile"><span class="lab">{lab}</span><p>{txt}</p></div>' for lab, txt in (
        ("Top element by VAI", f'{b(best("vai"))} has the highest VAI ({val(seg, "10", best("vai"), "vai"):.1f}/100).'),
        ("Highest VAI Speed", f'{b(best("speed"))} is noticed soonest ({val(seg, "10", best("speed"), "speed"):.1f}/100).'),
        ("Highest VAI Hold", f'{b(best("hold"))} holds attention longest ({val(seg, "10", best("hold"), "hold"):.1f}/100).'),
        ("Lowest VAI Reach", f'{b(worst("reach"))} is reached by the smallest share of viewers ({val(seg, "10", worst("reach"), "reach"):.1f}/100).')))
    glance_card = section(f'd{v["id"]}-glance', "At a glance", f'<div class="xgrid">{glance}</div><p class="hint">All viewers, first 10 seconds.</p>')
    insights = section(f'd{v["id"]}-findings', "What the data says", "".join(insight_card(spec, t, f'd{v["id"]}-finding-{k + 1}', [f'd{v["id"]}-summary', f'd{v["id"]}-build']) for k, t in enumerate(v.get("findings", []))))
    cards = "".join(
        f'<div class="aoicard2">{aoi_crop(base, v, a)}<div class="meta"><b>{e(a["name"])}</b><p><span class="kv">VAI <b>{val(seg, "10", i, "vai"):.1f}</b></span><span>·</span><span class="kv">Reach <b>{val(seg, "10", i, "reach"):.1f}</b></span>'
        f'<span>·</span><span class="kv">Speed <b>{val(seg, "10", i, "speed"):.1f}</b></span><span>·</span><span class="kv">Hold <b>{val(seg, "10", i, "hold"):.1f}</b></span></p></div><i class="cbar" style="background:{a.get("color", "#999")}"></i></div>'
        for i, a in enumerate(v["aois"]))
    overview = section(f'd{v["id"]}-overview', "AOIs overview", f'<div class="cards3">{cards}</div><p class="hint">All viewers, first 10 seconds. VAI and its components, 0–100.</p>')
    summary = section(f'd{v["id"]}-summary', "VAI summary", '<p class="hint">Measured VAI and its Reach / Speed / Hold per element, all viewers, first 10 seconds. Higher is better at attracting visual attention. Values are indices (0–100), not shares; elements overlap and do not need to total 100%.</p>'
                      + vai_summary(spec, v) + '<h4>VAI component averages per element</h4>' + comp_bars(spec, v, seg, "10") + '<h4>VAI by time window</h4>' + window_table(spec, v))
    series = lambda k: {nm: ([val(seg, w, i, k) for w in WIN], acolor(v, nm, i)) for i, nm in enumerate(n)}
    xl = ["first 3 s", "first 5 s", "first 10 s"]
    mini = "".join(f'<div><h5>{lab} by window</h5>{lines(series(k), xl, lab)}</div>' for k, lab in COMP)
    build_up = section(f'd{v["id"]}-build', "How attention builds up over time", legend([(nm, acolor(v, nm, i)) for i, nm in enumerate(n)]) + f'<div class="grid2">{mini}</div>')
    aud = section(f'd{v["id"]}-audience', "By gender, age and gender × age",
                  '<p class="hint">Each cell is the VAI for that audience, element and window, with Reach · Speed · Hold underneath. ‡ marks a group of %d to %d viewers (indicative, not certain: a result needs at least %d viewers in the group to be certain); † marks a group under %d viewers (anecdotal).</p>' % (MIN_N, CERTAIN_N - 1, CERTAIN_N, MIN_N)
                  + f'<span id="d{v["id"]}-gender"></span>' + segment_chart(spec, v, "gender", "By gender") + segment_table(spec, v, "gender", "By gender")
                  + f'<span id="d{v["id"]}-age"></span>' + segment_chart(spec, v, "age", "By age") + segment_table(spec, v, "age", "By age")
                  + f'<span id="d{v["id"]}-gender_age"></span>' + segment_chart(spec, v, "gender_age", "By gender × age") + segment_table(spec, v, "gender_age", "By gender × age"))

    def sheet(w):
        ls = " · ".join(alink(dash_url(spec, v, "heatmap", sg["label"], int(w)), sg["label"], "ext s") for sg in v["segments"] if dash_url(spec, v, "heatmap", sg["label"], int(w)))
        return (f'<h5>Heatmaps, {WIN_LABEL[w]}</h5><div class="sheet">{figure(base, v["heatmap_sheets"][w], f"Heatmaps by audience, {WIN_LABEL[w]}")}</div>'
                + (f'<p class="links small">Open in the RealEye heatmap: {ls}</p>' if ls else ""))
    sheets = section(f'd{v["id"]}-sheets', "Heatmaps by audience and time window", note("Illustration only:", HEATMAP_NOTE) + f'<p class="hint">{rich(v.get("heatmap_note", ""))}</p>' + "".join(sheet(w) for w in WIN if w in v.get("heatmap_sheets", {})))
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
    cnote = certainty_note(spec, True)
    text = cnote + "".join(insight_card(spec, x, f"seg-finding-{k + 1}", ["audience"] + [f'd{v["id"]}-audience' for v in variants]) for k, x in enumerate(spec.get("segment_findings", [])))
    ages = [s["label"] for s in variants[0]["segments"] if s["kind"] == "age"]
    ga = gap_table(spec, variants, "18–24", "25–34", "Viewers 25–34 minus viewers 18–24 (the 25–34 group is small: anecdotal)") if "18–24" in ages and "25–34" in ages else ""
    lk = ' · '.join('Design ' + e(x["id"]) + ': ' + open_links(spec, x, "Women", None, ("aoi", "heatmap")) + ' (women)' for x in variants) if open_links(spec, variants[0]) else ""
    gc = "".join(gap_chart(spec, v, vi, "Men", "Women", "Women minus men (VAI points)") for vi, v in enumerate(variants))
    gc2 = "".join(gap_chart(spec, v, vi, "Men 18–24", "Women 18–24", "Women 18–24 minus men 18–24 (VAI points)") for vi, v in enumerate(variants))
    body = (text + gc + gap_table(spec, variants, "Men", "Women", "Women minus men (VAI points)") + gc2 + gap_table(spec, variants, "Men 18–24", "Women 18–24", "Women 18–24 minus men 18–24 (the largest groups)") + ga
            + f'<p class="hint">‡ under {CERTAIN_N} viewers: indicative, not certain. † under {MIN_N} viewers: anecdotal. Full tables and heatmaps are in each design\'s section.</p>' + (f'<p class="links small">Open in RealEye: {lk}</p>' if lk else ""))
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
        items = "".join(f'<div class="li">{swatch(a.get("color", "#999"))}<div><b>{e(a["name"])}</b><span>{e(a.get("role", ""))}</span>' + (f'<span>Why: {e(a["why"])}</span>' if a.get("why") else "") + '</div></div>' for a in v["aois"])
        cols += (f'<div class="aoitog tcol"><div class="thead">{chip(v["id"], e(v["id"]), "badge", "background:" + vcolor(vi))}'
                 f'<div><h4>Design {e(v["id"])}: {e(v["name"])}</h4><p class="muted">{e(v.get("description", ""))}</p></div></div>'
                 f'<div class="stagebox">{stage(base, v)}</div>'
                 '<label class="switch"><input type="checkbox" class="sw-in" checked><span class="trk"></span><span>Show AOIs</span></label>'
                 f'<div class="alist">{items}</div>'
                 f'<p class="links small">{seg["n"]} viewers' + (f" · Open in RealEye: {links}" if links else "") + "</p></div>")
    prop = [v["id"] for v in spec["variants"] if v.get("aoi_source") == "proposed"]
    pnote = (f'<p class="box"><b>These AOIs were defined for this report.</b> The study had no AOIs saved for {"design " + prop[0] if len(prop) == 1 else "designs " + " and ".join(prop)}, '
             'so the elements were chosen from the image and the purpose of the design (why each one matters is listed under it). Their scores are measured from the same viewers and the same eye-tracking data, '
             'but the AOIs are not saved in RealEye: the study blueprint at the end gives their exact coordinates.</p>') if prop else ""
    body = (pnote + '<p class="hint">The images tested in this study and the elements analysed. Each outlined element is an Area of Interest (AOI) that is measured separately; '
            'the same elements are used throughout the report. Switch the outlines off to see the clean image.</p>' + f'<div class="two">{cols}</div>')
    return section("tested", "Tested designs and the elements analysed", body)


def _csv(rows):
    def q(x):
        t = f"{x:g}" if isinstance(x, float) else str(x)
        return '"' + t.replace('"', '""') + '"' if any(ch in t for ch in ',"\n') else t
    return "\n".join(",".join(q(x) for x in r) for r in rows)


def _audience_parts(label):
    lab = label.strip()
    gender = "all"
    if lab.startswith("Men"):
        gender, lab = "men", lab[3:].strip()
    elif lab.startswith("Women"):
        gender, lab = "women", lab[5:].strip()
    return gender, (lab if lab and lab != "All" else "all")


def data_tables(spec):
    """All the data the report is built from, as tidy tables (name -> list of rows, first row = header)."""
    n, variants = names(spec), spec["variants"]
    t = {}
    t["study"] = [["key", "value"]] + [[k, re.sub(r"\{([A-Z])\}", r"\1", str(v))] for k, v in (
        ("title", spec.get("title", "")), ("date", spec.get("date", "")), ("platform", spec["method"].get("platform", "")), ("eye_tracking", spec["method"].get("tracking", "")),
        ("study", spec["method"].get("study", "")), ("participants_analysed", spec["method"].get("participants", "")), ("quality_filter", spec["method"].get("quality_filter", "")),
        ("windows", spec["method"].get("windows", "")), ("audiences", spec["method"].get("segments", "")), ("task", spec["method"].get("task", "")),
        ("sample_size_rule", f"a group needs at least {CERTAIN_N} viewers for a result to be certain; {MIN_N} to {CERTAIN_N - 1} is indicative (marked with a double dagger); under {MIN_N} is anecdotal (marked with a dagger)"), ("report_generated_by", f"{SKILL_NAME} v{SKILL_VERSION} (report format {SCHEMA_VERSION})"), ("report_generated_on", spec.get("_generated", ""))) if v]
    si = spec.get("study_info") or {}
    for k, vv in si.items():
        t["study"].append(["study_" + k, re.sub(r"\{([A-Z])\}", r"\1", str(vv))])
    rng = collection_range(spec)
    if rng:
        t["study"].append(["data_collected", rng])
    ps = spec.get("participants") or {}
    if ps:
        pr = [["design", "group", "category", "viewers", "share_of_analysed_pct"]]
        for did, x in ps.items():
            tot = x["analysed"] or 1
            pr.append([did, "overall", "collected", x.get("collected", ""), ""])
            pr.append([did, "overall", "analysed", x["analysed"], 100])
            for grp, d in (("gender", x.get("gender", {})), ("age_band", x.get("age", {}).get("bands", {})), ("device", x.get("device", {}))):
                for k, c in d.items():
                    pr.append([did, grp, k, c, round(c / tot * 100, 1)])
            if x.get("age", {}).get("with_age") is not None:
                pr.append([did, "age_band", "No age given", tot - x["age"]["with_age"], round((tot - x["age"]["with_age"]) / tot * 100, 1)])
            for k, c in x.get("quality", {}).items():
                pr.append([did, "data_quality_of_collected", k, c, ""])
        t["participants"] = pr
    t["designs"] = [["design", "name", "description", "viewers_all", "item_id"]] + [[v["id"], v["name"], v.get("description", ""), seg_of(v, "All")["n"], v.get("item_id", "")] for v in variants]
    el = [["design", "element", "covers", "color", "bbox_x0_pct", "bbox_y0_pct", "bbox_x1_pct", "bbox_y1_pct"]]
    for v in variants:
        for a in v["aois"]:
            b = bbox(a["shape"]) if a.get("shape") else ("", "", "", "")
            el.append([v["id"], a["name"], a.get("role", ""), a.get("color", ""), *[round(x, 1) if x != "" else "" for x in b]])
    t["elements"] = el
    ac = [["design", "element", "shape", "colour", "image_width_px", "image_height_px", "x1_px", "y1_px", "x2_px", "y2_px", "vertices_px", "time_range_s"]]
    for v in variants:
        for a in aoi_records(spec, v):
            ac.append([v["id"], a["name"], a["type"], a["color"] or "", a["image_px"][0], a["image_px"][1], *a["bbox_px"], " ".join(f"({x},{y})" for x, y in a["points_px"]), "-".join(str(x) for x in a["time_range_s"])])
    t["aoi_coordinates"] = ac
    au = [["design", "audience", "kind", "gender", "age_band", "viewers", "small_audience"]]
    vai = [["design", "audience", "window_s", "element", "vai", "reach", "speed", "hold", "speed_rank", "vai_rank"]]
    for v in variants:
        for sg in v["segments"]:
            g, ab = _audience_parts(sg["label"])
            au.append([v["id"], sg["label"], sg["kind"], g, ab, sg["n"], "yes" if small(sg) else "no"])
            for w in WIN:
                sp = rank_names(spec, sg, w)
                vr = sorted(n, key=lambda nm: -val(sg, w, n.index(nm), "vai"))
                for i, nm in enumerate(n):
                    vai.append([v["id"], sg["label"], int(w), nm, val(sg, w, i, "vai"), val(sg, w, i, "reach"), val(sg, w, i, "speed"), val(sg, w, i, "hold"), sp.index(nm) + 1, vr.index(nm) + 1])
    t["audiences"], t["vai_by_audience"] = au, vai
    dd = [["design", "window", "element", "vai", "reach", "speed", "hold", "participants"]]
    for v in variants:
        d = v.get("dashboard_vai")
        if d:
            for nm, sm in d["summary"].items():
                dd.append([v["id"], "average of windows", nm, sm["vai"], sm["reach"], sm["speed"], sm["hold"], d["participants"]])
                for wi, wl in enumerate(d["windows"]):
                    dd.append([v["id"], wl, nm, *[d["by_window"][k][nm][wi] for k in ("vai", "reach", "speed", "hold")], d["participants"]])
    if len(dd) > 1:
        t["dashboard_vai_report_unfiltered"] = dd
    lk = [["design", "view", "url"]]
    for v in variants:
        for kind, lab in (("heatmap", "heatmap"), ("aoi", "aoi_report"), ("vai", "aoi_vai_report")):
            u = dash_url(spec, v, kind)
            if u:
                lk.append([v["id"], lab, u])
    if len(lk) > 1:
        t["dashboard_links"] = lk
    return t


def data_pack(spec):
    """Markdown 'data pack': a short guide plus every table as CSV, so an AI assistant can use the data without parsing the report."""
    t = data_tables(spec)
    guide = {
        "study": "Study context, including when the study was created, when the data was collected and the RealEye version.", "participants": "Viewer profile per design: gender, age bands (self-reported), device, and data quality of all collected viewers. share_of_analysed_pct is of the analysed viewers.", "designs": "The tested designs.", "aoi_coordinates": "Exact AOI geometry in image pixels (origin top-left), enough to redraw every AOI in RealEye and rerun the study.", "elements": "AOIs (elements) per design: what each covers and its bounding box in % of the image (0,0 = top-left).",
        "audiences": "Audiences and their sizes. kind: overall | gender | age | gender_age. small_audience = fewer than 30 viewers (anecdotal).",
        "vai_by_audience": ("MAIN TABLE, one row per design x audience x window x element. vai, reach, speed, hold are 0-100 (vai = mean of reach, speed, hold). "
                            "window_s = 3, 5 or 10: cumulative windows 0.5-3, 0.5-5, 0.5-10 s. speed_rank = viewing order position (1 = noticed first). vai_rank = rank by VAI."),
        "dashboard_vai_report_unfiltered": "The dashboard AOI VAI report: all participants with data, NOT quality-filtered (the dashboard cannot filter it).",
        "dashboard_links": "RealEye dashboard views (need a signed-in account).",
    }
    L = [f"# Data pack: {re.sub(r'[{}]', '', spec.get('title', 'report'))}", "",
         "Every number behind the report, as tidy CSV tables. Only VAI and its components (reach, speed, hold) exist; there are no other metrics. "
         "Use these tables directly instead of parsing the report. Only viewers with data quality Average or better are included, except where noted.", ""]
    for name, rows in t.items():
        L += [f"## {name}", guide.get(name, ""), "", "```csv", _csv(rows), "```", ""]
    return "\n".join(L).rstrip() + "\n"


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
    for k, lab in (("created", "Study created"), ("status", "Study status"), ("type", "Study type"), ("realeye_version", "RealEye version (dashboard at analysis)"), ("tracker", "Eye tracker"), ("settings", "Stimulus settings"), ("panel", "Participants")):
        if (spec.get("study_info") or {}).get(k):
            add(f"{lab}: {c(spec['study_info'][k])}")
    if collection_range(spec):
        add(f"Data collected: {collection_range(spec)}")
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
    add("- Heatmaps are illustrations only. Base every statement on the VAI numbers (VAI, Reach, Speed, Hold) in the data pack, never on how a heatmap looks.")
    add(f"- A result is certain only when every group it compares has at least {CERTAIN_N} viewers. Groups of {MIN_N} to {CERTAIN_N - 1} viewers are indicative (marked with a double dagger) and groups under {MIN_N} are anecdotal (marked with a dagger): say so whenever you use them and never call such a result certain. Viewers with other or unspecified gender, or no recorded age, are in 'All' but not in the gender or age cuts.")
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
    add("=== DATA PACK (markdown with CSV tables: every number behind the report; use it directly) ===")
    add(data_pack(spec))
    add("")
    add("=== THE REPORT'S FINDINGS AND CONCLUSIONS ===")
    add(f"Conclusion: {c(o.get('verdict_label', ''))}. {c(o.get('verdict_text', ''))}")
    add(c(o.get("summary", "")))
    for i, f in enumerate(o.get("findings", []), 1):
        ev = "; ".join(c(x if isinstance(x, str) else x.get("text", "")) for x in f.get("evidence", []))
        add(f"- Finding {i} [{f.get('tag', '')}] {c(f['title'])}: {c(f.get('conclusion') or f.get('text', ''))}" + (f" Why: {c(f['why'])}" if f.get("why") else "") + (f" Evidence: {ev}" if ev else ""))
    for x in o.get("conclusions", []):
        add(f"- Conclusion: {c(x if isinstance(x, str) else x.get('title', '') + ': ' + x.get('text', ''))}" + ("" if isinstance(x, str) else f" (follows from findings {', '.join(str(b) for b in x.get('based_on', []))})"))
    _t = lambda x: x if isinstance(x, str) else x.get("title", "") + ": " + x.get("text", "")
    for v in variants:
        for x in v.get("findings", []):
            add(f"- Design {v['id']}: {c(_t(x))}")
    for x in spec.get("segment_findings", []):
        add(f"- Gender/age: {c(_t(x))}")
    for v in variants:
        add(f"- Design {v['id']} presents: {c(v.get('presents', ''))} Assumed purpose: {c(v.get('purpose', ''))}")
    for i, h in enumerate(spec.get("hypotheses", []), 1):
        add(f"- Hypothesis {i} [{h.get('verdict', '')}] {c(h.get('hypothesis', ''))}: {c(h.get('conclusion', ''))} Why: {c(h.get('why', ''))}")
    for x in spec.get("study_improvements", []):
        add(f"- Study improvement [{x.get('category', '')}] {c(x.get('title', ''))}: {c(x.get('text', ''))}" + ("".join(f" Q: {c(q.get('question', ''))}" for q in x.get("questions", []))))
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
    add("2. Use the CSV tables in the data pack (load them into code or a spreadsheet if you can). Compute what I ask for: differences between designs, audiences and windows; rankings; viewing order per audience; gaps; build-up over time; which audiences behave differently. Show the arithmetic briefly.")
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
    body = ('<p class="lead">Want to go further? Copy the prompt below into your AI assistant (Claude, ChatGPT or similar). It carries the whole report: the study, how to read VAI, a data pack with every number as CSV tables, '
            'the designs and elements, every VAI, Reach, Speed and Hold number for every audience and time window, the findings, actions and limits. The assistant can then answer follow-up questions, '
            'run extra comparisons and suggest insights you did not think to ask for.</p>'
            '<div class="btnrow"><button class="btn" type="button" data-act="copy">Copy prompt</button><button class="btn" type="button" data-act="download">Download as .txt</button></div>'
            f'<textarea id="agent-prompt" aria-label="Prompt for an AI assistant, with the whole report" readonly rows="18" spellcheck="false">{e(prompt)}</textarea>'
            f'<p class="hint">{len(prompt):,} characters. It contains your results, so share it only with tools you trust. The dashboard links in it work only for people signed in to RealEye.</p>'
            '<details class="datapack"><summary>Underlying data: markdown with CSV tables (the prompt above already includes it)</summary>'
            '<p class="hint">Every number the report was built from, as tidy CSV tables: study, designs, elements (AOIs) with their position, audiences and sizes, the main VAI / Reach / Speed / Hold table '
            '(design × audience × window × element, with the viewing-order rank), the unfiltered dashboard AOI VAI report and the dashboard links. Give this to an AI assistant, or load the CSV into a spreadsheet or code, instead of parsing the report.</p>'
            '<div class="btnrow"><button class="btn" type="button" data-act="copy" data-target="data-pack">Copy data pack</button>'
            '<button class="btn" type="button" data-act="download" data-target="data-pack" data-file="visual-attention-report-data-pack.md">Download data pack (.md)</button>'
            '<button class="btn" type="button" data-act="download" data-target="data-csv" data-file="vai_by_audience.csv">Download main table (.csv)</button></div>'
            f'<textarea id="data-pack" class="dp" aria-label="Data pack: every number behind the report as markdown with CSV tables" readonly rows="14" spellcheck="false">{e(data_pack(spec))}</textarea>'
            f'<textarea id="data-csv" hidden>{e(_csv(data_tables(spec)["vai_by_audience"]))}</textarea></details>')
    return section("agent", "Continue the analysis with an AI agent", body)


POP2 = ('<script>(function(){document.addEventListener("click",function(ev){var b=ev.target.closest&&ev.target.closest("[data-act]");if(!b)return;var t=document.getElementById(b.dataset.target||"agent-prompt");if(!t)return;'
        'if(b.dataset.act==="copy"){var done=function(){var o=b.textContent;b.textContent="Copied to clipboard";setTimeout(function(){b.textContent=o},1800)};'
        'if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t.value).then(done,function(){t.select();document.execCommand("copy");done()})}else{t.select();document.execCommand("copy");done()}}'
        'else if(b.dataset.act==="download"){var f=b.dataset.file||"visual-attention-report-ai-prompt.txt";var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([t.value],{type:f.slice(-4)===".csv"?"text/csv":"text/plain"}));a.download=f;document.body.appendChild(a);a.click();a.remove()}})})();</script>')


def method_block(spec):
    m = spec["method"]
    rows = "".join(f'<div><dt>{e(k)}</dt><dd>{rich(x)}</dd></div>' for k, x in (
        ("Platform", m.get("platform")), ("Eye tracking", m.get("tracking")), ("Study", m.get("study")), ("Participants analysed", m.get("participants")),
        ("Participant quality filter", m.get("quality_filter")), ("Time windows", m.get("windows")), ("Audiences", m.get("segments")),
        ("Areas of interest", m.get("aois")), ("Task and exposure", m.get("task")), ("Source", m.get("source")), ("Tracker precision", m.get("precision"))) if x)
    return f'<h3>About this study</h3><dl class="ctx">{rows}</dl><p class="hint">{e(m.get("note", ""))}</p>'


# ------------------------------------------------------------------ versioning
SKILL_NAME = "neuromarketing-image-report"
SCHEMA_VERSION = 2   # report JSON format: 2 = findings with why + evidence, study blueprint


class ReportError(Exception):
    pass


def _skill_version():
    # the single source of truth is the version in SKILL.md (metadata.version)
    try:
        txt = (Path(__file__).resolve().parent.parent / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r'^\s*version:\s*"?([0-9][0-9A-Za-z.\-+]*)"?\s*$', txt, re.M)
        return m.group(1) if m else "unknown"
    except OSError:
        return "unknown"


SKILL_VERSION = _skill_version()
ERRORS, REFS = [], []


# ------------------------------------------------------------------ findings with evidence
TAG_COLORS = {"strength": "#17652f", "risk": "#a12a1b", "weak-evidence": "#8a6500", "opportunity": "#1d5fb4"}
_DLAB = {"aois": "image with AOIs", "heat": "measured heatmap", "glance": "at a glance", "findings": "what the data says", "overview": "AOIs overview",
         "summary": "VAI summary tables", "build": "how attention builds up over time", "audience": "by gender, age and gender × age", "gender": "VAI by gender",
         "age": "VAI by age", "gender_age": "VAI by gender × age", "sheets": "heatmaps by audience and time window"}
_FIXED = {"who": "Who took part", "tested": "Tested designs and AOIs", "vai": "What the scores mean (VAI)", "order": "Viewing order", "order-audience": "Viewing order by audience",
          "compare": "Head-to-head comparison", "audience": "Gender and age insights", "actions": "How to test it next", "technical": "Technical appendix",
          "blueprint": "Study blueprint", "agent": "Ask an AI agent", "overall": "Overall findings", "designs-top": "The designs", "hypotheses": "Hypotheses tested", "improve": "How to improve the study"}


def anchor_label(ref):
    if ref in _FIXED:
        return _FIXED[ref]
    m = re.match(r"^design-([A-Z])$", ref)
    if m:
        return f"Design {m.group(1)}: full analysis"
    m = re.match(r"^d([A-Z])-(\w+)$", ref)
    if m and m.group(2) in _DLAB:
        return f"Design {m.group(1)}: {_DLAB[m.group(2)]}"
    m = re.match(r"^f(\d+)$", ref)
    if m:
        return f"Finding {m.group(1)}"
    return ref


def point(spec, p):
    # Look up one number in the report data (design, aoi, window, metric, optional audience and minus), check any stated value, and return (chip html, refs, dashboard links).
    try:
        v = next(x for x in spec["variants"] if x["id"] == p["design"])
        ai, k, w = names(spec).index(p["aoi"]), p.get("metric", "vai"), str(p.get("window", "10"))
        if k not in dict(COMP) or w not in WIN:
            raise ValueError("metric or window")
        aud = p.get("audience", "All")
        sa = seg_of(v, aud)
        if sa is None:
            raise ValueError("no audience " + aud)
        got, v2, aud2, mi = val(sa, w, ai, k), v, aud, p.get("minus")
        if mi:
            v2 = next(x for x in spec["variants"] if x["id"] == mi.get("design", p["design"]))
            aud2 = mi.get("audience", aud)
            sb = seg_of(v2, aud2)
            if sb is None:
                raise ValueError("no audience " + aud2)
            got -= val(sb, w, ai, k)
    except Exception as ex:
        ERRORS.append(f"evidence data point {json.dumps(p, ensure_ascii=False)} is not in the report data ({type(ex).__name__}: {ex})")
        return "", [], []
    if "value" in p and abs(round(got, 1) - float(p["value"])) > 0.15:
        ERRORS.append(f"evidence data point {json.dumps(p, ensure_ascii=False)} says {p['value']} but the report data gives {got:.1f}")
    mname = dict(COMP)[k]
    if mi:
        lab = f"{{{v['id']}}} {aud} (N={sa['n']}{' ' + mk(sa) if mk(sa) else ''}) − {{{v2['id']}}} {aud2} (N={sb['n']}{' ' + mk(sb) if mk(sb) else ''})"
        shown = f"{got:+.1f}"
        refs = ["compare"] if v2["id"] != v["id"] else [f"d{v['id']}-{sa.get('kind', 'audience')}" if sa.get("kind") in ("gender", "age", "gender_age") else f"d{v['id']}-audience", "audience"]
    else:
        lab = f"{{{v['id']}}} · {aud} (N={sa['n']}{' ' + mk(sa) if mk(sa) else ''})"
        shown = f"{got:.1f}"
        refs = [f"d{v['id']}-summary" if aud == "All" else (f"d{v['id']}-{sa['kind']}" if sa.get("kind") in ("gender", "age", "gender_age") else f"d{v['id']}-audience")]
    dashes = [{"design": v["id"], "kind": "aoi", "audience": aud}]
    if mi and v2["id"] == v["id"] and aud2 != aud:
        dashes.append({"design": v["id"], "kind": "aoi", "audience": aud2})
    chip_ = f'<span class="dchip">{rich(lab + " · " + p["aoi"] + " · " + WIN_LABEL[w] + " · " + mname)} <b>{shown}</b></span>'
    return chip_, refs, dashes


def ref_link(spec, r):
    REFS.append(r)
    return f'<a class="ref" href="#{e(r)}">{e(anchor_label(r))} ↓</a>'


def dash_link(spec, d):
    v = next((x for x in spec["variants"] if x["id"] == d.get("design")), None)
    if v is None:
        ERRORS.append(f"dash link {json.dumps(d)} names an unknown design")
        return ""
    kind, aud, w = d.get("kind", "heatmap"), d.get("audience", "All"), d.get("window")
    u = dash_url(spec, v, kind, aud, int(w) if w else None)
    if not u:
        return ""
    nm = {"heatmap": "heatmap", "aoi": "AOI report", "vai": "AOI VAI report"}[kind]
    return alink(u, f"Design {v['id']} {nm}" + ("" if aud == "All" else f", {aud}") + (f", {WIN_LABEL[str(w)]}" if w and kind == "heatmap" else ""), "ext s")


def evidence_html(spec, evs, where):
    out = ""
    for i, x in enumerate(evs):
        x = {"text": x} if isinstance(x, str) else x
        chips, refs, dashes = "", [], []
        for p in x.get("data", []):
            c_, r_, d_ = point(spec, p)
            chips, refs, dashes = chips + c_, refs + r_, dashes + d_
        r0 = x.get("ref", [])
        refs += [r0] if isinstance(r0, str) else list(r0)
        dashes += x.get("dash", [])
        if not x.get("text"):
            ERRORS.append(f"{where}: evidence item {i + 1} has no text")
        if not refs:
            ERRORS.append(f"{where}: evidence item {i + 1} links to no data in the report (add ref and/or data)")
        illus = bool(refs) and not x.get("data") and all(re.match(r"^d[A-Z]-(heat|sheets)$", r_) for r_ in refs)
        rl = " · ".join(ref_link(spec, r) for r in dict.fromkeys(refs))
        seen, dl = set(), []
        for d in dashes:
            key = json.dumps(d, sort_keys=True)
            if key not in seen:
                seen.add(key)
                dl.append(dash_link(spec, d))
        dl = " · ".join(x_ for x_ in dl if x_)
        out += (f'<li class="ev"><div class="evt">' + ('<span class="illus">Illustration only</span> ' if illus else "") + f'{rich(x.get("text", ""))}</div>' + (f'<div class="evd">{chips}</div>' if chips else "")
                + f'<div class="evl"><span>In this report:</span> {rl}' + (f' <span class="sepdot">|</span> <span>In RealEye:</span> {dl}' if dl else "") + '</div></li>')
    return out


def split_title(s):
    s = str(s)
    m = re.match(r"^([^:]{3,70}):\s+(.*)$", s, re.S)
    if m:
        return m.group(1), m.group(2)
    words = s.split()
    return " ".join(words[:7]) + ("…" if len(words) > 7 else ""), s


def insight_card(spec, item, pid, default_refs=()):
    # One insight as its own sub-section. item: a string ("Title: text") or {title, text, evidence | ref | data}.
    if isinstance(item, str):
        title, text = split_title(item)
        evs = [{"text": "The numbers behind this are in", "ref": list(default_refs)}] if default_refs else []
    else:
        title, text, evs = item["title"], item.get("text", ""), item.get("evidence", [])
        if not evs and (item.get("ref") or item.get("data")):
            evs = [{"text": "The numbers behind this", "ref": item.get("ref", []), "data": item.get("data", [])}]
        if not evs and default_refs:
            evs = [{"text": "The numbers behind this are in", "ref": list(default_refs)}]
    ev = f'<ul class="evs">{evidence_html(spec, evs, pid)}</ul>' if evs else ""
    return f'<article class="finding mini" id="{e(pid)}"><h4>{rich(title)}</h4><p>{rich(text)}</p>{ev}</article>'


def finding_card(spec, f, n):
    where = f"finding {n}"
    for key in ("title", "why", "evidence"):
        if not f.get(key):
            ERRORS.append(f"{where} ({f.get('title', '?')}): missing '{key}'. Every finding needs a title, a conclusion, a why (how the conclusion follows from the data) and evidence with links.")
    concl = f.get("conclusion") or f.get("text") or ""
    if not concl:
        ERRORS.append(f"{where}: missing 'conclusion'")
    confidence_vs_sample(spec, f, where)
    needs_numbers(f, where)
    tag = f.get("tag", "")
    col = TAG_COLORS.get(tag, "#b53d1b")
    conf = f.get("confidence", "")
    cchip = f'<span class="fconf">{e(conf)} confidence</span>' if conf else ""
    ev = evidence_html(spec, f.get("evidence", []), where)
    return (f'<article class="finding" id="f{n}" style="--c:{col}"><div class="fhead"><span class="fnum">{n}</span><div><span class="ftag" style="background:{col}">{e(tag.replace("-", " ") or "finding")}</span>{cchip}'
            f'<h3>{rich(f.get("title", ""))}</h3></div></div><p class="concl">{rich(concl)}</p>'
            f'<h5>Why we conclude this</h5><p>{rich(f.get("why", ""))}</p>'
            f'<h5>Evidence, with links to the data</h5><ul class="evs">{ev}</ul>'
            + (f'<h5>What it means for the decision</h5><p>{rich(f["so_what"])}</p>' if f.get("so_what") else "")
            + (f'<p class="hint"><b>Confidence: {e(conf)}.</b> {rich(f["confidence_note"])}</p>' if f.get("confidence_note") else "") + '</article>')


def based_on(spec, item, where, nf):
    bo = item.get("based_on")
    if not bo:
        ERRORS.append(f"{where}: needs 'based_on' (the finding numbers it follows from, for example [1, 3])")
        return ""
    links = []
    for b in bo:
        n = int(str(b).lstrip("f"))
        if not 1 <= n <= nf:
            ERRORS.append(f"{where}: based_on {b} is not a finding number (1 to {nf})")
            continue
        REFS.append(f"f{n}")
        links.append(f'<a class="ref" href="#f{n}">Finding {n}: {e(spec["overall"]["findings"][n - 1].get("title", ""))} ↓</a>')
    return f'<p class="evl"><span>Follows from:</span> {" · ".join(links)}</p>'


def findings_section(spec):
    o = spec["overall"]
    fs = o.get("findings", [])
    cards = "".join(finding_card(spec, f, i + 1) for i, f in enumerate(fs))
    glance = "".join(
        f'<li><a href="#f{i + 1}"><span class="ftag" style="background:{TAG_COLORS.get(f.get("tag", ""), "#b53d1b")}">{e(f.get("tag", "").replace("-", " ") or "finding")}</span> '
        f'<b>{rich(f.get("title", ""))}</b></a><span class="muted"> {rich(f.get("conclusion") or f.get("text") or "")}</span></li>' for i, f in enumerate(fs))
    kp = "".join(tile(k["label"], k["value"], k.get("note", "")) for k in o.get("kpis", []))
    concl = ""
    for i, x in enumerate(o.get("conclusions", [])):
        if isinstance(x, str):
            ERRORS.append(f"conclusion {i + 1}: write it as an object {{title, text, based_on}} so it links to the findings it follows from")
            continue
        concl += (f'<article class="finding mini" id="c{i + 1}"><h4>{rich(x.get("title", ""))}</h4><p>{rich(x.get("text", ""))}</p>' + based_on(spec, x, f"conclusion {i + 1}", len(fs)) + '</article>')
    acts = ""
    for i, a in enumerate(spec.get("actions", [])):
        acts += (f'<article class="finding mini" id="a{i + 1}"><h4>{rich(a.get("title", ""))}</h4><p>{rich(a.get("text", ""))}'
                 + (f' <b>Preserve:</b> {rich(a["preserve"])}' if a.get("preserve") else "") + '</p>' + based_on(spec, a, f"action {i + 1}", len(fs)) + '</article>')
    return section("overall", "Overall findings and conclusions",
                   f'<div class="callout big"><span class="lab">{rich(o.get("verdict_label", "Conclusion"))}</span><p>{rich(o.get("verdict_text", ""))}</p></div><p class="lead">{rich(o.get("summary", ""))}</p>{certainty_note(spec)}<div class="readnote"><b>How to read the scores.</b> The higher the VAI score (and its Reach, Speed and Hold), the better that element is at attracting visual attention. Compare like with like, and judge each element against its role. <b>Heatmaps</b> are illustrations only: the findings rest on these numbers, not on how a heatmap looks.</div>'
                   f'<div class="tiles">{kp}</div><h3>The findings at a glance</h3><ol class="glance">{glance}</ol>'
                   f'<h3>The findings, and the evidence behind each</h3><p class="hint">Every finding states what we conclude, why, and the numbers that prove it, each linked to its table, chart or heatmap in this report and in the RealEye dashboard.</p>{cards}'
                   + (f"<h3>Conclusions</h3>{concl}" if concl else "") + f"<h3>What to do next</h3>{acts}"
                   '<p class="hint">The detailed analysis follows: what the scores mean, the viewing order, each design, gender and age. Technical details and the study blueprint are at the end.</p>', "hero")


# ------------------------------------------------------------------ study blueprint (backup of what was analysed)
def _img_px(spec, v):
    if v.get("image_px"):
        return list(v["image_px"])
    _, size = load_image(spec["_base"], src_of(v["stimulus"]))
    return list(size) if size else [1024, 1536]


def aoi_records(spec, v):
    W, H = _img_px(spec, v)
    out = []
    for a in v["aois"]:
        sh = a.get("shape") or []
        if not sh:
            continue
        x0, y0, x1, y1 = bbox(sh)
        rect = len(sh) == 4 and len({round(p[0], 1) for p in sh}) == 2 and len({round(p[1], 1) for p in sh}) == 2
        out.append({"name": a["name"], "color": a.get("color"), "type": a.get("type") or ("rectangle" if rect else "polygon"), "image_px": [W, H],
                    "bbox_px": [round(x0 / 100 * W), round(y0 / 100 * H), round(x1 / 100 * W), round(y1 / 100 * H)], "bbox_pct": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                    "points_px": [[round(p[0] / 100 * W), round(p[1] / 100 * H)] for p in sh], "points_pct": [[round(p[0], 2), round(p[1], 2)] for p in sh],
                    "time_range_s": a.get("time_range_s", [0.5, 10]), "role": a.get("role", ""), "why": a.get("why", "")})
    return out


def blueprint_data(spec):
    bp, d = spec.get("blueprint") or {}, spec.get("dashboard") or {}
    return {"format": "realeye-neuromarketing-study-blueprint",
            "generated_by": {"skill": SKILL_NAME, "skill_version": SKILL_VERSION, "report_format": SCHEMA_VERSION, "generated": spec["_generated"]},
            "study": {"title": spec.get("title", ""), "study_id": d.get("study_id"), "dashboard": d.get("base"), "info": spec.get("study_info", {}), "setup": {k: x for k, x in bp.items() if k != "recreate_steps"}},
            "stimuli": [{"design": v["id"], "name": v["name"], "item_id": v.get("item_id"), "image_px": _img_px(spec, v), "aois": aoi_records(spec, v)} for v in spec["variants"]],
            "analysis": {"metric": "VAI = mean of Reach, Speed and Hold", "windows_s": [[0.5, 3], [0.5, 5], [0.5, 10]], "min_data_quality": f"Average or better (grade {d.get('min_quality', 3)} or higher)",
                         "small_audience_below_viewers": MIN_N, "certain_at_viewers": CERTAIN_N, "audiences": [s["label"] for s in spec["variants"][0]["segments"]], "aoi_order": names(spec)},
            "participants": spec.get("participants", {})}


def _json_tag(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1).replace("</", "<\\/")


def blueprint_section(spec):
    bp, si = spec.get("blueprint") or {}, spec.get("study_info") or {}
    d = spec.get("dashboard") or {}
    variants = spec["variants"]
    rows = []
    surl = dash_url(spec, {}, "study")
    rows.append(("Study", (alink(surl, bp.get("study_name") or spec.get("title", "")) if surl else e(bp.get("study_name") or spec.get("title", "")))))
    if any(v.get("aoi_source") == "proposed" for v in variants):
        rows.append(("Areas of interest", "Defined for this report from the image (none were saved in the study); not saved in RealEye"))
    for k, lab in (("created", "Created"), ("type", "Study type"), ("status", "Status when analysed"), ("tracker", "Eye tracker"), ("panel", "Participants")):
        if si.get(k):
            rows.append((lab, rich(si[k])))
    for k, lab in (("target_participants", "Target number of participants"), ("participant_source", "Participant source"), ("demographics_asked", "Questions asked to participants"),
                   ("devices", "Devices accepted"), ("random_order", "Random stimulus order"), ("notes", "Notes")):
        if bp.get(k):
            rows.append((lab, rich(bp[k])))
    if si.get("settings") and not bp.get("stimuli"):
        rows.append(("Stimulus settings", rich(si["settings"])))
    for did, s in (bp.get("stimuli") or {}).items():
        rows.append((f"Design {did} settings", rich(", ".join(f"{k.replace('_', ' ')}: {x}" for k, x in s.items()))))
    setup = '<dl class="kv">' + "".join(f"<dt>{e(k)}</dt><dd>{x}</dd>" for k, x in rows) + "</dl>"
    dl_img = ""
    designs = ""
    for vi, v in enumerate(variants):
        uri, _ = load_image(spec["_base"], src_of(v["stimulus"]))
        ext = "png" if uri.startswith("data:image/png") else "jpg"
        W, H = _img_px(spec, v)
        dl_img += f'<a class="btn" download="stimulus-{e(v["id"])}.{ext}" href="{e(uri)}">Download design {e(v["id"])} image (.{ext})</a>'
        tr = ""
        for a in aoi_records(spec, v):
            x0, y0, x1, y1 = a["bbox_px"]
            pts = "" if a["type"] == "rectangle" else "<small>Vertices (px): " + " ".join(f"({x},{y})" for x, y in a["points_px"]) + "</small>"
            tr += (f'<tr><td>{swatch(a["color"] or "#999")}<b>{e(a["name"])}</b>{("<small>" + e(a["role"]) + "</small>") if a["role"] else ""}{("<small>Why: " + e(a["why"]) + "</small>") if a.get("why") else ""}</td><td>{e(a["type"])}</td><td>{e(a["color"] or "")}</td>'
                   f'<td>{x0}, {y0} → {x1}, {y1}{pts}</td><td>{a["bbox_pct"][0]}, {a["bbox_pct"][1]} → {a["bbox_pct"][2]}, {a["bbox_pct"][3]}</td><td>{a["time_range_s"][0]}–{a["time_range_s"][1]} s</td></tr>')
        designs += (f'<h4>{chip(v["id"], e(v["id"]), "vtag", "background:" + vcolor(vi))} {e(v["name"])}</h4>'
                    f'<div class="two"><div class="stagebox">{stage(spec["_base"], v)}</div><div><p class="hint">Image size {W} × {H} px. Coordinates are in image pixels, origin (0, 0) at the top-left, x to the right and y down. '
                    f'Percent coordinates are the same box as a share of the image width and height.</p></div></div>'
                    f'<div class="tablewrap"><table class="re"><thead><tr><th>Element (AOI)</th><th>Shape</th><th>Colour</th><th>Box in pixels (x1, y1 → x2, y2)</th><th>Box in %</th><th>Time range</th></tr></thead><tbody>{tr}</tbody></table></div>')
    wins = "first 3 s (0.5–3 s), first 5 s (0.5–5 s) and first 10 s (0.5–10 s), cumulative"
    analysis = ('<dl class="kv">'
                f'<dt>Metric</dt><dd>VAI = equal-weight mean of Reach, Speed and Hold (0–100)</dd><dt>Time windows</dt><dd>{wins}</dd>'
                f'<dt>Viewer filter</dt><dd>Data quality Average or better (grade {d.get("min_quality", 3)} or higher; grades: 1 Very low, 2 Low, 3 Average, 4 Good, 5 Very good, 6 Perfect)</dd>'
                f'<dt>Audiences</dt><dd>{e(", ".join(s["label"] for s in variants[0]["segments"]))}</dd><dt>Group size</dt><dd>at least {CERTAIN_N} viewers per group for a certain result; {MIN_N} to {CERTAIN_N - 1} indicative (‡); under {MIN_N} anecdotal (†)</dd>'
                f'<dt>Element order</dt><dd>{e(", ".join(names(spec)))}</dd></dl>')
    wh = d.get("base", "https://app.realeye.io")
    steps = [
        f"Create a new study in RealEye ({e(si.get('type') or 'Images and Videos')}) at {e(wh)}.",
        "Upload the stimulus images (download them above), in this order: " + "; ".join(f"design {e(v['id'])}" + (f" ({e(bp['stimuli'][v['id']]['file_name'])})" if (bp.get('stimuli') or {}).get(v['id'], {}).get('file_name') else "") for v in variants) + ".",
        "Set each stimulus' options as listed under Study set-up (display time, how it finishes, instructions, order).",
        ("These AOIs were proposed for this report and are not yet saved in the study. " if any(v.get("aoi_source") == "proposed" for v in variants) else "")
        + "Open each stimulus' AOI editor and draw the elements from the tables above, using the pixel coordinates (image size as shown). Keep the same names and, if you want the new report to look the same, the same colours.",
        "Add the participant questions (at least gender and age) so audience cuts work: " + e(bp.get("demographics_asked") or "gender and age") + ".",
        "Invite participants: share the study link with your own participants or order RealEye panel participants. Plan for at least 100 viewers with Average or better data quality in every group you want to analyse (each design, each gender, each age band, each gender × age cell): below 100 a result is only indicative.",
        "When data has come in, give an AI agent that has the neuromarketing-image-report skill the new study and item ids together with this report's data (download below). It collects the numbers, rebuilds the report and can compare it with this one.",
    ] + [rich(x) for x in bp.get("recreate_steps", [])]
    note = ('<p class="hint">The same study can also simply keep running: collect more participants, then rebuild the report. The report always states the collection dates and the number of viewers analysed, so two versions can be compared fairly.</p>')
    body = (f'<p class="lead">This report is also a backup of what was analysed. It holds the study set-up, the images, the exact position of every element (AOI) and the analysis settings, so the study can be recreated in RealEye '
            f'and run again with new participants.</p><div class="btnrow">{dl_img}<button class="btn" type="button" data-act="download" data-target="blueprint-json" data-file="study-blueprint.json">Download study blueprint (.json)</button>'
            '<button class="btn" type="button" data-act="download" data-target="report-json" data-file="report.json">Download report data (report.json)</button></div>'
            f'<h3>Study set-up</h3>{setup}<h3>Stimuli and AOI coordinates</h3>{designs}<h3>How the data was analysed</h3>{analysis}'
            f'<h3>How to run this study again</h3><ol class="plain">{"".join(f"<li>{x}</li>" for x in steps)}</ol>{note}'
            f'<textarea id="blueprint-json" hidden>{e(json.dumps(blueprint_data(spec), ensure_ascii=False, indent=1))}</textarea>'
            f'<textarea id="report-json" hidden>{e(spec["_raw_json"])}</textarea>'
            f'<script type="application/json" id="study-blueprint-data">{_json_tag(blueprint_data(spec))}</script>')
    return section("blueprint", "Study blueprint: recreate and rerun this study", body)


def version_block(spec):
    authored = spec.get("skill_version")
    rows = [("Skill", SKILL_NAME), ("Skill version used to build this report", f"v{SKILL_VERSION}"), ("Report format", f"version {SCHEMA_VERSION}"), ("Report generated on", spec["_generated"])]
    if authored:
        rows.append(("Report data written for skill version", f"v{authored}"))
    note = ""
    if authored and authored != SKILL_VERSION:
        note = f'<p class="box">The report data was written for skill v{e(authored)} and rendered with v{e(SKILL_VERSION)}. Regenerate the data with the current skill if sections look incomplete.</p>'
    return ('<h3>Report and skill version</h3><dl class="kv">' + "".join(f"<dt>{e(k)}</dt><dd>{e(x)}</dd>" for k, x in rows) + "</dl>" + note
            + '<p class="hint">The skill version is in the skill\'s SKILL.md and its CHANGELOG.md lists what changed in each version. The same version is embedded in the data pack and the study blueprint.</p>')


# ------------------------------------------------------------------ difference tokens: numbers that always show their difference
_TOK = re.compile(r"\{\{(cmp|diff|gap):([^}]*)\}\}")
CUR = {"spec": None}


def _expand_tokens(text):
    # {{diff:metric:AOI:window:A,B}} -> "B is 0.6 points higher"
    # {{cmp:metric:AOI:window:A,B[:audience]}}  -> "VAI 61.2 in {A} and 61.8 in {B} – B is 0.6 points higher"
    # {{gap:metric:AOI:window:design:Women,Men}} -> "VAI 70.1 for Women and 54.5 for Men in {A} – Women 15.6 points higher"
    spec = CUR["spec"]

    def one(m):
        try:
            kind, args = m.group(1), [a.strip() for a in m.group(2).split(":")]
            metric, aoi, w = args[0], args[1], args[2]
            if metric not in dict(COMP) or w not in WIN:
                raise ValueError("metric or window")
            ai = names(spec).index(aoi)
            mn = "VAI" if metric == "vai" else "VAI " + dict(COMP)[metric]
            V = lambda i: next(v for v in spec["variants"] if v["id"] == i)
            if kind in ("cmp", "diff"):
                a_id, b_id = [x.strip() for x in args[3].split(",")]
                aud = args[4] if len(args) > 4 else "All"
                xa, xb = val(seg_of(V(a_id), aud), w, ai, metric), val(seg_of(V(b_id), aud), w, ai, metric)
                d = xb - xa
                tail = "no difference" if abs(d) < 0.05 else f"{b_id} is {abs(d):.1f} points {'higher' if d > 0 else 'lower'}"
                if kind == "diff":
                    return tail[0].upper() + tail[1:]
                return f"{mn} {xa:.1f} in {{{a_id}}} and {xb:.1f} in {{{b_id}}} – {tail}"
            d_id, pair = args[3], [x.strip() for x in args[4].split(",")]
            x1, x2 = val(seg_of(V(d_id), pair[0]), w, ai, metric), val(seg_of(V(d_id), pair[1]), w, ai, metric)
            d = x1 - x2
            tail = "no difference" if abs(d) < 0.05 else f"{pair[0]} {abs(d):.1f} points {'higher' if d > 0 else 'lower'}"
            return f"{mn} {x1:.1f} for {pair[0]} and {x2:.1f} for {pair[1]} in {{{d_id}}} – {tail}"
        except Exception as ex:
            ERRORS.append(f"cannot expand {m.group(0)} ({type(ex).__name__}: {ex})")
            return "?"
    return _TOK.sub(one, text)


def expand_all(o):
    if isinstance(o, dict):
        return {k: expand_all(v) for k, v in o.items()}
    if isinstance(o, list):
        return [expand_all(x) for x in o]
    if isinstance(o, str) and "{{" in o:
        return _expand_tokens(o)
    return o


_PAIR1 = re.compile(r"\d+(?:\.\d+)?\s+(?:in|for)\s+\{?[A-Z]\}?\b[^.;]{0,60}?\d+(?:\.\d+)?\s+(?:in|for)\s+\{?[A-Z]\}?\b")
_PAIR2 = re.compile(r"\b\{?[A-Z]\}?\s+[+−-]?\d+(?:\.\d+)?\s*(?:·|,|and|vs\.?|versus)\s*\{?[A-Z]\}?\s+[+−-]?\d+(?:\.\d+)?")
_DIFFWORD = re.compile(r"higher|lower|difference|points|more than|less than|gap|apart|ahead|behind|same|viewers")


def lint_differences(spec):
    # Warn about text that gives the same number for two designs without their difference; the fix is a {{cmp:...}} token.
    seen = []

    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("segments", "dashboard_vai", "participants", "_raw_json", "value"):
                    continue
                walk(v, path + "/" + k)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
        elif isinstance(o, str) and (_PAIR1.search(o) or _PAIR2.search(o)) and not _DIFFWORD.search(o):
            seen.append(f"{path}: {o[:90]}")
    walk(spec, "")
    for s_ in seen:
        print("WARNING: numbers for two designs without their difference (use {{cmp:metric:AOI:window:A,B}}): " + s_, file=sys.stderr)


# ------------------------------------------------------------------ heatmaps are illustrations, the analysis is the data
HEATMAP_NOTE = ("Heatmaps are for illustration only. They draw where the viewers' gaze data landed, each scaled on its own, so how a heatmap looks depends on its colour scale and smoothing, "
                "and the strength of two maps cannot be compared. The analysis and every conclusion rest on the numbers (VAI and its Reach, Speed and Hold), not on how a heatmap looks.")


def needs_numbers(item, where):
    # a conclusion must rest on VAI numbers: at least one evidence item has data points
    if not any(isinstance(x, dict) and x.get("data") for x in item.get("evidence", [])):
        ERRORS.append(f"{where}: no evidence item with data points. Conclusions must rest on the VAI numbers (and Reach, Speed, Hold), not on how a heatmap looks: add `data`")


# ------------------------------------------------------------------ how certain: group sizes
def certainty_note(spec, compact=False):
    variants = spec["variants"]
    ok, weak = [], []
    for sg in variants[0]["segments"]:
        ns = [(seg_of(v, sg["label"]) or {"n": 0})["n"] for v in variants]
        txt = f'{sg["label"]} ({", ".join("{" + v["id"] + "} " + str(n) for v, n in zip(variants, ns))})'
        (ok if min(ns) >= CERTAIN_N else weak).append(txt)
    head = ('<b>How certain are these results?</b> ' + rich("To be certain, every group you want to analyse needs at least ") + f"<b>{CERTAIN_N} viewers</b>. "
            + rich(("Groups of that size here: " + "; ".join(ok) + ". ") if ok else "No group here reaches that size. "))
    if compact:
        return f'<div class="readnote">{head}' + (rich(str(len(weak)) + " groups are smaller (marked ‡ or †): read their results as indicative, not certain.") if weak else "") + "</div>"
    return (f'<div class="readnote">{head}'
            + (rich("Smaller groups, whose results are indicative and not certain (‡ 30 to " + str(CERTAIN_N - 1) + " viewers, † under " + str(MIN_N) + "): " + "; ".join(weak) + ". ") if weak else "")
            + rich("Collect more viewers in the groups that matter to you before acting on their differences.") + "</div>")


def min_group_n(spec, evs):
    ns = []
    for x in evs:
        if isinstance(x, str):
            continue
        for p_ in x.get("data", []):
            try:
                v = next(v_ for v_ in spec["variants"] if v_["id"] == p_["design"])
                ns.append(seg_of(v, p_.get("audience", "All"))["n"])
                if p_.get("minus"):
                    v2 = next(v_ for v_ in spec["variants"] if v_["id"] == p_["minus"].get("design", p_["design"]))
                    ns.append(seg_of(v2, p_["minus"].get("audience", p_.get("audience", "All")))["n"])
            except Exception:
                pass
    return min(ns) if ns else None


def confidence_vs_sample(spec, item, where):
    n = min_group_n(spec, item.get("evidence", []))
    if item.get("confidence") == "high" and item.get("tag") != "weak-evidence" and n is not None and n < CERTAIN_N:  # a weak-evidence finding is about small groups: high confidence in the limit is fine
        ERRORS.append(f"{where}: confidence 'high' but its evidence uses a group of {n} viewers (under {CERTAIN_N}). Lower the confidence to medium or low, or base the finding on larger groups")


# ------------------------------------------------------------------ the designs at the very top
def designs_band(spec):
    cards = ""
    for vi, v in enumerate(spec["variants"]):
        src = v.get("aoi_source", "saved")
        if src not in ("saved", "proposed"):
            ERRORS.append(f"design {v['id']}: aoi_source must be 'saved' or 'proposed'")
        if src == "proposed":
            for a_ in v["aois"]:
                for key in ("role", "why"):
                    if not a_.get(key):
                        ERRORS.append(f"design {v['id']}: proposed AOI '{a_.get('name', '?')}' needs '{key}' (what it is, and why it matters for this design)")
        for key in ("presents", "purpose"):
            if not v.get(key):
                ERRORS.append(f"design {v['id']}: missing '{key}' (what the design presents, and the assumed purpose of showing it to people)")
        links = open_links(spec, v)
        cards += (f'<div class="dcard"><div class="stagebox">{stage(spec["_base"], v, outlines=False)}</div><div class="dtext">'
                  f'<h3>{chip(v["id"], e(v["id"]), "badge sm", "background:" + vcolor(vi))}Design {e(v["id"])}: {e(v["name"])}</h3>'
                  f'<p><b>What it presents.</b> {rich(v.get("presents", ""))}</p><p><b>Assumed purpose.</b> {rich(v.get("purpose", ""))}</p>'
                  + (f'<p class="links small">Open in RealEye: {links}</p>' if links else "") + '</div></div>')
    return section("designs-top", "The designs in this report", f'<div class="dband">{cards}</div>', "bandsec")


# ------------------------------------------------------------------ hypotheses
VERDICTS = {"supported": "#17652f", "partly supported": "#8a6500", "not supported": "#a12a1b", "cannot tell": "#5c5c5c"}


def hypotheses_section(spec):
    hs = spec.get("hypotheses", [])
    if len(hs) < 3:
        ERRORS.append("hypotheses: give at least 3 hypotheses the designer or brand owner probably had when making the image(s), each answered with evidence")
    cards, rows = "", ""
    for i, h in enumerate(hs, 1):
        where = f"hypothesis {i}"
        for key in ("hypothesis", "verdict", "conclusion", "why", "evidence"):
            if not h.get(key):
                ERRORS.append(f"{where}: missing '{key}'")
        vd = h.get("verdict", "")
        if vd and vd not in VERDICTS:
            ERRORS.append(f"{where}: verdict must be one of {', '.join(VERDICTS)}")
        col = VERDICTS.get(vd, "#5c5c5c")
        confidence_vs_sample(spec, h, where)
        needs_numbers(h, where)
        ev = evidence_html(spec, h.get("evidence", []), where)
        rows += f'<li><a href="#h{i}"><span class="ftag" style="background:{col}">{e(vd)}</span> <b>{rich(h.get("hypothesis", ""))}</b></a></li>'
        cards += (f'<article class="finding" id="h{i}" style="--c:{col}"><div class="fhead"><span class="fnum">H{i}</span><div><span class="ftag" style="background:{col}">{e(vd)}</span>'
                  + (f'<span class="fconf">{e(h["confidence"])} confidence</span>' if h.get("confidence") else "")
                  + f'<h3>{rich(h.get("hypothesis", ""))}</h3></div></div><p class="concl">{rich(h.get("conclusion", ""))}</p>'
                  f'<h5>Why we conclude this</h5><p>{rich(h.get("why", ""))}</p><h5>Evidence, with links to the data</h5><ul class="evs">{ev}</ul>'
                  + (f'<h5>What it means for the decision</h5><p>{rich(h["so_what"])}</p>' if h.get("so_what") else "") + '</article>')
    return section("hypotheses", "Did the design do what it was meant to? Hypotheses tested",
                   '<p class="lead">People who design an image usually build in a few assumptions about how viewers will look at it. These are the main ones, and what the measured attention says about each.</p>'
                   f'<ol class="glance hyp">{rows}</ol>{cards}'
                   '<p class="hint">Attention data can support or reject assumptions about where people look. It cannot show whether they understood, liked or remembered what they saw: where a hypothesis is about that, the verdict is "cannot tell".</p>')


# ------------------------------------------------------------------ ideas to improve the study
IMPROVE_CATS = [("aois", "Different or more AOIs"), ("respondents", "More or different respondents"), ("survey", "Add a survey: questions worth asking"),
                ("benchmark", "Benchmark against the best performers"), ("other", "Other ideas")]


def improve_section(spec):
    items = spec.get("study_improvements", [])
    have = {x.get("category") for x in items}
    for c_, _ in IMPROVE_CATS[:4]:
        if c_ not in have:
            ERRORS.append(f"study_improvements: add at least one item with category '{c_}'")
    out = ""
    for cat, label in IMPROVE_CATS:
        group = [x for x in items if x.get("category") == cat]
        if not group:
            continue
        out += f"<h3>{label}</h3>"
        for i, x in enumerate(group, 1):
            qs = ""
            if x.get("questions"):
                qs = ('<div class="tablewrap"><table class="re"><thead><tr><th>Question</th><th>Why it helps</th><th>Answer type</th></tr></thead><tbody>'
                      + "".join(f'<tr><td><b>{rich(q.get("question", ""))}</b></td><td>{rich(q.get("why", ""))}</td><td>{e(q.get("answer_type", ""))}</td></tr>' for q in x["questions"]) + "</tbody></table></div>")
            steps = ("<ol class=\"plain\">" + "".join(f"<li>{rich(s_)}</li>" for s_ in x["steps"]) + "</ol>") if x.get("steps") else ""
            out += (f'<article class="finding mini" id="imp-{cat}-{i}"><h4>{rich(x.get("title", ""))}</h4><p>{rich(x.get("text", ""))}</p>'
                    + (f'<p class="hint"><b>Why:</b> {rich(x["why"])}</p>' if x.get("why") else "") + steps + qs + "</article>")
    return section("improve", "How to improve the study", '<p class="lead">Ideas to get more, and more useful, insight from the next round of this study.</p>' + out)


# ------------------------------------------------------------------ support links for the definitions
SUPPORT_BASE = "https://www.realeye.io"
SUPPORT = {"VAI": "/support/areas-of-interest-aois", "Reach": "/support/areas-of-interest-aois", "Speed": "/support/areas-of-interest-aois", "Hold": "/support/areas-of-interest-aois",
           "Viewing order": "/support/areas-of-interest-aois", "Windows": "/support/areas-of-interest-aois", "AOI": "/support/what-is-aoi",
           "Webcam eye tracking": "/support/how-to-get-accurate-results", "Quality filter": "/support/participant-quality-stats-explained",
           "Gender and age": "/support/external-variables-age-and-gender", "Heatmap": "/features/online-analysis-dashboard", "RealEye": "/"}


def support_link(term):
    p = SUPPORT.get(term)
    if not p:
        return ""
    return f' <a class="ext s" href="{SUPPORT_BASE}{p}" target="_blank" rel="noopener">Read more on RealEye ↗</a>'


# ------------------------------------------------------------------ floating menu
def toc_html(spec, ids):
    o = spec.get("overall", {})
    clean = lambda t: re.sub(r"\{([A-Z])\}", r"\1", str(t))[:64]
    items = [("designs-top", "The designs", []), ("overall", "Overall findings", [(f"f{i + 1}", f.get("title", "")) for i, f in enumerate(o.get("findings", []))]),
             ("audience", "Gender and age", []), ("hypotheses", "Hypotheses tested", [(f"h{i + 1}", h.get("hypothesis", "")) for i, h in enumerate(spec.get("hypotheses", []))]),
             ("tested", "Designs and AOIs", []), ("who", "Who took part", []), ("vai", "What VAI means", []), ("order", "Viewing order", [])]
    items += [(f"design-{v['id']}", f"Design {v['id']}: analysis", []) for v in spec["variants"]]
    items += [("compare", "Head-to-head", []), ("actions", "How to test it next", []), ("improve", "Improve the study", []), ("technical", "Technical appendix", []),
              ("blueprint", "Study blueprint", []), ("agent", "Ask an AI agent", [])]
    cp = lambda i: f'<button class="cp" type="button" data-copy="{e(i)}" title="Copy link to this part" aria-label="Copy link to this part">⧉</button>'
    li = ""
    for id_, label, kids in items:
        if id_ not in ids:
            continue
        sub = "".join(f'<li><a href="#{e(k)}" data-id="{e(k)}">{e(clean(t))}</a>{cp(k)}</li>' for k, t in kids if k in ids)
        li += f'<li><a href="#{e(id_)}" data-id="{e(id_)}">{e(label)}</a>{cp(id_)}' + (f"<ul>{sub}</ul>" if sub else "") + "</li>"
    return ('<aside id="toc" aria-label="Report navigation"><div class="tochead"><b>Contents</b><button type="button" id="tocx" aria-label="Close menu">×</button></div>'
            f'<ul>{li}</ul><p class="tochint">⧉ copies a link to that part of the report.</p></aside><button type="button" id="tocbtn">☰ Menu</button>')


POP3 = r"""<script>(function(){
var toc=document.getElementById("toc"),btn=document.getElementById("tocbtn");if(!toc)return;
var links=[].slice.call(toc.querySelectorAll("a[data-id]")),items=[];
links.forEach(function(a){var el=document.getElementById(a.dataset.id);if(el)items.push({a:a,el:el})});
function spy(){var y=window.scrollY+120,cur=null;items.forEach(function(x){if(x.el.getBoundingClientRect().top+window.scrollY<=y)cur=x});
 links.forEach(function(a){a.classList.remove("on");a.parentNode.classList.remove("open")});
 if(cur){cur.a.classList.add("on");var li=cur.a.parentNode;li.classList.add("open");var p=li.parentNode&&li.parentNode.closest?li.parentNode.closest("li"):null;if(p)p.classList.add("open");
  var r=cur.a.getBoundingClientRect(),t=toc.getBoundingClientRect();if(r.top<t.top+40||r.bottom>t.bottom-30)toc.scrollTop+=r.top-t.top-80}}
var tk=0;window.addEventListener("scroll",function(){if(tk)return;tk=1;requestAnimationFrame(function(){tk=0;spy()})},{passive:true});window.addEventListener("load",spy);spy();
btn.addEventListener("click",function(){document.body.classList.toggle("tocopen")});document.getElementById("tocx").addEventListener("click",function(){document.body.classList.remove("tocopen")});
toc.addEventListener("click",function(ev){if(ev.target.closest("a")&&window.innerWidth<1500)document.body.classList.remove("tocopen")});
function copyText(t,done){function ok(){done&&done()}if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(ok,function(){fb()})}else fb();
 function fb(){var a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();try{document.execCommand("copy")}catch(e){}a.remove();ok()}}
document.addEventListener("click",function(ev){var b=ev.target.closest&&ev.target.closest("[data-copy]");if(!b)return;ev.preventDefault();var id=b.dataset.copy,u=location.href.split("#")[0]+"#"+id,o=b.textContent;
 copyText(u,function(){b.textContent="✓";b.classList.add("done");setTimeout(function(){b.textContent=o;b.classList.remove("done")},1500)});try{history.replaceState(null,"","#"+id)}catch(e){}});
[].slice.call(document.querySelectorAll("main [id]")).forEach(function(el){if(!/^(SECTION|ARTICLE)$/.test(el.tagName))return;var h=el.querySelector("h2,h3,h4");if(!h)return;
 var b=document.createElement("button");b.type="button";b.className="lnk";b.dataset.copy=el.id;b.title="Copy link to this part";b.setAttribute("aria-label","Copy link to this part");b.textContent="#";h.appendChild(b)});
})();</script>"""

POP5 = r"""<script>window.addEventListener("beforeprint",function(){[].forEach.call(document.querySelectorAll("details.dash"),function(d){if(!d.open){d.setAttribute("data-po","1");d.open=true}})});window.addEventListener("afterprint",function(){[].forEach.call(document.querySelectorAll("details[data-po]"),function(d){d.open=false;d.removeAttribute("data-po")})});</script>"""

POP4 = r"""<script>(function(){
var root=document.querySelector("main.page");if(!root)return;
var KEY="re-marks:"+document.title+":"+((document.querySelector("meta[name=generator]")||{}).content||""),store={t:[],a:[]},mode="",color="y";
function save(){try{localStorage.setItem(KEY,JSON.stringify(store))}catch(e){}}
try{var s0=localStorage.getItem(KEY);if(s0)store=JSON.parse(s0)}catch(e){}
function nodes(){var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:function(n){var p=n.parentNode;return(!n.nodeValue||(p.closest&&p.closest("script,style,textarea,#hlbar,#toc,#tocbtn")))?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT}}),a=[],n;while(n=w.nextNode())a.push(n);return a}
function off(list,node,o){if(node.nodeType===3){var c=0;for(var i=0;i<list.length;i++){if(list[i]===node)return c+o;c+=list[i].nodeValue.length}return null}
 var r=document.createRange();r.setStart(node,o);r.collapse(true);var c2=0;for(var j=0;j<list.length;j++){if(r.comparePoint(list[j],0)===1)return c2;c2+=list[j].nodeValue.length}return c2}
function wrap(s,e,col,id){var list=nodes(),c=0;list.forEach(function(n){var L=n.nodeValue.length,a=Math.max(s,c),b=Math.min(e,c+L);c+=L;if(a>=b)return;
 var t=n.nodeValue,pre=t.slice(0,a-(c-L)),mid=t.slice(a-(c-L),b-(c-L)),post=t.slice(b-(c-L)),m=document.createElement("mark");m.className="hl c-"+col;m.dataset.id=id;m.textContent=mid;
 var p=n.parentNode;if(pre)p.insertBefore(document.createTextNode(pre),n);p.insertBefore(m,n);if(post)p.insertBefore(document.createTextNode(post),n);p.removeChild(n)})}
var areas=document.createElement("div");areas.id="hlareas";root.appendChild(areas);
function drawArea(a){var d=document.createElement("div");d.className="areamark c-"+a.c;d.dataset.id=a.id;d.style.cssText="left:"+a.x+"%;top:"+a.y+"px;width:"+a.w+"%;height:"+a.h+"px";areas.appendChild(d)}
store.t.forEach(function(x){wrap(x.s,x.e,x.c,x.id)});store.a.forEach(drawArea);
var bar=document.getElementById("hlbar");
function setMode(m){mode=(mode===m)?"":m;document.body.classList.toggle("hl-text",mode==="text");document.body.classList.toggle("hl-area",mode==="area");document.body.classList.toggle("hl-erase",mode==="erase");
 [].forEach.call(bar.querySelectorAll("[data-mode]"),function(b){b.classList.toggle("on",b.dataset.mode===mode)})}
bar.addEventListener("click",function(ev){var b=ev.target.closest("button");if(!b)return;
 if(b.id==="hlopen"){bar.classList.toggle("open");if(!bar.classList.contains("open")&&mode)setMode(mode);return}
 if(b.dataset.mode)setMode(b.dataset.mode);else if(b.dataset.color){color=b.dataset.color;[].forEach.call(bar.querySelectorAll("[data-color]"),function(x){x.classList.toggle("on",x===b)})}
 else if(b.id==="hlclear"){if(confirm("Remove all your marks from this report?")){[].slice.call(root.querySelectorAll("mark.hl")).forEach(function(m){var p=m.parentNode;while(m.firstChild)p.insertBefore(m.firstChild,m);p.removeChild(m);p.normalize()});areas.innerHTML="";store={t:[],a:[]};save()}}});
function uid(){return Date.now().toString(36)+Math.random().toString(36).slice(2,6)}
function sel(){if(mode!=="text")return;var s=window.getSelection();if(!s||!s.rangeCount||s.isCollapsed)return;var r=s.getRangeAt(0);if(!root.contains(r.commonAncestorContainer))return;
 var list=nodes(),a=off(list,r.startContainer,r.startOffset),b=off(list,r.endContainer,r.endOffset);if(a===null||b===null||a>=b)return;var id=uid();wrap(a,b,color,id);store.t.push({s:a,e:b,c:color,id:id});save();s.removeAllRanges()}
document.addEventListener("mouseup",function(){setTimeout(sel,0)});document.addEventListener("touchend",function(){setTimeout(sel,50)});
document.addEventListener("click",function(ev){if(mode!=="erase")return;var m=ev.target.closest&&ev.target.closest("mark.hl,.areamark");if(!m)return;var id=m.dataset.id;
 [].slice.call(document.querySelectorAll('[data-id="'+id+'"]')).forEach(function(x){if(x.tagName==="MARK"){var p=x.parentNode;while(x.firstChild)p.insertBefore(x.firstChild,x);p.removeChild(x);p.normalize()}else x.remove()});
 store.t=store.t.filter(function(x){return x.id!==id});store.a=store.a.filter(function(x){return x.id!==id});save()});
var cap=document.createElement("div");cap.id="hlcap";root.appendChild(cap);var st=null,tmp=null;
function pt(ev){var r=root.getBoundingClientRect();return{x:ev.clientX-r.left,y:ev.clientY-r.top,w:r.width}}
cap.addEventListener("pointerdown",function(ev){if(mode!=="area")return;st=pt(ev);tmp=document.createElement("div");tmp.className="areamark c-"+color;areas.appendChild(tmp);cap.setPointerCapture(ev.pointerId);ev.preventDefault()});
cap.addEventListener("pointermove",function(ev){if(!st)return;var p=pt(ev),x=Math.min(st.x,p.x),y=Math.min(st.y,p.y);tmp.style.cssText="left:"+x+"px;top:"+y+"px;width:"+Math.abs(p.x-st.x)+"px;height:"+Math.abs(p.y-st.y)+"px"});
cap.addEventListener("pointerup",function(ev){if(!st)return;var p=pt(ev),x=Math.min(st.x,p.x),y=Math.min(st.y,p.y),w=Math.abs(p.x-st.x),h=Math.abs(p.y-st.y);areas.removeChild(tmp);tmp=null;st=null;
 if(w>8&&h>8){var a={x:+(x/p.w*100).toFixed(2),y:Math.round(y),w:+(w/p.w*100).toFixed(2),h:Math.round(h),c:color,id:uid()};store.a.push(a);drawArea(a);save()}});
})();</script>"""

HLBAR = ('<div id="hlbar"><div class="hltools"><button type="button" data-mode="text" title="Select text to highlight it">✎ Highlight text</button><button type="button" data-mode="area" title="Drag to mark an area, for example on a heatmap">▭ Mark area</button>'
         '<button type="button" data-mode="erase" title="Click a mark to remove it">⌫ Erase</button><span class="hlcols"><button type="button" class="hc c-y on" data-color="y" aria-label="Yellow"></button><button type="button" class="hc c-g" data-color="g" aria-label="Green"></button>'
         '<button type="button" class="hc c-p" data-color="p" aria-label="Pink"></button><button type="button" class="hc c-b" data-color="b" aria-label="Blue"></button></span>'
         '<button type="button" id="hlclear">Clear all</button><small>Marks are saved in this browser only.</small></div><button type="button" id="hlopen">✎ Mark up</button></div>')

NEW_CSS = """
.bandsec{padding:24px 32px}.bandsec>h2{font-size:20px}.dband{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:22px}
.dcard{display:flex;gap:18px;align-items:flex-start}.dcard .stagebox{flex:none;width:190px}.dcard .stage{max-width:190px}.dcard h3{border-top:0;padding-top:0;margin:0 0 8px;font-size:18px}.dcard p{margin:6px 0}
.hyp{margin-bottom:18px}a.gl{color:inherit;text-decoration:none}
#toc{position:fixed;z-index:60;left:10px;top:70px;width:232px;max-height:calc(100vh - 90px);overflow:auto;background:#fff;border:1px solid var(--line);padding:12px 8px 8px;font-size:13.5px;box-shadow:0 6px 24px rgba(0,0,0,.08)}
#toc .tochead{display:flex;justify-content:space-between;align-items:center;padding:0 8px 8px;color:var(--strong)}#toc #tocx{display:none;border:0;background:none;font-size:22px;cursor:pointer;line-height:1}
#toc ul{list-style:none;margin:0;padding:0}#toc li{position:relative}#toc li>a{display:block;padding:5px 30px 5px 10px;color:var(--muted);text-decoration:none;border-left:3px solid transparent}
#toc li>a:hover{color:var(--strong);background:var(--bg)}#toc li>a.on{color:var(--strong);font-weight:700;border-left-color:var(--accent);background:var(--insight)}
#toc li>ul{display:none;margin-left:10px}#toc li.open>ul{display:block}#toc li li>a{font-size:12.5px;padding:3px 26px 3px 10px}
#toc .cp{position:absolute;right:4px;top:3px;border:0;background:none;color:var(--soft);cursor:pointer;font-size:14px;opacity:0;padding:2px 5px}#toc li:hover>.cp,#toc .cp:focus,#toc .cp.done{opacity:1}#toc .cp.done{color:var(--best-fg)}
#toc .tochint{font-size:11.5px;color:var(--soft);margin:8px 10px 2px}
#tocbtn{display:none;position:fixed;z-index:61;left:14px;bottom:14px;background:#212529;color:#fff;border:0;padding:11px 16px;font:600 14px Barlow,sans-serif;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25)}
@media(max-width:1499px){#toc{transform:translateX(-110%);transition:transform .2s;top:0;left:0;max-height:100vh;height:100vh;width:280px}body.tocopen #toc{transform:none}#toc #tocx{display:block}#tocbtn{display:block}}
[id]{scroll-margin-top:70px}
button.lnk{border:0;background:none;color:var(--soft);cursor:pointer;font:inherit;font-weight:400;margin-left:8px;opacity:0;padding:0 4px}h2:hover>.lnk,h3:hover>.lnk,h4:hover>.lnk,.lnk:focus,.lnk.done{opacity:1}.lnk.done{color:var(--best-fg)}
#hlbar{position:fixed;z-index:62;right:14px;bottom:14px;display:flex;flex-direction:column;align-items:flex-end;gap:8px}
#hlbar .hltools{display:none;background:#fff;border:1px solid var(--line);padding:10px;box-shadow:0 6px 24px rgba(0,0,0,.15);flex-direction:column;gap:6px;min-width:190px}#hlbar.open .hltools{display:flex}
#hlbar button{font:600 13px Barlow,sans-serif;border:1px solid var(--line);background:#fff;padding:7px 10px;cursor:pointer;text-align:left;color:var(--strong)}#hlbar button.on{background:var(--insight);border-color:var(--accent)}
#hlbar #hlopen{background:#212529;color:#fff;border:0;padding:11px 16px;box-shadow:0 4px 14px rgba(0,0,0,.25)}#hlbar small{color:var(--soft);font-size:11.5px}
.hlcols{display:flex;gap:6px}#hlbar .hc{width:26px;height:26px;padding:0}#hlbar .hc.on{outline:2px solid var(--strong);outline-offset:1px}
.c-y{background:#fff3a3}.c-g{background:#c9f2c7}.c-p{background:#ffd1e0}.c-b{background:#cfe5ff}
#hlbar .hc.c-y{background:#fff3a3}#hlbar .hc.c-g{background:#c9f2c7}#hlbar .hc.c-p{background:#ffd1e0}#hlbar .hc.c-b{background:#cfe5ff}
mark.hl{color:inherit;padding:0}body.hl-erase mark.hl,body.hl-erase .areamark{cursor:pointer;outline:1px dashed #a12a1b}
main.page{position:relative}#hlareas{position:absolute;inset:0;pointer-events:none;z-index:30}.areamark{position:absolute;border:2px solid rgba(0,0,0,.35);opacity:.55;mix-blend-mode:multiply}body.hl-erase .areamark{pointer-events:auto}
#hlcap{display:none;position:absolute;inset:0;z-index:40;cursor:crosshair;touch-action:none}body.hl-area #hlcap{display:block}body.hl-text main{cursor:text}
@media print{#toc,#tocbtn,#hlbar,button.lnk{display:none!important}mark.hl,.areamark{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
@media(max-width:700px){.dcard{flex-direction:column}.dcard .stagebox{width:100%}}

@page{size:A4;margin:12mm 10mm}
@media print{
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
html,body{background:#fff!important;font-size:12px}
.page{max-width:none;padding:0}
.bar{position:static;height:auto;padding:6px 0;border-bottom:1px solid #ddd}
.sec{break-inside:auto!important;padding:14px 16px;margin:0 0 10px;box-shadow:none!important}
.sec.hero{padding:16px 18px}
h2,h3,h4,h5{break-after:avoid}
.finding:not(.mini),.insight,.tile,.cc,.aoicard2,.dcard,figure,li.ev,.xtile,.example,.callout,.readnote,.note,tr,.step,.exrow,.dchip{break-inside:avoid}
.tablewrap{overflow:visible!important}
table.re{font-size:10px}table.re th,table.re td{padding:3px 4px}table.re small{font-size:8.5px}
.stagebox,.stage,.heat{max-width:250px}.dcard .stagebox,.dcard .stage{max-width:150px}
.chart{max-width:100%}
.dband{grid-template-columns:1fr 1fr}.tiles{grid-template-columns:repeat(4,1fr)}.xgrid,.grid2,.two{grid-template-columns:1fr 1fr}
.sheet{max-width:100%}
textarea,#agent .btnrow,#agent details{display:none!important}
#agent:after{content:"The copy-paste AI prompt and the data pack are in the interactive HTML version of this report.";display:block;color:#555;margin-top:8px}
a.ext,a.ref{color:#333!important;text-decoration:none!important}
}
"""
POP = '<script>(function(){var p=document.createElement("div");p.id="dpop";document.body.appendChild(p);function show(el){while(p.firstChild)p.removeChild(p.firstChild);var t=document.createElement("div");t.className="th pic "+el.dataset.cls;var b=document.createElement("b");b.textContent="Design "+el.dataset.id;var s=document.createElement("small");s.textContent=el.dataset.name;p.appendChild(t);p.appendChild(b);p.appendChild(s);p.style.display="block";var r=el.getBoundingClientRect(),w=p.offsetWidth,h=p.offsetHeight,x=Math.min(Math.max(8,r.left),window.innerWidth-w-8),y=r.bottom+6;if(y+h>window.innerHeight-8)y=Math.max(8,r.top-h-6);p.style.left=x+"px";p.style.top=y+"px"}function hide(){p.style.display="none"}function ref(ev){return ev.target.closest&&ev.target.closest(".dref")}document.addEventListener("mouseover",function(ev){var el=ref(ev);if(el)show(el)});document.addEventListener("mouseout",function(ev){if(ref(ev))hide()});document.addEventListener("focusin",function(ev){var el=ref(ev);if(el)show(el)});document.addEventListener("focusout",function(ev){if(ref(ev))hide()});document.addEventListener("click",function(ev){var el=ref(ev);if(el)show(el);else hide()});document.addEventListener("keydown",function(ev){if(ev.key==="Escape"){hide();hg()}});})();(function(){var g=document.createElement("div");g.id="gpop";document.body.appendChild(g);function gl(ev){return ev.target.closest&&ev.target.closest(".gl")}function sg(el){g.textContent=el.dataset.tip;g.style.display="block";var r=el.getBoundingClientRect(),w=g.offsetWidth,h=g.offsetHeight,x=Math.min(Math.max(8,r.left),window.innerWidth-w-8),y=r.bottom+6;if(y+h>window.innerHeight-8)y=Math.max(8,r.top-h-6);g.style.left=x+"px";g.style.top=y+"px"}window.hg=function(){g.style.display="none"};document.addEventListener("mouseover",function(ev){var el=gl(ev);if(el)sg(el)});document.addEventListener("mouseout",function(ev){if(gl(ev))hg()});document.addEventListener("click",function(ev){var el=gl(ev);if(el)sg(el);else hg()});})();</script>'

CSS = """
:root{--bg:#f6f5f3;--card:#fff;--ink:#333;--strong:#1a1a1a;--muted:#5c5c5c;--soft:#6b6b6b;--line:#e7e4e0;--line2:#f0edea;--thbg:#fbfaf9;--accent:#fc7753;--accent-d:#b53d1b;
--tag-bg:#ede3f7;--tag-fg:#6b3fa0;--best-bg:#e4f3e8;--best-fg:#17652f;--worst-bg:#fbe9e7;--worst-fg:#a12a1b;--insight:#fff1ec}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 Barlow,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.bar{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:16px;padding:0 24px;height:58px}
.logo{display:inline-flex;align-items:center;font-weight:700;font-size:19px;color:var(--strong);letter-spacing:-.2px}.logo b{background:var(--accent);color:#1a1a1a;border-radius:50%;width:27px;height:27px;display:grid;place-items:center;font-size:15px;margin-right:1px}
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
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:20px}
.tile{background:#fff;border:1px solid var(--line);padding:18px 18px 16px}.tile .lab,.lab{display:block;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.72px;color:var(--muted)}
.tile b{display:block;font-size:24px;line-height:1.2;color:var(--strong);margin:8px 0 4px;font-weight:700}.tile .sub{color:var(--muted);font-size:14px}
.sec{background:#fff;border:1px solid var(--line);padding:28px 32px;margin:0 0 20px}.sec>h2{font-size:22.5px;font-weight:700;color:var(--strong);margin:0 0 16px}
h3{font-size:18px;margin:28px 0 10px;color:var(--strong);padding-top:18px;border-top:1px solid var(--line)}h4{font-size:16px;margin:22px 0 8px;color:var(--strong)}h5{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.72px;color:var(--muted);margin:20px 0 8px}
.lead{font-size:16.5px;margin:0 0 14px;color:var(--ink)}.muted{color:var(--muted)}.hint{color:var(--muted);font-size:13.5px;margin:8px 0}.small{font-size:13px}
.callout{background:var(--insight);border-left:4px solid var(--accent);padding:16px 20px;margin:0 0 16px}.callout .lab{color:var(--accent-d)}.callout p{margin:6px 0 0;font-size:17px;color:var(--strong)}
.note{background:var(--bg);padding:14px 16px;margin:14px 0;color:var(--muted)}.note b{color:var(--strong)}.box{background:var(--bg);padding:12px 14px;color:var(--muted);font-size:13.5px;margin:12px 0}
.insight{display:flex;gap:12px;background:var(--insight);padding:14px 16px;margin:0 0 8px;align-items:flex-start}.insight .chk{flex:none;margin-top:3px}.insight b{color:var(--strong)}
.xgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.xgrid.one{grid-template-columns:1fr}.xtile{border:1px solid var(--line);padding:14px 16px}.xtile p{margin:6px 0 0}
.cards4{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:14px 0}.cc{border:1px solid var(--line);border-top:3px solid var(--accent);padding:14px 16px 16px}.cc h4{margin:8px 0 6px;font-size:20px}.cc p{margin:0;color:var(--muted)}
.cards3{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}.aoicard2{border:1px solid var(--line);position:relative;background:#fff}.aoicard2 .meta{padding:12px 14px 14px}.aoicard2 .meta p{margin:6px 0 0;color:var(--muted);font-size:14px}.aoicard2 .meta p b{color:var(--strong)}.aoicard2 .meta span:not(.gl):not(.kv){margin:0 6px;color:var(--soft)}.aoicard2 .meta .kv{white-space:nowrap;margin:0;color:inherit}.aoicard2 .cbar{display:block;height:3px}
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
tr.grp th,tr.grp td{border-top:2px solid var(--line)}td.vc b{font-size:16px;color:var(--strong)}td.low{opacity:.8}td.big{background:var(--insight)}.rk{font-size:17px}small.ok{color:var(--best-fg)!important;font-weight:600}
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
.btnrow{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}details.datapack{border:1px solid var(--line);padding:14px 18px;margin:16px 0 0}details.datapack summary{cursor:pointer;font-weight:600;color:var(--strong)}textarea.dp{width:100%;height:300px;font:12.5px/1.5 ui-monospace,Consolas,Menlo,monospace;color:var(--ink);background:var(--thbg);border:1px solid var(--line);padding:14px;resize:vertical}#agent-prompt{width:100%;height:360px;font:12.5px/1.5 ui-monospace,Consolas,Menlo,monospace;color:var(--ink);background:var(--thbg);border:1px solid var(--line);padding:14px;resize:vertical}
.pbars{margin:8px 0 14px}.prow{display:grid;grid-template-columns:120px 1fr 44px 44px;gap:10px;align-items:center;margin:5px 0;font-size:14px}.prow .pl{color:var(--strong)}.prow b{text-align:right;color:var(--strong)}.prow .pp{color:var(--muted);text-align:right}
.wtabs>input{position:absolute;opacity:0;pointer-events:none}.wtabs .tabs{display:flex;gap:6px;margin:6px 0 10px}.wtabs .tabs label{border:1px solid var(--line);padding:6px 14px;cursor:pointer;font-weight:600;color:var(--muted);background:#fff}
.wtabs .wpane{display:none}.wtabs:has(input[value="3"]:checked) .wpane[data-w="3"],.wtabs:has(input[value="5"]:checked) .wpane[data-w="5"],.wtabs:has(input[value="10"]:checked) .wpane[data-w="10"]{display:block}
.wtabs:has(input[value="3"]:checked) label[data-w="3"],.wtabs:has(input[value="5"]:checked) label[data-w="5"],.wtabs:has(input[value="10"]:checked) label[data-w="10"]{background:var(--insight);border-color:var(--accent);color:var(--strong)}
.thead{display:flex;gap:12px;align-items:center;margin-bottom:12px}.thead h4{margin:0}.thead p{margin:2px 0 0}.tcol .switch{margin-top:12px}.alist{margin-top:10px}.alist .li{display:flex;gap:8px;margin:7px 0;align-items:flex-start}.alist .li .sw{margin-top:4px;flex:none}.alist .li span{display:block;color:var(--muted);font-size:13.5px}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0;font-size:13.5px;color:var(--muted)}.legend.small{font-size:13px}.legend span{display:inline-flex;align-items:center}
.chart{width:100%;height:auto;display:block;max-width:440px}.chart.wide{max-width:none}.chart .grid{stroke:var(--line);stroke-width:1}.chart text{fill:var(--ink);font-size:12px}.chart .axis{fill:var(--soft)}.chart .val{font-weight:600}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:28px}
.seq{font-size:16px;font-weight:700;color:var(--strong);margin:12px 0 2px}ul.plain{padding-left:20px;margin:10px 0}ul.plain li{margin:5px 0}
.example{background:var(--bg);padding:6px 18px 16px;margin-top:18px;max-width:600px}.exrow{display:grid;grid-template-columns:170px 1fr 48px;gap:12px;align-items:center;margin:8px 0}.exrow.total{border-top:1px solid var(--line);padding-top:10px;font-weight:700}.exrow b{text-align:right}
.links{margin:6px 0 0;color:var(--muted);font-size:14px}a.ext{color:var(--accent-d);text-decoration:none;white-space:nowrap;font-weight:600}a.ext:hover{text-decoration:underline}a.ext.s{font-size:13px}table.re thead a.ext{font-size:12px;text-transform:none;letter-spacing:0}
dl.ctx{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px 24px;margin:0}dl.ctx dt{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.72px;color:var(--muted)}dl.ctx dd{margin:3px 0 0}
dl.kv{display:grid;grid-template-columns:220px 1fr;gap:10px 18px;margin:0}dl.kv dt{font-weight:600;color:var(--strong)}dl.kv dd{margin:0;color:var(--muted)}
details.dash{border:1px solid var(--line);padding:14px 18px;margin:12px 0}details summary{cursor:pointer;font-weight:600;color:var(--strong)}
.kicker .ver{margin-left:auto;color:var(--soft);font-size:12px}
.sec.hero{border-top:6px solid var(--accent);padding:34px 40px;box-shadow:0 6px 28px rgba(252,119,83,.14)}.sec.hero>h2{font-size:30px;margin-bottom:20px}
.callout.big{padding:22px 26px}.callout.big p{font-size:21px;line-height:1.35}
ol.glance{list-style:none;padding:0;margin:8px 0 0;counter-reset:g}ol.glance li{counter-increment:g;padding:11px 0 11px 40px;border-bottom:1px solid var(--line2);position:relative}
ol.glance li:before{content:counter(g);position:absolute;left:0;top:11px;width:26px;height:26px;background:#212529;color:#fff;font-weight:700;display:grid;place-items:center;font-size:14px}
ol.glance a{color:var(--strong);text-decoration:none}ol.glance a:hover b{text-decoration:underline}
.ftag{display:inline-block;color:#fff;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;padding:2px 8px;margin-right:8px}.fconf{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.finding{border:1px solid var(--line);border-left:5px solid var(--c,var(--accent));padding:22px 26px;margin:18px 0;background:#fff;scroll-margin-top:72px}
.finding h3{border-top:0;padding-top:0;margin:6px 0 0;font-size:21px}.finding h5{margin:18px 0 6px}.finding p{margin:6px 0}
.fhead{display:flex;gap:14px;align-items:flex-start}.fnum{flex:none;width:34px;height:34px;background:var(--c,var(--accent-d));color:#fff;font-weight:700;font-size:18px;display:grid;place-items:center}
p.concl{font-size:17.5px;font-weight:600;color:var(--strong);margin:12px 0 4px}
.finding.mini{border-left-width:3px;padding:14px 18px;margin:10px 0}.finding.mini h4{margin:0 0 4px;font-size:16.5px}
ul.evs{list-style:none;padding:0;margin:6px 0}li.ev{background:var(--bg);padding:10px 14px;margin:6px 0}li.ev .evt{color:var(--ink)}.evd{margin:6px 0 2px}
.dchip{display:inline-block;background:#fff;border:1px solid var(--line);padding:2px 8px;font-size:12.5px;margin:2px 6px 2px 0;color:var(--muted)}.dchip b{color:var(--strong)}
.evl{font-size:13px;color:var(--muted);margin:6px 0 0}.evl span{font-weight:500;color:var(--soft)}.evl .sepdot{color:var(--soft);margin:0 4px}a.ref,.evl a.ext,.links a.ext{color:var(--muted);text-decoration:underline;text-decoration-color:#cfcac4;text-underline-offset:3px;font-weight:500}a.ref:hover,.evl a.ext:hover,.links a.ext:hover{color:var(--strong);text-decoration-color:var(--accent)}
.readnote{background:var(--bg);border-left:4px solid var(--accent);padding:12px 16px;margin:0 0 14px;color:var(--ink)}
.illus{display:inline-block;background:#e9e6e1;color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;padding:2px 7px;margin-right:6px}
footer{color:var(--soft);font-size:13px;text-align:center;padding:10px 0 30px}
@media(max-width:700px){.sec{padding:20px 16px}.aoicard{grid-template-columns:1fr}.xgrid{grid-template-columns:1fr}dl.kv{grid-template-columns:1fr}.hd{flex-direction:column}.comp-chart .crow{grid-template-columns:1fr}.bar nav{display:none}}
@media print{.finding{break-inside:avoid}.wtabs .tabs{display:none}.wtabs .wpane{display:block!important}#dpop,#gpop,.btnrow,details.datapack{display:none!important}#agent-prompt{height:auto}.bar{position:static}.bar nav,.btn{display:none}body{background:#fff}.sec{break-inside:avoid;border-color:#ddd}details{display:block}}
"""


def a11y_post(h):
    # Heading levels never skip a level for assistive technology (aria-level keeps the visual style), and chips inside links are not separate buttons
    prev = [1]

    def hd(m):
        lvl = int(m.group(1))
        eff = min(lvl, prev[0] + 1)
        prev[0] = eff
        return m.group(0) if eff == lvl else f'<h{lvl} aria-level="{eff}"{m.group(2)}>'
    h = re.sub(r"<h([1-6])((?:\s[^>]*)?)>", hd, h)
    return re.sub(r"<a\s[^>]*>.*?</a>", lambda m: m.group(0).replace(' tabindex="0" role="button"', ""), h, flags=re.S)


def build(spec, base):
    raw = json.dumps({k: x for k, x in spec.items() if not k.startswith("_")}, ensure_ascii=False, indent=1)
    spec["_base"] = base
    spec["_generated"] = spec.get("generated") or datetime.date.today().isoformat()
    ERRORS.clear()
    REFS.clear()
    CUR["spec"] = spec
    spec.update(expand_all({k: x for k, x in spec.items() if not k.startswith("_")}))
    spec["_raw_json"] = raw
    lint_differences(spec)
    for v in spec["variants"]:
        uri, _ = load_image(base, src_of(v["stimulus"]))
        DESIGNS[v["id"]] = {"name": v["name"], "cls": reg_image(uri)}
    m, o, variants = spec["method"], spec["overall"], spec["variants"]
    tiles = "".join([
        tile("Designs compared", str(len(variants)), " · ".join("{" + v["id"] + "}: " + v["name"].split("(")[0].strip() for v in variants)),
        tile("Viewers analysed", " · ".join("{" + v["id"] + "} " + str(seg_of(v, "All")["n"]) for v in variants), "all viewers, by design"),
        *(study_tiles(spec) or [tile("Time windows", "3", "first 3, 5 and 10 seconds"), tile("Primary metric", "VAI", "Composite of Reach, Speed, Hold")])])
    overall = findings_section(spec)
    retest = section("actions", "How to test it next", '<dl class="kv">' + "".join(f"<dt>{e(k.replace('_', ' ').title())}</dt><dd>{rich(x)}</dd>" for k, x in spec.get("retest", {}).items()) + "</dl>")
    limits = "".join(f"<li>{rich(x)}</li>" for x in spec.get("limits", []))
    changes = "".join(f"<li>{rich(x)}</li>" for x in spec.get("would_change", []))
    sources = "".join(f"<li>{rich(x)}</li>" for x in spec.get("sources", []))
    defs = "".join(f"<dt>{e(k)}</dt><dd>{e(x)}{support_link(k)}</dd>" for k, x in {
        "VAI": "RealEye's Visual Attention Index (0–100): the equal-weight mean of Reach, Speed and Hold. A relative score, not a share of viewers or of attention.",
        "Reach": "Share of viewers who looked at the AOI at least once in the window.", "Speed": "How soon the AOI is noticed after it becomes visible. Used to rank the viewing order.",
        "Hold": "How long attention stays on the AOI relative to the window.", "Viewing order": "AOIs ranked by VAI Speed: a relative hierarchy across viewers, not one person's scan path.",
        "AOI": "Area of Interest: a saved region of the image (tagline, pack, face, logo, brand name).", "Windows": "First 3, 5 and 10 s are cumulative and start at 0.5 s.",
        "Webcam eye tracking": "Gaze estimated from participants' own webcams in the RealEye platform. It shows where attention concentrates, with less precision than lab trackers.",
        "Quality filter": m.get("quality_filter", "Only viewers with data quality Average or better."),
        "Heatmap": "A picture of where viewers looked: warm colours (yellow, orange, red) mark where attention concentrated, cool colours where it did not. It is an illustration only: the analysis rests on VAI and its components, not on how a heatmap looks.",
        "Gender and age": "Viewers' own answers to the gender and age questions of the study. Audience groups under 30 viewers are indicative only.",
        "RealEye": "The online research platform with webcam eye tracking that ran this study and produced every number here."}.items())
    appendix = section("technical", "Technical appendix",
                       '<p class="muted">For analysts and researchers: how the study was run, the data used, and the limits of the evidence.</p>' + method_block(spec) + participants_appendix(spec) + version_block(spec) + vai_tech_notes()
                       + f'<h3>Evidence and limits</h3><ul class="plain">{limits}</ul>' + (f'<h4>What would change the recommendation</h4><ul class="plain">{changes}</ul>' if changes else "")
                       + f'<h3>Definitions</h3><dl class="kv">{defs}</dl><h3>Sources</h3><ul class="plain">{sources}</ul><h3>Dashboard AOI VAI report (unfiltered copy)</h3>'
                       + "".join(dashboard_vai(spec, v, i) for i, v in enumerate(variants)))
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t in (("overall", "Findings"), ("tested", "Designs"), ("who", "Participants"), ("vai", "VAI"), ("order", "Viewing order"), ("design-A", "Analysis"), ("compare", "Comparison"),
                                                          ("audience", "Gender and age"), ("actions", "Next steps"), ("technical", "Appendix"), ("blueprint", "Blueprint"), ("agent", "Ask an AI")))
    body = "".join(f'<a id="design-{v["id"]}"></a>' + design_sections(spec, v, i) for i, v in enumerate(variants))
    study = spec.get("app_title") or m.get("study") or spec.get("title", "")
    printer = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="1.8"><path d="M6 9V3h12v6M6 18H4v-7h16v7h-2M7 14h10v7H7z"/></svg>'
    info = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#5c5c5c" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></svg>'
    page = (f'<div class="kicker"><span class="re-tag">Report</span><span class="t">Visual Attention Report</span><span class="ver">made with {SKILL_NAME} v{SKILL_VERSION} · {e(spec["_generated"])}</span></div>'
            f'<div class="hd"><div><h1>{e(spec.get("title", ""))}</h1><p>{e(spec.get("subtitle", ""))} {e(spec.get("date", ""))}{" · " + e(spec["prepared_for"]) if spec.get("prepared_for") else ""}</p></div>'
            f'<button class="btn" onclick="window.print()">{printer} Print / Save as PDF</button></div>'
            f'{designs_band(spec)}<div class="strip">{info}<div><b>How this was measured</b><span>{e(m.get("banner", "RealEye platform, webcam eye tracking."))}</span></div></div>'
            f'{overall}{audience_section(spec)}{hypotheses_section(spec)}{intro_section(spec)}<div class="tiles">{tiles}</div>{participants_section(spec)}{vai_guide(spec)}{order_section(spec)}{body}{compare_section(spec)}{retest}{improve_section(spec)}{appendix}{blueprint_section(spec)}{agent_section(spec)}'
            f'<footer>Generated with the RealEye {SKILL_NAME} skill v{SKILL_VERSION} (report format {SCHEMA_VERSION}) on {e(spec["_generated"])}. Eye tracking shows where people looked, not what they understood, liked or will buy.</footer>')
    ids = set(re.findall(r'\bid="([^"]+)"', page))
    for r in sorted(set(REFS)):
        if r not in ids:
            ERRORS.append(f"a link points to #{r}, which does not exist in the report")
    if ERRORS:
        raise ReportError("\n".join("- " + x_ for x_ in dict.fromkeys(ERRORS)))
    page = a11y_post(page)
    tips = make_tips(spec)
    nav, page = tips(nav), tips(page)
    css_imgs = "".join(f".{c}{{background-image:url('{u}')}}" for u, c in IMAGES.items())
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="generator" content="{SKILL_NAME} {SKILL_VERSION}">'
            f'<title>{e(spec.get("title", "Visual Attention Report"))}</title>'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&display=swap" rel="stylesheet">'
            f'<style>{CSS}{NEW_CSS}</style></head><body><div class="bar"><span class="logo"><b>Re</b>alEye</span><span class="sep"></span><span class="study">{e(study)}</span></div>'
            f'<main class="page">{page}</main>' + toc_html(spec, ids) + HLBAR + f'<style>{css_imgs}</style>' + POP + POP2 + POP3 + POP4 + POP5 + '</body></html>')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json_file")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()
    src = Path(a.json_file).resolve()
    spec = json.loads(src.read_text(encoding="utf-8"))
    out = Path(a.output) if a.output else src.with_suffix(".html")
    try:
        html_out = build(spec, src.parent)
    except ReportError as ex:
        print("The report data has problems, nothing was written:\n" + str(ex), file=sys.stderr)
        return 1
    out.write_text(html_out, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    sys.exit(main())
