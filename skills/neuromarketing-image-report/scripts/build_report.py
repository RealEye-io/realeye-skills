#!/usr/bin/env python3
"""Render a neuromarketing report JSON file into one self-contained HTML report.

Usage:  python build_report.py report.json [-o report.html]

The report uses only RealEye's measured VAI (Visual Attention Index) and its three
components (Reach, Speed, Hold). Raw metrics such as time to first fixation are never
shown, because on their own they mislead. Standard library only (Pillow optional, only
to shrink large screenshots). Images are embedded as data URIs, so the result is a single
file. See references/html-report.md for the JSON schema.
"""
import argparse
import base64
import html
import json
import math
import mimetypes
import struct
import sys
from pathlib import Path

PALETTE = ["#e8590c", "#1c7ed6", "#2f9e44", "#ae3ec9"]
AOI_COLORS = ["#d9722f", "#37b24d", "#1c7ed6", "#d6336c", "#82c91e", "#7048e8", "#f08c00"]
MIN_N = 30
WIN_LABEL = {"3": "first 3 s", "5": "first 5 s", "10": "first 10 s"}
COMP = [("vai", "VAI"), ("reach", "Reach"), ("speed", "Speed"), ("hold", "Hold")]
KINDS = [("overall", "Overall"), ("gender", "Gender"), ("age", "Age"), ("gender_age", "Gender × age")]

e = lambda s: html.escape("" if s is None else str(s), quote=True)
color = lambda i: PALETTE[i % len(PALETTE)]


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


def figure(base, spec, alt, markers=None, cls="", wide=False):
    """spec: path or {"src","crop":[x0,y0,x1,y1] in source px,"caption"}."""
    if not spec:
        return ""
    if isinstance(spec, str):
        spec = {"src": spec}
    uri, size = load_image(base, spec.get("src"))
    crop = spec.get("crop")
    mk = "".join(f'<span class="mk" style="left:{x:.2f}%;top:{y:.2f}%">{e(l)}</span>' for l, x, y in (markers or []))
    if crop and size:
        W, H = size
        x0, y0, x1, y1 = crop
        cw, ch = x1 - x0, y1 - y0
        bx = x0 / (W - cw) * 100 if W != cw else 0
        by = y0 / (H - ch) * 100 if H != ch else 0
        inner = (f'<div class="crop {reg_image(uri)}" role="img" aria-label="{e(alt)}" style="aspect-ratio:{cw}/{ch};'
                 f'background-size:{W / cw * 100:.4f}% auto;background-position:{bx:.3f}% {by:.3f}%">{mk}</div>')
    else:
        inner = f'<div class="crop plain"><img src="{e(uri)}" alt="{e(alt)}">{mk}</div>'
    return f'<figure class="{cls}{" wide" if wide else ""}">{inner}<figcaption>{e(spec.get("caption", ""))}</figcaption></figure>'


# ------------------------------------------------------------------ data access
def seg_of(v, label):
    return next((s for s in v["segments"] if s["label"] == label), None)


def val(seg, w, ai, k):
    """VAI component value for window w ('3','5','10'), AOI index, component key."""
    wi = ["3", "5", "10"].index(w)
    o = wi * 20 + ai * 4
    return seg["values"][o + [c for c, _ in COMP].index(k)]


def names(spec):
    return spec["aoi_order"]


def rank_names(spec, seg, w, key="speed"):
    n = names(spec)
    return sorted(n, key=lambda nm: -val(seg, w, n.index(nm), key))


def small(seg):
    return seg["n"] < MIN_N


def lst(words):
    words = list(words)
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


# ------------------------------------------------------------------ charts
def lines(series, xlabels, title, w=380, h=200, ymax=100):
    """series: {name: ([values], color)}"""
    left, right, top, bot = 34, 12, 12, 34
    pw, ph = w - left - right, h - top - bot
    out = [f'<svg class="chart small" viewBox="0 0 {w} {h}" role="img" aria-label="{e(title)}">']
    for t in range(5):
        y = top + ph - ph * t / 4
        out.append(f'<line x1="{left}" x2="{w - right}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                   f'<text x="{left - 5}" y="{y + 4:.1f}" text-anchor="end" class="axis">{ymax * t // 4}</text>')
    xs = [left + pw * i / (len(xlabels) - 1) for i in range(len(xlabels))]
    for x, lab in zip(xs, xlabels):
        out.append(f'<text x="{x:.1f}" y="{h - 12}" text-anchor="middle" class="axis">{e(lab)}</text>')
    for nm, (vals, c) in series.items():
        pts = " ".join(f"{x:.1f},{top + ph - ph * min(v, ymax) / ymax:.1f}" for x, v in zip(xs, vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.4"/>')
        for x, v in zip(xs, vals):
            out.append(f'<circle cx="{x:.1f}" cy="{top + ph - ph * min(v, ymax) / ymax:.1f}" r="3" fill="{c}"/>')
    out.append("</svg>")
    return "".join(out)


def bars(cats, series, title, ymax=100, labelw=170):
    """Grouped horizontal bars. series: [(label, color, [value per cat])]"""
    bh, gap, gg, width = 14, 3, 14, 760
    gh = len(series) * (bh + gap)
    h = len(cats) * (gh + gg) + 8
    plot = width - labelw - 60
    out = [f'<svg class="chart" viewBox="0 0 {width} {h}" role="img" aria-label="{e(title)}">']
    for t in range(5):
        x = labelw + plot * t / 4
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{h - 4}" class="grid"/>')
    for gi, c in enumerate(cats):
        y0 = gi * (gh + gg) + 4
        out.append(f'<text x="{labelw - 10}" y="{y0 + gh / 2 + 4}" text-anchor="end" class="axis">{e(c)}</text>')
        for si, (lab, col, vals) in enumerate(series):
            y = y0 + si * (bh + gap)
            w = max(1.5, plot * vals[gi] / ymax)
            out.append(f'<rect x="{labelw}" y="{y}" width="{w:.1f}" height="{bh}" rx="3" fill="{col}"/>'
                       f'<text x="{labelw + w + 6:.1f}" y="{y + 11}" class="val">{vals[gi]:.1f}</text>')
    out.append("</svg>")
    return "".join(out)


def legend(items):
    return '<div class="legend">' + "".join(f'<span><i style="background:{c}"></i>{e(l)}</span>' for l, c in items) + "</div>"


def components_chart(spec, v, seg, w):
    n = names(spec)
    shades = ["#343a40", "#e8590c", "#4dabf7", "#f59f00"]
    bh, gap, gg, width, labelw = 11, 2, 14, 760, 170
    gh = 4 * (bh + gap)
    h = len(n) * (gh + gg) + 24
    plot = width - labelw - 70
    out = [f'<svg class="chart" viewBox="0 0 {width} {h}" role="img" aria-label="VAI components {e(v["name"])}">']
    for t in range(5):
        x = labelw + plot * t / 4
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{h - 20}" class="grid"/><text x="{x:.1f}" y="{h - 6}" text-anchor="middle" class="axis">{t * 25}</text>')
    for gi, nm in enumerate(n):
        y0 = gi * (gh + gg) + 4
        out.append(f'<text x="{labelw - 10}" y="{y0 + gh / 2 + 4}" text-anchor="end" class="axis">{e(nm)}</text>')
        for ci, (k, lab) in enumerate(COMP):
            x = val(seg, w, gi, k)
            y = y0 + ci * (bh + gap)
            out.append(f'<rect x="{labelw}" y="{y}" width="{max(1.5, plot * x / 100):.1f}" height="{bh}" rx="2" fill="{shades[ci]}"/>'
                       f'<text x="{labelw + max(1.5, plot * x / 100) + 5:.1f}" y="{y + 9}" class="val s">{lab} {x:.0f}</text>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ tables
def cell(seg, w, ai, heat=None):
    vai, r, s, h = (val(seg, w, ai, k) for k, _ in COMP)
    style = f' style="background:color-mix(in srgb,{heat} {min(vai, 100) * .55:.0f}%,transparent)"' if heat else ""
    cls = " low" if small(seg) else ""
    return f'<td class="vc{cls}"{style}><b>{vai:.0f}</b><small>{r:.0f} · {s:.0f} · {h:.0f}</small></td>'


def window_table(spec, v, vi):
    seg = seg_of(v, "All")
    head = "".join(f'<th colspan="1">{WIN_LABEL[w]}</th>' for w in ["3", "5", "10"])
    rows = ""
    for ai, nm in enumerate(names(spec)):
        a = next(x for x in v["aois"] if x["name"] == nm)
        rows += (f'<tr><th scope="row"><i class="dot" style="background:{a.get("color", "#999")}"></i>{e(nm)}<small>{e(a.get("role", ""))}</small></th>'
                 + "".join(cell(seg, w, ai, color(vi)) for w in ["3", "5", "10"]) + "</tr>")
    return (f'<div class="tablewrap"><table class="seg"><thead><tr><th>Element</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
            '<p class="muted small">Each cell: <b>VAI</b> (large) and Reach · Speed · Hold (small), 0–100.</p>')


def segment_table(spec, v, vi, kind, title):
    segs = [s for s in v["segments"] if s["kind"] == kind]
    if not segs:
        return ""
    head = "".join(f'<th>{e(s["label"])}<small>N = {s["n"]}{" †" if small(s) else ""}</small></th>' for s in segs)
    rows = ""
    for ai, nm in enumerate(names(spec)):
        for wi, w in enumerate(["3", "5", "10"]):
            lab = f'<th scope="row" rowspan="3">{e(nm)}</th>' if wi == 0 else ""
            rows += f'<tr class="{"grp" if wi == 0 else ""}">{lab}<th class="w">{WIN_LABEL[w]}</th>' + "".join(cell(s, w, ai, color(vi)) for s in segs) + "</tr>"
    return (f'<h5>{e(title)}</h5><div class="tablewrap"><table class="seg"><thead><tr><th>Element</th><th>Window</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>')


def gap_table(spec, variants, a_label, b_label, title):
    """segment b minus segment a, VAI and Speed per AOI/window, for every design."""
    rows = ""
    for vi, v in enumerate(variants):
        sa, sb = seg_of(v, a_label), seg_of(v, b_label)
        if not sa or not sb:
            continue
        for ai, nm in enumerate(names(spec)):
            cells = ""
            for w in ["3", "5", "10"]:
                dv = val(sb, w, ai, "vai") - val(sa, w, ai, "vai")
                ds = val(sb, w, ai, "speed") - val(sa, w, ai, "speed")
                strong = abs(dv) >= 10
                cells += f'<td class="{"big" if strong else ""}"><b>{dv:+.1f}</b><small>Speed {ds:+.1f}</small></td>'
            rows += f'<tr><th scope="row"><span class="vtag" style="background:{color(vi)}">{e(v["id"])}</span> {e(nm)}</th>{cells}</tr>'
    return (f'<h5>{e(title)}</h5><div class="tablewrap"><table class="seg"><thead><tr><th>Design · element</th>'
            + "".join(f"<th>{WIN_LABEL[w]}</th>" for w in ["3", "5", "10"]) + f'</tr></thead><tbody>{rows}</tbody></table></div>'
            '<p class="muted small">VAI points (large) and VAI Speed points (small). Bold-shaded cells differ by 10 or more VAI points.</p>')


# ------------------------------------------------------------------ sections
def method_section(spec):
    m = spec["method"]
    rows = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in (
        ("Platform", m.get("platform")), ("Eye tracking", m.get("tracking")), ("Study", m.get("study")),
        ("Participants analysed", m.get("participants")), ("Participant quality filter", m.get("quality_filter")),
        ("Time windows", m.get("windows")), ("Segments", m.get("segments")), ("Task and exposure", m.get("task")),
        ("Source", m.get("source")), ("Tracker precision", m.get("precision"))) if v)
    return f'<h3 class="sub3">About this study</h3><dl class="ctx">{rows}</dl><p class="muted small">{e(m.get("note", ""))}</p>'


def vai_guide(spec):
    g = spec["variants"][0]
    seg = seg_of(g, "All")
    n = names(spec)
    # worked example: the AOI with the lowest VAI at 10 s
    ai = min(range(len(n)), key=lambda i: val(seg, "10", i, "vai"))
    ex = {k: val(seg, "10", ai, k) for k, _ in COMP}
    bar = lambda lab, x, c: (f'<div class="exrow"><span>{lab}</span><div class="exbar"><i style="width:{x:.0f}%;background:{c}"></i></div><b>{x:.1f}</b></div>')
    example = (f'<div class="example"><h5>Worked example · {e(n[ai])}, design {e(g["id"])}, {WIN_LABEL["10"]}</h5>'
               + bar("Reach", ex["reach"], "#e8590c") + bar("Speed", ex["speed"], "#4dabf7") + bar("Hold", ex["hold"], "#f59f00")
               + f'<div class="exrow total"><span>VAI = mean of the three</span><div></div><b>{ex["vai"]:.1f}</b></div>'
               f'<p class="muted small">Only about {ex["reach"]:.0f}% of viewers reached it, those who did got there late (Speed {ex["speed"]:.0f}) and looked only briefly (Hold {ex["hold"]:.0f}). '
               "The low VAI is the combination of all three, which is why the components matter as much as the total.</p></div>")
    patterns = [
        ("High", "High", "High", "Strong element: almost everyone reaches it, soon, and stays on it.", "Keep it. Protect its position and size."),
        ("High", "High", "Low", "Seen fast by most viewers but only glanced at. Normal for a logo; a problem for a claim that must be read.", "If it must be read, shorten it or give it more room."),
        ("High", "Low", "any", "Reached eventually, but late: it competes with elements ahead of it in the viewing order.", "Move it earlier in the order or make it more salient."),
        ("Low", "Low", "Low", "Blind spot: few viewers reach it, late, and briefly.", "Relocate, enlarge, raise contrast, or remove clutter around it."),
        ("Low", "any", "High", "Hard to find, but viewers who find it read it: a placement problem, not a content problem.", "Move it into the path viewers already follow."),
    ]
    prow = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{f}</td></tr>" for a, b, c, d, f in patterns)
    return f"""
<section class="card" id="vai"><h2>What the scores mean (VAI)</h2>
<p><b>VAI (Visual Attention Index)</b> is RealEye's attention score for an element of the image (the tagline, the pack, the face, the logo). It runs from 0 to 100 and is the <b>average of three simple measures</b>:</p>
<div class="comp3">
 <div><h4>Reach</h4><p>How many viewers looked at it at all. <i>Did people get there?</i></p></div>
 <div><h4>Speed</h4><p>How soon they noticed it. <i>How early in the viewing order?</i> It is used here to rank the viewing order.</p></div>
 <div><h4>Hold</h4><p>How long attention stayed on it. <i>Did people stay?</i></p></div>
</div>
<h4>How to use it</h4>
<ul class="findings">
<li><b>Compare, don't grade.</b> VAI is not a percentage of viewers. Use it to rank the elements within a design and to compare the same element across designs, time windows or audiences.</li>
<li><b>Look at the three measures, not just the total.</b> The same VAI can hide very different stories (see the table below).</li>
<li><b>Higher is not always better.</b> A logo can do its job at a moderate score. What matters is that each element scores as the design intends.</li>
<li><b>It shows attention, not outcome.</b> It does not say whether viewers understood, liked or will buy; confirm with a recall or choice test.</li>
</ul>
<h4>Component patterns and what to do</h4>
<div class="tablewrap"><table><thead><tr><th>Reach</th><th>Speed</th><th>Hold</th><th>Reading</th><th>Typical action</th></tr></thead><tbody>{prow}</tbody></table></div>
{example}
</section>"""


def vai_tech_notes():
    return f"""<h3 class="sub3">Technical notes on VAI</h3><ul class="findings">
<li><b>Compare like with like:</b> the same element, the same time window and a similar number of viewers (N). Large elements, and elements that overlap others, naturally score higher.</li>
<li><b>Windows are cumulative.</b> "First 3 s" is 0.5–3 s, "first 5 s" is 0.5–5 s and "first 10 s" is 0.5–10 s. The first 0.5 s is skipped to reduce the effect of where viewers happened to be looking when the image appeared. Reach and Speed can only rise as the window grows; Hold is relative to the window, so it can fall even when viewers keep looking.</li>
<li><b>Small groups are noisy.</b> Audiences with fewer than {MIN_N} viewers are marked † and should be read as anecdotal.</li>
<li><b>VAI is the equal-weight mean of Reach, Speed and Hold</b> and is not a share of the image's attention.</li></ul>"""


def order_section(spec):
    variants = spec["variants"]
    n = names(spec)
    blocks = ""
    stable_all = True
    for vi, v in enumerate(variants):
        seg = seg_of(v, "All")
        orders = {w: rank_names(spec, seg, w) for w in ["3", "5", "10"]}
        stable = len({tuple(o) for o in orders.values()}) == 1
        stable_all &= stable
        rows = ""
        for ai, nm in enumerate(n):
            tds = ""
            for w in ["3", "5", "10"]:
                rk = orders[w].index(nm) + 1
                sp, rc = val(seg, w, ai, "speed"), val(seg, w, ai, "reach")
                tds += f'<td class="vc"><b class="rk">#{rk}</b><small>Speed {sp:.0f} · Reach {rc:.0f}%</small></td>'
            rows += f'<tr><th scope="row">{e(nm)}</th>{tds}</tr>'
        reach_txt = "".join(
            f'<li><b>{WIN_LABEL[w]}:</b> {lst([f"{nm} ({val(seg, w, n.index(nm), "reach"):.0f}%)" for nm in orders[w] if val(seg, w, n.index(nm), "reach") >= 50]) or "no element"} reached by half of the viewers or more.</li>'
            for w in ["3", "5", "10"])
        seq = " → ".join(orders["10"])
        blocks += (f'<div class="ordercol"><h4><span class="vtag" style="background:{color(vi)}">{e(v["id"])}</span> {e(v["name"])}</h4>'
                   f'<p class="seq">{e(seq)}</p>'
                   f'<p class="muted small">{"The order is the same in the first 3, 5 and 10 seconds." if stable else "The order changes between windows (see table)."}</p>'
                   f'<div class="tablewrap"><table class="seg"><thead><tr><th>Element</th>' + "".join(f"<th>{WIN_LABEL[w]}</th>" for w in ["3", "5", "10"]) +
                   f'</tr></thead><tbody>{rows}</tbody></table></div><ul class="findings">{reach_txt}</ul></div>')
    same = len({tuple(rank_names(spec, seg_of(v, "All"), "10")) for v in variants}) == 1
    lead = (f"In {'both designs' if len(variants) > 1 else 'the design'} viewers notice the elements in this order: "
            f"<b>{' → '.join(rank_names(spec, seg_of(variants[0], 'All'), '10'))}</b>"
            + (", and the order does not change between the first 3, 5 and 10 seconds." if stable_all and same else ".")
            if same else "The viewing order differs between the designs (see below).")
    overlays = "".join(figure(spec["_base"], v.get("aoi_overlay"), "Image with viewing order", markers=order_markers(spec, v), cls="ov") for v in variants)
    return f"""
<section class="card" id="order"><h2>Viewing order</h2>
<p class="lead">{lead}</p>
<p class="muted small">The order in which viewers notice the elements, across all viewers (not one person's scan path). #1 is noticed soonest; it is ranked by VAI Speed. The numbered circles show the first-10-seconds order.</p>
<div class="figs">{overlays}</div>
<div class="two">{blocks}</div></section>"""


def order_markers(spec, v):
    seg = seg_of(v, "All")
    order = rank_names(spec, seg, "10")
    out = []
    for a in v["aois"]:
        if a.get("marker"):
            out.append((order.index(a["name"]) + 1, a["marker"][0], a["marker"][1]))
    return out


def variant_section(spec, v, vi):
    base = spec["_base"]
    n = names(spec)
    seg = seg_of(v, "All")
    cols = {a["name"]: a.get("color", "#999") for a in v["aois"]}
    series = lambda k: {nm: ([val(seg, w, i, k) for w in ["3", "5", "10"]], cols[nm]) for i, nm in enumerate(n)}
    xl = ["first 3 s", "first 5 s", "first 10 s"]
    mini = "".join(f'<div><h5>{lab} by window</h5>{lines(series(k), xl, lab)}</div>' for k, lab in COMP)
    leg = legend([(nm, cols[nm]) for nm in n])
    sheets = "".join(figure(base, v["heatmap_sheets"][w], f"Heatmaps by segment, {WIN_LABEL[w]}", wide=True) for w in ["3", "5", "10"] if w in v.get("heatmap_sheets", {}))
    flist = "".join(f"<li>{e(f)}</li>" for f in v.get("findings", []))
    return f"""
<section class="card variant" id="variant-{e(v['id'])}">
  <div class="variant-head"><span class="badge" style="background:{color(vi)}">{e(v['id'])}</span>
    <div><h3>Design {e(v['id'])}: {e(v['name'])}</h3><p class="muted">{e(v.get('description', ''))}</p></div>
    <div class="nbox"><b>{seg['n']}</b><span>viewers</span></div></div>
  <div class="figs">{figure(base, v.get('aoi_overlay'), 'Analysed image with AOIs', cls='ov')}{figure(base, v.get('heatmap'), 'Measured heatmap', cls='hm')}</div>
  {leg}
  <h4>Scores for all viewers</h4>
  {window_table(spec, v, vi)}
  <h4>Reach, Speed and Hold in the first 10 seconds</h4>{components_chart(spec, v, seg, "10")}
  <h4>How attention builds up over time</h4>{leg}<div class="grid2">{mini}</div>
  <h4>What the data says</h4><ul class="findings">{flist}</ul>
  <h3 class="sub3">By gender, age and gender × age</h3>
  <p class="muted small">Each cell is the VAI for that audience, element and window, with Reach · Speed · Hold underneath. † marks a small audience (fewer than {MIN_N} viewers): read it as indicative.</p>
  {segment_table(spec, v, vi, "gender", "By gender")}
  {segment_table(spec, v, vi, "age", "By age")}
  {segment_table(spec, v, vi, "gender_age", "By gender × age")}
  <h3 class="sub3">Heatmaps by audience and time window</h3>
  <p class="muted small">{e(v.get('heatmap_note', ''))}</p>
  {sheets}
</section>"""


def compare_section(spec):
    variants = spec["variants"]
    if len(variants) < 2:
        return ""
    A, B = variants[0], variants[1]
    n = names(spec)
    sa, sb = seg_of(A, "All"), seg_of(B, "All")
    charts = ""
    for w in ["3", "5", "10"]:
        charts += f'<h4>VAI by element, {WIN_LABEL[w]}</h4>' + bars(n, [(f'{A["id"]} · {A["name"]}', color(0), [val(sa, w, i, "vai") for i in range(len(n))]),
                                                                  (f'{B["id"]} · {B["name"]}', color(1), [val(sb, w, i, "vai") for i in range(len(n))])], "VAI")
    rows = ""
    for ai, nm in enumerate(n):
        tds = ""
        for w in ["3", "5", "10"]:
            d = {k: val(sb, w, ai, k) - val(sa, w, ai, k) for k, _ in COMP}
            ra, rb = val(sa, w, ai, "reach"), val(sb, w, ai, "reach")
            ca, cb = round(ra / 100 * sa["n"]), round(rb / 100 * sb["n"])
            p1, p2 = ca / sa["n"], cb / sb["n"]
            se = math.sqrt(p1 * (1 - p1) / sa["n"] + p2 * (1 - p2) / sb["n"])
            lo, hi = (p2 - p1) * 100 - 196 * se, (p2 - p1) * 100 + 196 * se
            tag = ("indicative" if lo > 0 or hi < 0 else "within noise") if se else "within noise"
            tds += (f'<td class="vc"><b>{d["vai"]:+.1f}</b><small>R {d["reach"]:+.1f} · S {d["speed"]:+.1f} · H {d["hold"]:+.1f}</small>'
                    f'<small class="{"ok" if tag == "indicative" else ""}">Reach gap {tag}</small></td>')
        rows += f'<tr><th scope="row">{e(nm)}</th>{tds}</tr>'
    return f"""
<section class="card" id="compare"><h2>Head-to-head: design {e(B['id'])} versus design {e(A['id'])}</h2>
<p class="muted small">Differences are {e(B['id'])} minus {e(A['id'])}, in VAI points. R, S and H are the Reach, Speed and Hold differences. "Indicative" means the Reach gap is larger than chance would explain; the viewer groups may overlap, so treat it as a signal, not proof.</p>
<div class="tablewrap"><table class="seg"><thead><tr><th>Element</th>{''.join(f'<th>{WIN_LABEL[w]}</th>' for w in ['3', '5', '10'])}</tr></thead><tbody>{rows}</tbody></table></div>
{legend([(f'{A["id"]} · {A["name"]}', color(0)), (f'{B["id"]} · {B["name"]}', color(1))])}{charts}</section>"""


def audience_section(spec):
    variants = spec["variants"]
    text = "".join(f"<li>{e(x)}</li>" for x in spec.get("segment_findings", []))
    gaps = gap_table(spec, variants, "Men", "Women", "Women minus men (VAI points)")
    ga = ""
    ages = [s["label"] for s in variants[0]["segments"] if s["kind"] == "age"]
    if "18–24" in ages and "25–34" in ages:
        ga = gap_table(spec, variants, "18–24", "25–34", "Viewers 25–34 minus viewers 18–24 (VAI points; the 25–34 group is small, treat as anecdotal)")
    gga = gap_table(spec, variants, "Men 18–24", "Women 18–24", "Women 18–24 minus men 18–24 (VAI points; the largest groups)")
    return f"""
<section class="card" id="audience"><h2>Gender and age insights</h2>
<ul class="findings">{text}</ul>{gaps}{gga}{ga}
<p class="muted small">† Small audiences (fewer than {MIN_N} viewers) are indicative only. Full tables and heatmaps are in each design's section.</p></section>"""


def dashboard_vai(v, vi, base):
    d = v.get("dashboard_vai")
    if not d:
        return ""
    summ, wins, cols = d["summary"], d["windows"], d.get("aoi_colors", {})
    nm = list(summ.keys())
    best = lambda k: max(nm, key=lambda x: summ[x][k])
    worst = lambda k: min(nm, key=lambda x: summ[x][k])
    ex = "".join(f'<div class="kpi"><span>{e(t)}</span><b>{e(x)}</b><small>{e(s)}</small></div>' for t, x, s in (
        ("Top AOI by VAI", best("vai"), f'VAI {summ[best("vai")]["vai"]:.1f}'), ("Highest VAI Speed", best("speed"), f'Speed {summ[best("speed")]["speed"]:.1f}'),
        ("Highest VAI Hold", best("hold"), f'Hold {summ[best("hold")]["hold"]:.1f}'), ("Lowest VAI Reach", worst("reach"), f'Reach {summ[worst("reach")]["reach"]:.1f}')))
    rows = "".join(f'<tr><th scope="row"><i class="dot" style="background:{cols.get(x, "#999")}"></i>{e(x)}</th>' + "".join(f'<td>{summ[x][k]:.1f}</td>' for k, _ in COMP) + f'<td>{d["participants"]}</td></tr>' for x in nm)
    tabs = ""
    for k, lab in COMP:
        r = "".join(f'<tr><th scope="row">{e(x)}</th><td><b>{summ[x][k]:.1f}</b></td>' + "".join(f"<td>{t:.1f}</td>" for t in d["by_window"][k][x]) + "</tr>" for x in nm)
        tabs += f'<h5>{lab} per cumulative window</h5><div class="tablewrap"><table><thead><tr><th>AOI</th><th>Average</th>' + "".join(f"<th>{e(w)}</th>" for w in wins) + f"</tr></thead><tbody>{r}</tbody></table></div>"
    ins = "".join(f"<li>{e(x)}</li>" for x in d.get("insights", []))
    return f"""
<details class="card dash"><summary><span class="badge sm" style="background:{color(vi)}">{e(v['id'])}</span> Dashboard AOI VAI report, design {e(v['id'])} <small class="muted">· {e(d.get('scope', ''))}</small></summary>
<p class="notice">{e(d.get('note', ''))}</p>
<div class="figs">{figure(base, d.get('aoi_image'), 'Analysed image with AOIs')}<div><h5>Executive summary</h5><div class="kpis one">{ex}</div></div></div>
<h5>AOIs overview: VAI and components (average of the cumulative windows)</h5>
<div class="tablewrap"><table><thead><tr><th>AOI</th><th>VAI</th><th>Reach</th><th>Speed</th><th>Hold</th><th>Participants</th></tr></thead><tbody>{rows}</tbody></table></div>{tabs}
{('<h5>Insights from the dashboard report</h5><ul>' + ins + '</ul>') if ins else ''}</details>"""


# ------------------------------------------------------------------ page
def build(spec, base):
    spec["_base"] = base
    o = spec["overall"]
    m = spec["method"]
    variants = spec["variants"]
    kp = "".join(f'<div class="kpi"><span>{e(k["label"])}</span><b>{e(k["value"])}</b><small>{e(k.get("note", ""))}</small></div>' for k in o.get("kpis", []))
    finds = "".join(f'<div class="finding {e(f.get("tag", ""))}"><span class="tag">{e(f.get("tag", "").replace("-", " "))}</span><h4>{e(f["title"])}</h4><p>{e(f["text"])}</p></div>' for f in o.get("findings", []))
    concl = "".join(f"<li>{e(x)}</li>" for x in o.get("conclusions", []))
    actions = "".join(
        f'<li><span class="num">{i + 1}</span><div><h4>{e(a["title"])}</h4><p>{e(a["text"])}</p>' + (f'<p class="preserve"><b>Preserve:</b> {e(a["preserve"])}</p>' if a.get("preserve") else "") + "</div></li>"
        for i, a in enumerate(spec.get("actions", [])))
    retest = "".join(f"<dt>{e(k.replace('_', ' ').title())}</dt><dd>{e(x)}</dd>" for k, x in spec.get("retest", {}).items())
    limits = "".join(f"<li>{e(x)}</li>" for x in spec.get("limits", []))
    changes = "".join(f"<li>{e(x)}</li>" for x in spec.get("would_change", []))
    sources = "".join(f"<li>{e(x)}</li>" for x in spec.get("sources", []))
    defs = "".join(f"<dt>{e(k)}</dt><dd>{e(x)}</dd>" for k, x in {
        "VAI": "RealEye's Visual Attention Index (0–100): the equal-weight mean of Reach, Speed and Hold. A relative score, not a share of viewers or of attention.",
        "Reach": "Share of viewers who looked at the AOI at least once in the window.",
        "Speed": "How soon the AOI is noticed after it becomes visible. Used to rank the viewing order.",
        "Hold": "How long attention stays on the AOI relative to the window.",
        "Viewing order": "AOIs ranked by VAI Speed: a relative hierarchy across viewers, not one person's scan path.",
        "AOI": "Area of Interest: a saved region of the image (tagline, pack, face, logo, brand name).",
        "Windows": "First 3, 5 and 10 s are cumulative and start at 0.5 s.",
        "Webcam eye tracking": "Gaze estimated from participants' own webcams in the RealEye platform. It shows where attention concentrates, with less precision than lab trackers.",
        "Quality filter": m.get("quality_filter", "Only viewers with data quality Average or better.")}.items())
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t in (("overall", "Findings"), ("vai", "What VAI means"), ("order", "Viewing order"), ("variants", "Per design"), ("compare", "Comparison"), ("audience", "Gender and age"), ("actions", "Next steps"), ("technical", "Technical appendix")))
    var_html = "".join(variant_section(spec, v, i) for i, v in enumerate(variants))
    banner = (f'<div class="banner"><b>How this was measured:</b> {e(m.get("banner", "RealEye platform, webcam eye tracking."))}</div>')

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(spec.get('title', 'Neuromarketing report'))}</title>
<style>
:root{{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--muted:#6b6b72;--line:#e4e2dc;--accent:#e8590c;--ok:#2f9e44;--warn:#e67700;--risk:#c92a2a;--soft:#faf9f6}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#141416;--card:#1d1d20;--ink:#f1f0ec;--muted:#a1a1a8;--line:#323237;--soft:#242428}}}}
:root[data-theme=dark]{{--bg:#141416;--card:#1d1d20;--ink:#f1f0ec;--muted:#a1a1a8;--line:#323237;--soft:#242428}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
.wrap{{max-width:1120px;margin:0 auto;padding:0 20px 64px}}
header.hero{{padding:44px 0 18px}}
.eyebrow{{color:var(--accent);font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:.78rem}}
h1{{font-size:clamp(1.8rem,4vw,2.7rem);line-height:1.15;margin:.3em 0 .2em}}
h2{{font-size:1.5rem;margin:0 0 .6em}}h3{{font-size:1.25rem;margin:0}}h3.sub3{{margin:2em 0 .3em;padding-top:1em;border-top:1px solid var(--line)}}h4{{margin:1.6em 0 .5em;font-size:1.02rem}}h5{{margin:1.2em 0 .4em;font-size:.85rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}}
.sub{{color:var(--muted);font-size:1.08rem;max-width:780px}}
.banner{{border:1px solid var(--accent);background:color-mix(in srgb,var(--accent) 8%,transparent);border-radius:10px;padding:12px 16px;margin:16px 0 0;font-size:.95rem}}
nav.toc{{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);display:flex;gap:18px;overflow-x:auto;padding:10px 0;margin:18px 0 24px}}
nav.toc a{{color:var(--muted);text-decoration:none;font-size:.9rem;white-space:nowrap}}nav.toc a:hover{{color:var(--accent)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:26px;margin:0 0 22px}}
dl.ctx{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px 24px;margin:0}}
dl.ctx dt{{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}}dl.ctx dd{{margin:2px 0 0;font-size:.95rem}}
.verdict{{border-left:5px solid var(--accent);background:var(--soft);padding:16px 20px;border-radius:0 10px 10px 0;margin:18px 0}}
.vlabel{{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);font-weight:700}}.verdict p{{margin:.3em 0 0;font-size:1.08rem}}
.lead{{font-size:1.1rem}}.seq{{font-size:1.05rem;font-weight:700;margin:.2em 0}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-top:16px}}.kpis.one{{grid-template-columns:1fr}}
.kpi{{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:14px}}.kpi span{{display:block;font-size:.78rem;color:var(--muted)}}
.kpi b{{display:block;font-size:1.5rem;line-height:1.2}}.kpi small{{color:var(--muted)}}
.finds{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.finding{{border:1px solid var(--line);border-top:4px solid var(--muted);border-radius:10px;padding:16px;background:var(--soft)}}
.finding.strength{{border-top-color:var(--ok)}}.finding.risk{{border-top-color:var(--risk)}}.finding.weak-evidence{{border-top-color:var(--warn)}}
.finding h4{{margin:.3em 0}}.finding p{{margin:0;color:var(--muted);font-size:.95rem}}
.tag{{font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;font-weight:700;color:var(--muted)}}
.variant-head{{display:flex;gap:16px;align-items:center;flex-wrap:wrap}}.variant-head>div:nth-child(2){{flex:1;min-width:220px}}
.badge{{width:44px;height:44px;border-radius:12px;color:#fff;font-weight:800;display:grid;place-items:center;font-size:1.2rem;flex:none}}.badge.sm{{width:26px;height:26px;font-size:.85rem;border-radius:8px;display:inline-grid;vertical-align:middle;margin-right:6px}}
.vtag{{display:inline-block;min-width:22px;padding:0 6px;border-radius:6px;color:#fff;font-weight:700;text-align:center;font-size:.82rem}}
.nbox{{text-align:right}}.nbox b{{display:block;font-size:1.5rem}}.nbox span{{font-size:.75rem;color:var(--muted)}}
.figs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin:18px 0;align-items:start}}
figure{{margin:0;max-width:520px}}figure.wide{{max-width:none;margin:14px 0}}.crop{{position:relative;width:100%;border-radius:10px;border:1px solid var(--line);background-repeat:no-repeat}}
.crop.plain img{{display:block;width:100%;border-radius:10px}}figcaption{{font-size:.8rem;color:var(--muted);margin-top:6px}}
.mk{{position:absolute;transform:translate(-50%,-50%);width:30px;height:30px;border-radius:50%;background:#212529;color:#fff;font-weight:800;font-size:.95rem;display:grid;place-items:center;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5)}}
.tablewrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:.92rem}}
th,td{{padding:8px 11px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
thead th{{font-size:.74rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}}
tbody th{{font-weight:600}}th small,td small{{display:block;color:var(--muted);font-weight:400;font-size:.74rem}}small.ok{{color:var(--ok);font-weight:600}}
table.seg td,table.seg thead th{{text-align:center}}table.seg th{{text-align:left}}table.seg th.w{{font-weight:400;color:var(--muted);font-size:.8rem;white-space:nowrap}}
tr.grp th,tr.grp td{{border-top:2px solid var(--line)}}td.vc b{{font-size:1.05rem}}td.low{{opacity:.55}}td.big{{background:color-mix(in srgb,var(--accent) 16%,transparent)}}.rk{{font-size:1.1rem}}
.dot{{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:6px}}
.findings li{{margin:.4em 0}}.muted{{color:var(--muted)}}.small{{font-size:.82rem}}
.chart{{width:100%;height:auto;display:block}}.chart.small{{max-width:420px}}.chart .grid{{stroke:var(--line);stroke-width:1}}
.chart text{{fill:var(--ink);font-size:12px}}.chart .axis{{fill:var(--muted)}}.chart .val{{font-weight:600}}.chart .val.s{{font-size:10px;font-weight:500}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0 4px;font-size:.85rem}}.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
.two{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:24px}}.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}}
.comp3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:14px 0}}.comp3>div{{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:4px 16px 12px}}.comp3 h4{{margin:.8em 0 .3em}}.comp3 p{{margin:0;color:var(--muted);font-size:.93rem}}
.example{{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:6px 18px 14px;margin-top:18px;max-width:560px}}
.exrow{{display:grid;grid-template-columns:150px 1fr 48px;gap:10px;align-items:center;margin:6px 0;font-size:.9rem}}.exrow.total{{border-top:1px solid var(--line);padding-top:8px;font-weight:700}}.exbar{{height:12px;background:var(--line);border-radius:6px;overflow:hidden}}.exbar i{{display:block;height:100%}}.exrow b{{text-align:right}}
ol.actions{{list-style:none;margin:0;padding:0}}ol.actions li{{display:flex;gap:16px;padding:14px 0;border-bottom:1px solid var(--line)}}ol.actions li:last-child{{border:0}}
.num{{flex:none;width:32px;height:32px;border-radius:50%;background:var(--accent);color:#fff;font-weight:700;display:grid;place-items:center}}
ol.actions h4{{margin:0 0 .2em}}ol.actions p{{margin:.2em 0;color:var(--muted)}}.preserve{{color:var(--ink)!important;font-size:.9rem}}
details.dash{{margin:26px 0 0;background:var(--soft)}}details summary{{cursor:pointer;font-weight:600}}
.notice{{background:var(--card);border:1px dashed var(--warn);border-radius:8px;padding:10px 14px;font-size:.88rem;color:var(--muted)}}
dl.kv{{display:grid;grid-template-columns:220px 1fr;gap:10px 18px;margin:0}}dl.kv dt{{font-weight:600}}dl.kv dd{{margin:0;color:var(--muted)}}
@media(max-width:640px){{dl.kv{{grid-template-columns:1fr}}.card{{padding:18px}}}}
footer{{color:var(--muted);font-size:.8rem;text-align:center;padding:24px 0}}
@media print{{nav.toc{{display:none}}body{{background:#fff;color:#000;font-size:10.5pt}}.card{{break-inside:avoid}}.variant{{break-before:page}}details{{display:block}}}}
</style></head>
<body><div class="wrap">
<header class="hero"><div class="eyebrow">Neuromarketing report · RealEye webcam eye tracking</div>
<h1>{e(spec.get('title', ''))}</h1><p class="sub">{e(spec.get('subtitle', ''))}</p>
<p class="muted small">{e(spec.get('date', ''))}{' · ' + e(spec.get('prepared_for')) if spec.get('prepared_for') else ''}</p>{banner}</header>
<nav class="toc">{nav}</nav>

<section class="card" id="overall"><h2>Overall findings and conclusions</h2>
<div class="verdict"><span class="vlabel">{e(o.get('verdict_label', 'Conclusion'))}</span><p>{e(o.get('verdict_text', ''))}</p></div>
<p>{e(o.get('summary', ''))}</p><div class="kpis">{kp}</div>
<h4>Key findings</h4><div class="finds">{finds}</div>
{('<h4>Conclusions</h4><ul class="findings">' + concl + '</ul>') if concl else ''}
<h4>What to do next</h4><ol class="actions">{actions}</ol>
<p class="muted small">The detailed analysis follows: what the scores mean, the viewing order, each design, gender and age. Technical details are in the appendix at the end.</p></section>

{vai_guide(spec)}
{order_section(spec)}
<div id="variants">{var_html}</div>
{compare_section(spec)}
{audience_section(spec)}

<section class="card" id="actions"><h2>How to test it next</h2><dl class="kv">{retest}</dl></section>

<section class="card" id="technical"><h2>Technical appendix</h2>
<p class="muted">For analysts and researchers: how the study was run, the data used, and the limits of the evidence.</p>
{method_section(spec)}
{vai_tech_notes()}
<h3 class="sub3">Evidence and limits</h3><ul>{limits}</ul>
{('<h4>What would change the recommendation</h4><ul>' + changes + '</ul>') if changes else ''}
<h3 class="sub3">Definitions</h3><dl class="kv">{defs}</dl>
<h3 class="sub3">Sources</h3><ul>{sources}</ul>
<h3 class="sub3">Dashboard AOI VAI report (unfiltered copy)</h3>
{''.join(dashboard_vai(v, i, spec['_base']) for i, v in enumerate(variants))}
</section>
<footer>Generated with the RealEye neuromarketing-image-report skill. Eye tracking shows where people looked, not what they understood, liked or will buy.</footer>
</div>
<style>{"".join(f".{c}{{background-image:url('{u}')}}" for u, c in IMAGES.items())}</style>
</body></html>"""


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
