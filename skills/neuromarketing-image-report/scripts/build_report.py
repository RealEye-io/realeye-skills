#!/usr/bin/env python3
"""Render a neuromarketing report JSON file into one self-contained HTML report.

Usage:  python build_report.py report.json [-o report.html]

Standard library only. Images (AOI overlay, measured heatmap, stimulus) are embedded
as data URIs so the result is a single file that can be emailed, archived or printed
to PDF. Every number comes from the JSON; the script only derives viewing order,
ratios (count / N), differences with a 95% interval and the charts.
See references/html-report.md for the JSON schema.
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

PALETTE = ["#e8590c", "#1c7ed6", "#2f9e44", "#ae3ec9"]      # variants
AOI_COLORS = ["#d9722f", "#37b24d", "#1c7ed6", "#d6336c", "#82c91e", "#7048e8", "#f08c00"]
MIN_N = 30                                                  # segments below this are flagged

e = lambda s: html.escape("" if s is None else str(s), quote=True)


# ------------------------------------------------------------------ helpers
def color(i):
    return PALETTE[i % len(PALETTE)]


def aoi_color(a, i):
    return a.get("color") or AOI_COLORS[i % len(AOI_COLORS)]


def ratio_of(a):
    if a.get("ratio") is not None:
        return a["ratio"]
    if a.get("count") is not None and a.get("n"):
        return a["count"] / a["n"] * 100
    return None


def fmt(v, kind, d=None):
    if v is None:
        return "n/a"
    if kind == "pct":
        return f"{v:.0f}%"
    if kind == "pct1":
        return f"{v:.1f}%"
    if kind == "s":
        return f"{v:.2f} s"
    if kind == "n":
        return f"{v:g}"
    return f"{v}"


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
    if len(data) > 250_000:  # shrink big screenshots when Pillow is available (optional)
        try:
            import io
            from PIL import Image
            im = Image.open(io.BytesIO(data)).convert("RGB")
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=85, optimize=True)
            data, mime = buf.getvalue(), "image/jpeg"
        except Exception:
            pass
    return f"data:{mime};base64,{base64.b64encode(data).decode()}", image_size(data)


IMAGES = {}   # data URI -> css class, so each image is embedded once


def reg_image(uri):
    if uri not in IMAGES:
        IMAGES[uri] = f"im{len(IMAGES)}"
    return IMAGES[uri]


def figure(base, spec, alt, markers=None, cls=""):
    """spec: path or {"src","crop":[x0,y0,x1,y1] in source px,"caption"}.
    markers: list of (label, x%, y%, color) drawn over the image (viewing order)."""
    if not spec:
        return ""
    if isinstance(spec, str):
        spec = {"src": spec}
    uri, size = load_image(base, spec.get("src"))
    crop = spec.get("crop")
    mk = "".join(f'<span class="mk" style="left:{x:.2f}%;top:{y:.2f}%;background:{c}">{e(l)}</span>'
                 for l, x, y, c in (markers or []))
    if crop and size:
        W, H = size
        x0, y0, x1, y1 = crop
        cw, ch = x1 - x0, y1 - y0
        bx = x0 / (W - cw) * 100 if W != cw else 0
        by = y0 / (H - ch) * 100 if H != ch else 0
        inner = (f'<div class="crop {reg_image(uri)}" role="img" aria-label="{e(alt)}" style="aspect-ratio:{cw}/{ch};'
                 f"background-size:{W / cw * 100:.4f}% auto;"
                 f'background-position:{bx:.3f}% {by:.3f}%">{mk}</div>')
    else:
        inner = f'<div class="crop plain"><img src="{e(uri)}" alt="{e(alt)}">{mk}</div>'
    return f'<figure class="{cls}">{inner}<figcaption>{e(spec.get("caption", ""))}</figcaption></figure>'


def diff_ci(c1, n1, c2, n2):
    """p2 - p1 in percentage points with a Wald 95% interval."""
    p1, p2 = c1 / n1, c2 / n2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p2 - p1
    return d * 100, (d - 1.96 * se) * 100, (d + 1.96 * se) * 100


def find(aois, name):
    return next((a for a in aois if a["name"] == name), None)


def order_by(aois, key, reverse):
    have = [a for a in aois if a.get(key) is not None]
    return sorted(have, key=lambda a: a[key], reverse=reverse)


def reading(lo, hi, independent):
    if lo > 0 or hi < 0:
        return f'<span class="pill ok">{"likely real" if independent else "indicative"}</span>'
    return '<span class="pill">within noise</span>'


# ------------------------------------------------------------------ charts
def grouped_bars(variants, names, metric, kind, vmax=None, title="", labelw=170):
    def val(v, n):
        a = find(v["aois"], n)
        return None if a is None else (ratio_of(a) if metric == "ratio" else a.get(metric))
    vals = [[val(v, n) for n in names] for v in variants]
    flat = [x for r in vals for x in r if x is not None]
    vmax = vmax or (max(flat) * 1.15 if flat else 1)
    bh, gap, gg, width = 14, 3, 16, 760
    gh = len(variants) * (bh + gap)
    h = len(names) * (gh + gg) + 10
    plot = width - labelw - 70
    out = [f'<svg class="chart" viewBox="0 0 {width} {h}" role="img" aria-label="{e(title)}">']
    for t in range(5):
        x = labelw + plot * t / 4
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{h - 6}" class="grid"/>')
    for gi, n in enumerate(names):
        y0 = gi * (gh + gg) + 6
        out.append(f'<text x="{labelw - 10}" y="{y0 + gh / 2 + 4}" text-anchor="end" class="axis">{e(n)}</text>')
        for vi in range(len(variants)):
            v = vals[vi][gi]
            y = y0 + vi * (bh + gap)
            if v is None:
                out.append(f'<text x="{labelw + 4}" y="{y + 11}" class="na">n/a</text>')
                continue
            w = max(1.5, plot * v / vmax)
            out.append(f'<rect x="{labelw}" y="{y}" width="{w:.1f}" height="{bh}" rx="3" fill="{color(vi)}"/>')
            out.append(f'<text x="{labelw + w + 6:.1f}" y="{y + 11}" class="val">{e(fmt(v, kind))}</text>')
    out.append("</svg>")
    return "".join(out)


def legend(variants):
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{color(i)}"></i>{e(v["id"])} · {e(v["name"])}</span>'
        for i, v in enumerate(variants)) + "</div>"


def components_chart(v, vi):
    """VAI, Reach, Speed, Hold per AOI for one variant."""
    comps = [("vai", "VAI"), ("reach", "Reach"), ("speed", "Speed"), ("hold", "Hold")]
    shades = ["#343a40", color(vi), "#4dabf7", "#f59f00"]
    bh, gap, gg, width, labelw = 11, 2, 14, 760, 170
    aois = v["aois"]
    gh = len(comps) * (bh + gap)
    h = len(aois) * (gh + gg) + 24
    plot = width - labelw - 60
    out = [f'<svg class="chart" viewBox="0 0 {width} {h}" role="img" aria-label="VAI components {e(v["name"])}">']
    for t in range(5):
        x = labelw + plot * t / 4
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="0" y2="{h - 20}" class="grid"/>'
                   f'<text x="{x:.1f}" y="{h - 6}" text-anchor="middle" class="axis">{t * 25}</text>')
    for gi, a in enumerate(aois):
        y0 = gi * (gh + gg) + 4
        out.append(f'<text x="{labelw - 10}" y="{y0 + gh / 2 + 4}" text-anchor="end" class="axis">{e(a["name"])}</text>')
        for ci, (k, lab) in enumerate(comps):
            val = a.get(k)
            y = y0 + ci * (bh + gap)
            if val is None:
                continue
            w = max(1.5, plot * val / 100)
            out.append(f'<rect x="{labelw}" y="{y}" width="{w:.1f}" height="{bh}" rx="2" fill="{shades[ci]}"/>'
                       f'<text x="{labelw + w + 5:.1f}" y="{y + 9}" class="val s">{lab} {val:.0f}</text>')
    out.append("</svg>")
    return "".join(out)


def ttff_timeline(v, vi, vmax):
    """First-fixation timeline: each AOI at its average TTFF."""
    aois = order_by(v["aois"], "ttff", False)
    width, left, right = 760, 30, 30
    plot = width - left - right
    rows = len(aois)
    h = 56 + rows * 26
    out = [f'<svg class="chart" viewBox="0 0 {width} {h}" role="img" aria-label="First fixation timeline {e(v["name"])}">']
    for t in range(0, int(vmax) + 1):
        x = left + plot * t / vmax
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="14" y2="{h - 26}" class="grid"/>'
                   f'<text x="{x:.1f}" y="{h - 10}" text-anchor="middle" class="axis">{t} s</text>')
    for i, a in enumerate(aois):
        y = 26 + i * 26
        x = left + plot * a["ttff"] / vmax
        out.append(f'<line x1="{left}" x2="{x:.1f}" y1="{y}" y2="{y}" stroke="{color(vi)}" stroke-opacity=".35" stroke-width="3"/>'
                   f'<circle cx="{x:.1f}" cy="{y}" r="9" fill="{color(vi)}"/>'
                   f'<text x="{x:.1f}" y="{y + 4}" text-anchor="middle" class="mkt">{i + 1}</text>'
                   f'<text x="{min(x + 16, width - 160):.1f}" y="{y + 4}" class="val">{e(a["name"])} · {a["ttff"]:.2f} s</text>')
    out.append("</svg>")
    return "".join(out)


def window_lines(var, comp, windows):
    """Line chart of one VAI component across cumulative windows (dashboard report)."""
    data = var["by_window"][comp]
    width, h, left, right, top, bot = 360, 190, 34, 12, 12, 34
    pw, ph = width - left - right, h - top - bot
    out = [f'<svg class="chart small" viewBox="0 0 {width} {h}" role="img" aria-label="{e(comp)} by window">']
    for t in range(5):
        y = top + ph - ph * t / 4
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                   f'<text x="{left - 5}" y="{y + 4:.1f}" text-anchor="end" class="axis">{t * 25}</text>')
    xs = [left + pw * i / (len(windows) - 1) for i in range(len(windows))]
    for x, w in zip(xs, windows):
        out.append(f'<text x="{x:.1f}" y="{h - 12}" text-anchor="middle" class="axis">{e(w)}</text>')
    for i, (name, vals) in enumerate(data.items()):
        c = (var.get("aoi_colors") or {}).get(name) or AOI_COLORS[i % len(AOI_COLORS)]
        pts = " ".join(f"{x:.1f},{top + ph - ph * min(v, 100) / 100:.1f}" for x, v in zip(xs, vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.2"/>')
        for x, v in zip(xs, vals):
            out.append(f'<circle cx="{x:.1f}" cy="{top + ph - ph * min(v, 100) / 100:.1f}" r="3" fill="{c}"/>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ sections
def aoi_table(v, vi):
    rows = []
    for a in v["aois"]:
        r = ratio_of(a)
        bar = f'<div class="bar"><span style="width:{r:.0f}%;background:{color(vi)}"></span></div>' if r is not None else ""
        cnt = f' <small>({a["count"]}/{a["n"]})</small>' if a.get("count") is not None else ""
        rows.append(
            f'<tr><th scope="row">{e(a["name"])}<small>{e(a.get("role", ""))}</small></th>'
            f'<td class="ratio">{e(fmt(r, "pct"))}{cnt}{bar}</td>'
            f'<td>{e(fmt(a.get("ttff"), "s"))}</td><td>{e(fmt(a.get("fix_time"), "s"))}</td>'
            f'<td><b>{e(fmt(a.get("vai"), "pct"))}</b></td>'
            f'<td>{e(fmt(a.get("reach"), "pct"))}</td><td>{e(fmt(a.get("speed"), "pct"))}</td><td>{e(fmt(a.get("hold"), "pct"))}</td></tr>')
    return ('<div class="tablewrap"><table><thead><tr><th>AOI</th><th>Viewing ratio<br><small>fixation ratio</small></th><th>TTFF</th>'
            '<th>Fixation time<br><small>among fixators</small></th><th>VAI</th><th>Reach</th><th>Speed</th><th>Hold</th>'
            '</tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def order_markers(v):
    sp = order_by(v["aois"], "speed", True)
    rank = {a["name"]: i + 1 for i, a in enumerate(sp)}
    out = []
    for i, a in enumerate(v["aois"]):
        if a.get("marker") and a["name"] in rank:
            out.append((rank[a["name"]], a["marker"][0], a["marker"][1], "#212529"))
    return out


def viewing_order(v, vi, base):
    sp = order_by(v["aois"], "speed", True)
    tt = order_by(v["aois"], "ttff", False)
    li = "".join(f'<li><b>{e(a["name"])}</b><span>Speed {a["speed"]:.1f}</span></li>' for a in sp)
    lt = "".join(f'<li><b>{e(a["name"])}</b><span>first fixation at {a["ttff"]:.2f} s</span></li>' for a in tt)
    vmax = max([a["ttff"] for a in tt] + [6])
    vmax = math.ceil(vmax)
    note = ("Viewing order is a relative hierarchy across viewers, not one person's scan path. "
            "It is ranked two ways: by VAI Speed (RealEye's order, how soon each AOI is noticed relative to its visible window) "
            "and by average time to first fixation (TTFF) among viewers who fixated it. "
            "The numbered markers on the AOI image show the VAI Speed order (#1 = noticed soonest).")
    return (f'<h4>Viewing order</h4><p class="muted small">{note}</p>'
            f'<div class="two"><div><h5>By VAI Speed</h5><ol class="rank">{li}</ol></div>'
            f'<div><h5>By time to first fixation</h5><ol class="rank">{lt}</ol></div></div>'
            f'{ttff_timeline(v, vi, vmax)}')


def segment_matrix(v, vi, dim, title):
    segs = v.get("segments", {}).get(dim, [])
    if not segs:
        return ""
    names = [a["name"] for a in v["aois"]]
    head = "".join(f'<th>{e(s["label"])}<small>N = {s["n"]}{" †" if s["n"] < MIN_N else ""}</small></th>' for s in segs)
    blocks = ""
    for metric, kind, label, vmax in (("ratio", "pct", "Viewing ratio", 100), ("ttff", "s", "TTFF (lower = noticed sooner)", None),
                                      ("vai", "pct", "VAI", 100), ("reach", "pct", "VAI Reach", 100),
                                      ("speed", "pct", "VAI Speed", 100), ("hold", "pct", "VAI Hold", 100)):
        rows = []
        allv = [x for s in segs for a in s["aois"] for x in [ratio_of(a) if metric == "ratio" else a.get(metric)] if x is not None]
        top = vmax or (max(allv) if allv else 1)
        for n in names:
            cells = ""
            for s in segs:
                a = find(s["aois"], n)
                val = None if a is None else (ratio_of(a) if metric == "ratio" else a.get(metric))
                if val is None:
                    cells += '<td class="na">n/a</td>'
                    continue
                inten = min(1, val / top) if metric != "ttff" else max(0, 1 - val / top)
                cls = " low" if s["n"] < MIN_N else ""
                cells += (f'<td class="heat{cls}" style="background:color-mix(in srgb,{color(vi)} {inten * 55:.0f}%,transparent)">'
                          f'{e(fmt(val, kind))}</td>')
            rows.append(f'<tr><th scope="row">{e(n)}</th>{cells}</tr>')
        blocks += (f'<h5>{e(label)}</h5><div class="tablewrap"><table class="seg"><thead><tr><th>AOI</th>{head}</tr></thead>'
                   f'<tbody>{"".join(rows)}</tbody></table></div>')
    return f'<h4>{e(title)}</h4>{blocks}'


def gender_gap(v, independent):
    segs = {s["label"].lower(): s for s in v.get("segments", {}).get("gender", [])}
    f = segs.get("women") or segs.get("female")
    m = segs.get("men") or segs.get("male")
    if not f or not m:
        return ""
    rows = []
    for a in v["aois"]:
        fa, ma = find(f["aois"], a["name"]), find(m["aois"], a["name"])
        if not fa or not ma or fa.get("count") is None or ma.get("count") is None:
            continue
        d, lo, hi = diff_ci(ma["count"], ma["n"], fa["count"], fa["n"])
        t = (f'{fa["ttff"] - ma["ttff"]:+.2f} s' if fa.get("ttff") is not None and ma.get("ttff") is not None else "n/a")
        sp = (f'{fa["speed"] - ma["speed"]:+.1f}' if fa.get("speed") is not None and ma.get("speed") is not None else "n/a")
        rows.append(f'<tr><th scope="row">{e(a["name"])}</th><td>{ratio_of(ma):.0f}% → {ratio_of(fa):.0f}%</td>'
                    f'<td><b>{d:+.1f} pts</b><small>95% interval {lo:+.1f} to {hi:+.1f}</small></td><td>{t}</td><td>{sp}</td>'
                    f'<td>{reading(lo, hi, independent)}</td></tr>')
    return ('<h4>Gender gap: women vs men</h4><div class="tablewrap"><table><thead><tr><th>AOI</th><th>Viewing ratio<br><small>men → women</small></th>'
            '<th>Difference</th><th>TTFF change</th><th>VAI Speed change</th><th>Reading</th></tr></thead><tbody>'
            + "".join(rows) + f'</tbody></table></div><p class="muted small">Women N = {f["n"]}, men N = {m["n"]}. '
            'Viewers with other or unspecified gender are in the overall results but not in this comparison.</p>')


def dashboard_vai(v, vi, base):
    d = v.get("dashboard_vai")
    if not d:
        return ""
    summ = d["summary"]
    names = list(summ.keys())
    wins = d["windows"]
    cols = d.get("aoi_colors", {})
    best = lambda k: max(names, key=lambda n: summ[n][k])
    worst = lambda k: min(names, key=lambda n: summ[n][k])
    execs = [("Top AOI by VAI", best("vai"), f'highest measured VAI index ({summ[best("vai")]["vai"]:.1f}/100)'),
             ("Highest VAI Speed", best("speed"), f'noticed soonest relative to its visible window ({summ[best("speed")]["speed"]:.1f}/100)'),
             ("Highest VAI Hold", best("hold"), f'holds attention longest relative to its visible window ({summ[best("hold")]["hold"]:.1f}/100)'),
             ("Lowest VAI Reach", worst("reach"), f'fixated by the smallest share of participants ({summ[worst("reach")]["reach"]:.1f}/100)')]
    ex = "".join(f'<div class="kpi"><span>{e(t)}</span><b>{e(n)}</b><small>{e(s)}</small></div>' for t, n, s in execs)
    rows = "".join(
        f'<tr><th scope="row"><i class="dot" style="background:{cols.get(n, "#999")}"></i>{e(n)}</th>'
        + "".join(f'<td>{summ[n][k]:.1f}</td>' for k in ("vai", "reach", "speed", "hold")) + f'<td>{d["participants"]}</td></tr>'
        for n in names)
    charts = ""
    for comp, label in (("vai", "VAI"), ("reach", "VAI Reach"), ("speed", "VAI Speed"), ("hold", "VAI Hold")):
        charts += f'<div><h5>{label} by window</h5>{window_lines(d | {"aoi_colors": cols}, comp, wins)}</div>'
    leg = '<div class="legend">' + "".join(
        f'<span><i style="background:{cols.get(n, "#999")}"></i>{e(n)}</span>' for n in names) + "</div>"
    tabs = ""
    for comp, label in (("vai", "VAI"), ("reach", "VAI Reach"), ("speed", "VAI Speed"), ("hold", "VAI Hold")):
        r = "".join(f'<tr><th scope="row">{e(n)}</th><td><b>{summ[n][comp]:.1f}</b></td>'
                    + "".join(f'<td>{x:.1f}</td>' for x in d["by_window"][comp][n]) + "</tr>" for n in names)
        tabs += (f'<h5>{label} per cumulative window</h5><div class="tablewrap"><table><thead><tr><th>AOI</th><th>Average</th>'
                 + "".join(f"<th>{e(w)}</th>" for w in wins) + f"</tr></thead><tbody>{r}</tbody></table></div>")
    insights = "".join(f"<li>{e(x)}</li>" for x in d.get("insights", []))
    return f"""
<details class="card dash" id="dash-{e(v['id'])}"><summary><span class="badge sm" style="background:{color(vi)}">{e(v['id'])}</span>
 Dashboard AOI VAI report: {e(v['name'])} <small class="muted">· {e(d.get('scope', ''))}</small></summary>
<p class="notice">{e(d.get('note', ''))}</p>
<div class="figs">{figure(base, d.get('aoi_image'), 'Analysed image with AOIs ' + v['name'], markers=None)}<div><h5>Executive summary</h5><div class="kpis one">{ex}</div></div></div>
<h5>AOIs overview: measured VAI and its components (average of the cumulative windows)</h5>
<div class="tablewrap"><table><thead><tr><th>AOI</th><th>VAI</th><th>Reach</th><th>Speed</th><th>Hold</th><th>Participants</th></tr></thead><tbody>{rows}</tbody></table></div>
{leg}<div class="grid2">{charts}</div>{tabs}
{('<h5>Actionable insights from the dashboard report</h5><ul>' + insights + '</ul>') if insights else ''}
</details>"""


def full_metrics(v):
    keys = [("ttfg", "TTFG", "s"), ("gaze_time", "Gaze time", "s"), ("fixations", "Fixations", "n"), ("gazes", "Gazes", "n"),
            ("gazes_ratio", "Gazes ratio", "pct"), ("avg_fix_dur", "Avg fixation", "s"), ("ffd", "First fix. dur.", "s"),
            ("revisits", "Revisits", "n"), ("ttfc", "TTFC", "s"), ("k", "K-coef.", "n")]
    head = "".join(f"<th>{l}</th>" for _, l, _ in keys)
    rows = "".join(f'<tr><th scope="row">{e(a["name"])}</th>' + "".join(f'<td>{e(fmt(a.get(k), kd))}</td>' for k, _, kd in keys) + "</tr>"
                   for a in v["aois"])
    return (f'<h5>All AOI report metrics: {e(v["name"])}</h5><div class="tablewrap"><table><thead><tr><th>AOI</th>{head}</tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def variant_section(base, v, vi, window, study):
    flist = "".join(f"<li>{e(f)}</li>" for f in v.get("findings", []))
    mk = order_markers(v)
    legend_aoi = '<div class="legend">' + "".join(
        f'<span><i style="background:{aoi_color(a, i)}"></i>{e(a["name"])}</span>' for i, a in enumerate(v["aois"])) + "</div>"
    excl = v.get("excluded")
    qn_extra = f" · {e(excl)} below-Average excluded" if excl else ""
    seg_html = (segment_matrix(v, vi, "gender", "Viewing by gender") + gender_gap(v, study.get("independent_groups", False))
                + segment_matrix(v, vi, "age", "Viewing by age") + (f'<p class="muted small">{e(v.get("segment_note", ""))}</p>' if v.get("segments") else ""))
    return f"""
<section class="card variant" id="variant-{e(v['id'])}">
  <div class="variant-head"><span class="badge" style="background:{color(vi)}">{e(v['id'])}</span>
    <div><h3>{e(v['name'])}</h3><p class="muted">{e(v.get('description', ''))}</p></div>
    <div class="nbox"><b>{e(v['n'])}</b><span>tests analysed{qn_extra}</span></div></div>
  <div class="figs">
    <div>{figure(base, v.get('aoi_overlay'), 'Analysed image with AOIs', markers=mk, cls='ov')}{legend_aoi}</div>
    {figure(base, v.get('heatmap'), 'Measured heatmap', cls='hm')}
  </div>
  <h4>Viewing ratio, time and VAI by AOI <span class="muted">· window {e(window)}</span></h4>
  {aoi_table(v, vi)}
  <h4>VAI and its components</h4>
  <p class="muted small">VAI is the equal-weight mean of Reach (share of viewers who fixated the AOI), Speed (how soon it is noticed) and Hold (how long attention stays). It is a summary score, not a share of attention.</p>
  {components_chart(v, vi)}
  {viewing_order(v, vi, base)}
  {seg_html}
  <h4>What the data says</h4><ul class="findings">{flist}</ul>
  {dashboard_vai(v, vi, base)}
  <details class="more"><summary>All AOI report metrics</summary>{full_metrics(v)}</details>
</section>"""


def comparison_section(variants, study):
    names = [a["name"] for a in variants[0]["aois"]]
    charts = ""
    for metric, kind, title, vmax in (
        ("ratio", "pct", "Viewing ratio: share of viewers who looked at the AOI at least once", 100),
        ("ttff", "s", "Time to first fixation (lower = noticed sooner), among fixators", None),
        ("fix_time", "s", "Fixation time among fixators (longer = more looking, not necessarily more liking)", None),
        ("vai", "pct", "Measured VAI (summary only, not a share of attention)", 100),
        ("reach", "pct", "VAI Reach", 100), ("speed", "pct", "VAI Speed", 100), ("hold", "pct", "VAI Hold", 100)):
        if any(a.get(metric) is not None or (metric == "ratio" and ratio_of(a) is not None) for v in variants for a in v["aois"]):
            charts += f'<h4>{e(title)}</h4>{grouped_bars(variants, names, metric, kind, vmax, title)}'
    A, B = variants[0], (variants[1] if len(variants) > 1 else None)
    diff, order = "", ""
    if B:
        independent = study.get("independent_groups", False)
        rows = []
        for a in A["aois"]:
            b = find(B["aois"], a["name"])
            if not b or a.get("count") is None or b.get("count") is None:
                continue
            d, lo, hi = diff_ci(a["count"], a["n"], b["count"], b["n"])
            ttff = f'{b["ttff"] - a["ttff"]:+.2f} s' if a.get("ttff") is not None and b.get("ttff") is not None else "n/a"
            ft = f'{b["fix_time"] - a["fix_time"]:+.2f} s' if a.get("fix_time") is not None and b.get("fix_time") is not None else "n/a"
            vd = f'{b["vai"] - a["vai"]:+.0f}' if a.get("vai") is not None and b.get("vai") is not None else "n/a"
            rows.append(f'<tr><th scope="row">{e(a["name"])}</th><td>{ratio_of(a):.0f}% → {ratio_of(b):.0f}%</td>'
                        f'<td><b>{d:+.1f} pts</b><small>95% interval {lo:+.1f} to {hi:+.1f}</small></td>'
                        f'<td>{ttff}</td><td>{ft}</td><td>{vd}</td><td>{reading(lo, hi, independent)}</td></tr>')
        note = ("Groups were independent, so the intervals are standard." if independent else
                "The groups may overlap (same viewers, several images), so intervals are rough and labelled "
                "<i>indicative</i> rather than <i>likely real</i>.")
        diff = (f'<h4>Head to head: {e(B["id"])} versus {e(A["id"])}</h4><div class="tablewrap"><table><thead><tr><th>AOI</th><th>Viewing ratio</th>'
                '<th>Difference</th><th>TTFF change</th><th>Fixation time change</th><th>VAI change</th><th>Reading</th></tr></thead><tbody>'
                + "".join(rows) + f'</tbody></table></div><p class="muted small">{note} Differences are {e(B["id"])} minus {e(A["id"])}.</p>')
        # viewing order comparison
        ra = {a["name"]: i + 1 for i, a in enumerate(order_by(A["aois"], "speed", True))}
        rb = {a["name"]: i + 1 for i, a in enumerate(order_by(B["aois"], "speed", True))}
        ta = {a["name"]: i + 1 for i, a in enumerate(order_by(A["aois"], "ttff", False))}
        tb = {a["name"]: i + 1 for i, a in enumerate(order_by(B["aois"], "ttff", False))}
        orows = "".join(f'<tr><th scope="row">{e(n)}</th><td>#{ra.get(n, "–")} → #{rb.get(n, "–")}</td><td>#{ta.get(n, "–")} → #{tb.get(n, "–")}</td>'
                        f'<td>{"same order" if ra.get(n) == rb.get(n) and ta.get(n) == tb.get(n) else "order differs"}</td></tr>' for n in names)
        order = (f'<h4>Viewing order compared</h4><div class="tablewrap"><table><thead><tr><th>AOI</th><th>VAI Speed order<br><small>{e(A["id"])} → {e(B["id"])}</small></th>'
                 f'<th>First-fixation order<br><small>{e(A["id"])} → {e(B["id"])}</small></th><th></th></tr></thead><tbody>{orows}</tbody></table></div>')
    return (f'<section class="card" id="compare"><h2>Head-to-head comparison</h2>{legend(variants)}{order}{diff}{charts}</section>')


def segment_compare(variants):
    """Gender / age comparisons across designs for the brand-critical AOIs."""
    if len(variants) < 2 or not all(v.get("segments") for v in variants):
        return ""
    out = ""
    for dim, title in (("gender", "Gender"), ("age", "Age")):
        segs0 = variants[0]["segments"].get(dim, [])
        if not segs0:
            continue
        head = "".join(f'<th colspan="{len(variants)}">{e(s["label"])}</th>' for s in segs0)
        sub = "".join("".join(f'<th class="sub" style="color:{color(i)}">{e(v["id"])}</th>' for i, v in enumerate(variants)) for _ in segs0)
        rows = ""
        for a in variants[0]["aois"]:
            cells = ""
            for si, s in enumerate(segs0):
                for vi, v in enumerate(variants):
                    sv = v["segments"][dim][si]
                    x = find(sv["aois"], a["name"])
                    r = ratio_of(x) if x else None
                    cells += f'<td class="{"low" if sv["n"] < MIN_N else ""}">{e(fmt(r, "pct"))}</td>'
            rows += f'<tr><th scope="row">{e(a["name"])}</th>{cells}</tr>'
        ns = "".join("".join(f'<td class="sub">N={v["segments"][dim][si]["n"]}</td>' for v in variants) for si in range(len(segs0)))
        out += (f'<h4>Viewing ratio by {title.lower()}: designs side by side</h4><div class="tablewrap"><table class="seg"><thead>'
                f'<tr><th rowspan="2">AOI</th>{head}</tr><tr>{sub}</tr></thead><tbody>{rows}<tr><th>Sample</th>{ns}</tr></tbody></table></div>')
    return out


def build(spec, base):
    st = spec.get("study", {})
    d = spec.get("decision", {})
    variants = spec["variants"]
    window = st.get("window", "n/a")

    kpis = "".join(f'<div class="kpi"><span>{e(k["label"])}</span><b>{e(k["value"])}</b><small>{e(k.get("note", ""))}</small></div>' for k in spec.get("kpis", []))
    verdict = (f'<div class="verdict"><span class="vlabel">{e(d.get("verdict_label", "Recommendation"))}</span><p>{e(d.get("verdict_text", ""))}</p></div>')
    findings = "".join(
        f'<div class="finding {e(f.get("tag", ""))}"><span class="tag">{e(f.get("tag", "").replace("-", " "))}</span>'
        f'<h4>{e(f["title"])}</h4><p>{e(f["text"])}</p></div>' for f in spec.get("headline_findings", []))
    actions = "".join(
        f'<li><span class="num">{i + 1}</span><div><h4>{e(a["title"])}</h4><p>{e(a["text"])}</p>'
        + (f'<p class="preserve"><b>Preserve:</b> {e(a["preserve"])}</p>' if a.get("preserve") else "") + "</div></li>"
        for i, a in enumerate(spec.get("actions", [])))
    retest = "".join(f"<dt>{e(k.replace('_', ' ').title())}</dt><dd>{e(v)}</dd>" for k, v in spec.get("retest", {}).items())
    limits = "".join(f"<li>{e(x)}</li>" for x in spec.get("limits", []))
    changes = "".join(f"<li>{e(x)}</li>" for x in spec.get("would_change", []))
    sources = "".join(f"<li>{e(x)}</li>" for x in spec.get("sources", []))
    defs = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in {
        "Viewing ratio (fixation ratio)": "Share of the analysed viewers with at least one qualifying fixation in the AOI during the window. A miss means no recorded fixation, not 'did not see'.",
        "TTFF": "Time to first fixation: average time from exposure start to the first fixation in the AOI, among viewers who fixated.",
        "Fixation time": "Average time spent fixating the AOI, among viewers who fixated it. Long looks can mean interest or difficulty.",
        "VAI": "RealEye's Measured Visual Attention Index: the equal-weight mean of Reach, Speed and Hold. A summary score, not a percentage of viewers or of attention.",
        "VAI Reach": "Percentage of the viewers who had the opportunity and fixated the AOI.",
        "VAI Speed": "How quickly the AOI is noticed after it becomes visible. Used to rank the viewing order.",
        "VAI Hold": "How long attention dwells on the AOI relative to its visible window.",
        "Viewing order": "A relative hierarchy across viewers (by VAI Speed and by average TTFF), not one person's scan path.",
        "AOI": "Area of Interest: a saved region of the creative (logo, pack, claim, face).",
        "Quality filter": st.get("quality_filter", "Only viewers with data quality Average or better are analysed."),
        "Window": "The time slice analysed. RealEye commonly starts at 0.5 s to limit initial centre bias."}.items())
    nav = "".join(f'<a href="#{i}">{t}</a>' for i, t in (("summary", "Summary"), ("findings", "Findings"), ("variants", "Per design"),
                                                          ("compare", "Comparison"), ("segments", "Gender and age"), ("actions", "Actions"), ("limits", "Evidence")))
    var_html = "".join(variant_section(base, v, i, window, st) for i, v in enumerate(variants))
    cmp_html = comparison_section(variants, st) if len(variants) > 1 else ""
    seg_cmp = segment_compare(variants)
    seg_text = "".join(f"<li>{e(x)}</li>" for x in spec.get("segment_findings", []))
    seg_card = (f'<section class="card" id="segments"><h2>Gender and age insights</h2>'
                f'{("<ul class=findings>" + seg_text + "</ul>") if seg_text else ""}{seg_cmp}'
                f'<p class="muted small">† Segments with fewer than {MIN_N} viewers are shown muted; treat them as anecdotal.</p></section>') if (seg_cmp or seg_text) else ""
    ctx = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in (
        ("Study", st.get("name")), ("Window", window), ("Participant quality", st.get("quality_filter")),
        ("Task / exposure", st.get("task")), ("Audience", d.get("audience")), ("Placement", d.get("placement")),
        ("Primary outcome", d.get("primary_outcome")), ("Source", st.get("source"))) if v)

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
header.hero{{padding:48px 0 24px}}
.eyebrow{{color:var(--accent);font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:.78rem}}
h1{{font-size:clamp(1.8rem,4vw,2.7rem);line-height:1.15;margin:.3em 0 .2em}}
h2{{font-size:1.5rem;margin:0 0 .6em}}h3{{font-size:1.25rem;margin:0}}h4{{margin:1.6em 0 .5em;font-size:1.02rem}}h5{{margin:1.2em 0 .4em;font-size:.9rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}}
.sub{{color:var(--muted);font-size:1.08rem;max-width:780px}}
nav.toc{{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);display:flex;gap:18px;overflow-x:auto;padding:10px 0;margin-bottom:24px}}
nav.toc a{{color:var(--muted);text-decoration:none;font-size:.9rem;white-space:nowrap}}nav.toc a:hover{{color:var(--accent)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:26px;margin:0 0 22px}}
dl.ctx{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px 24px;margin:0}}
dl.ctx dt{{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}}dl.ctx dd{{margin:2px 0 0;font-size:.95rem}}
.verdict{{border-left:5px solid var(--accent);background:var(--soft);padding:16px 20px;border-radius:0 10px 10px 0;margin:18px 0}}
.vlabel{{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);font-weight:700}}.verdict p{{margin:.3em 0 0;font-size:1.08rem}}
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
.nbox{{text-align:right}}.nbox b{{display:block;font-size:1.5rem}}.nbox span{{font-size:.75rem;color:var(--muted)}}
.figs{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin:18px 0;align-items:start}}
figure{{margin:0;max-width:520px}}.crop{{position:relative;width:100%;border-radius:10px;border:1px solid var(--line);background-repeat:no-repeat}}
.crop.plain img{{display:block;width:100%;border-radius:10px}}figcaption{{font-size:.8rem;color:var(--muted);margin-top:6px}}
.mk{{position:absolute;transform:translate(-50%,-50%);width:28px;height:28px;border-radius:50%;color:#fff;font-weight:800;font-size:.9rem;display:grid;place-items:center;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5)}}
.tablewrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:.92rem}}
th,td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
thead th{{font-size:.74rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}}
tbody th{{font-weight:600}}th small,td small{{display:block;color:var(--muted);font-weight:400;font-size:.76rem}}td.ratio small{{display:inline}}
table.seg td{{text-align:center}}table.seg th{{text-align:left}}table.seg thead th{{text-align:center}}td.heat{{font-weight:600}}td.low{{opacity:.55}}td.na{{color:var(--muted)}}td.sub,th.sub{{text-align:center;font-size:.72rem;color:var(--muted)}}
.bar{{height:6px;background:var(--line);border-radius:3px;margin-top:6px;min-width:90px}}.bar span{{display:block;height:100%;border-radius:3px}}
.pill{{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.78rem;border:1px solid var(--line);color:var(--muted);white-space:nowrap}}
.pill.ok{{border-color:var(--ok);color:var(--ok);font-weight:600}}
.findings li{{margin:.4em 0}}.muted{{color:var(--muted)}}.small{{font-size:.82rem}}
.chart{{width:100%;height:auto;display:block}}.chart.small{{max-width:420px}}.chart .grid{{stroke:var(--line);stroke-width:1}}
.chart text{{fill:var(--ink);font-size:12px}}.chart .axis{{fill:var(--muted)}}.chart .val{{font-weight:600}}.chart .val.s{{font-size:10px;font-weight:500}}.chart .na{{fill:var(--muted);font-style:italic}}.chart .mkt{{fill:#fff;font-weight:800;font-size:11px}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0 4px;font-size:.85rem}}.legend i,.dot{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
.two{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}}.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:16px}}
ol.rank{{margin:0;padding-left:22px}}ol.rank li{{margin:.3em 0}}ol.rank li span{{color:var(--muted);margin-left:8px;font-size:.88rem}}
ol.actions{{list-style:none;margin:0;padding:0}}ol.actions li{{display:flex;gap:16px;padding:14px 0;border-bottom:1px solid var(--line)}}ol.actions li:last-child{{border:0}}
.num{{flex:none;width:32px;height:32px;border-radius:50%;background:var(--accent);color:#fff;font-weight:700;display:grid;place-items:center}}
ol.actions h4{{margin:0 0 .2em}}ol.actions p{{margin:.2em 0;color:var(--muted)}}.preserve{{color:var(--ink)!important;font-size:.9rem}}
details.dash{{margin:22px 0 0;background:var(--soft)}}details summary{{cursor:pointer;font-weight:600}}details.more{{margin-top:16px}}
.notice{{background:var(--card);border:1px dashed var(--warn);border-radius:8px;padding:10px 14px;font-size:.88rem;color:var(--muted)}}
dl.kv{{display:grid;grid-template-columns:220px 1fr;gap:10px 18px;margin:0}}dl.kv dt{{font-weight:600}}dl.kv dd{{margin:0;color:var(--muted)}}
@media(max-width:640px){{dl.kv{{grid-template-columns:1fr}}.card{{padding:18px}}}}
footer{{color:var(--muted);font-size:.8rem;text-align:center;padding:24px 0}}
@media print{{nav.toc{{display:none}}body{{background:#fff;color:#000;font-size:10.5pt}}.card{{break-inside:avoid}}.variant{{break-before:page}}details{{display:block}}details>summary{{margin-bottom:8px}}}}
</style></head>
<body><div class="wrap">
<header class="hero"><div class="eyebrow">Neuromarketing report · RealEye eye tracking</div>
<h1>{e(spec.get('title', ''))}</h1><p class="sub">{e(spec.get('subtitle', ''))}</p>
<p class="muted small">{e(spec.get('date', ''))}{' · ' + e(spec.get('prepared_for')) if spec.get('prepared_for') else ''}</p></header>
<nav class="toc">{nav}</nav>

<section class="card" id="summary"><h2>Decision at a glance</h2>{verdict}
<p>{e(d.get('summary', ''))}</p><div class="kpis">{kpis}</div><dl class="ctx" style="margin-top:22px">{ctx}</dl></section>

<section class="card" id="findings"><h2>Key findings</h2><div class="finds">{findings}</div></section>

<div id="variants">{var_html}</div>
{cmp_html}
{seg_card}

<section class="card" id="actions"><h2>Prioritised actions</h2><ol class="actions">{actions}</ol>
<h4>Retest plan</h4><dl class="kv">{retest}</dl></section>

<section class="card" id="limits"><h2>Evidence and limits</h2><ul>{limits}</ul>
{('<h4>What would change the recommendation</h4><ul>' + changes + '</ul>') if changes else ''}
<h4>Sources</h4><ul>{sources}</ul>
<h4>Metric definitions</h4><dl class="kv">{defs}</dl></section>
<footer>Generated with the RealEye neuromarketing-image-report skill. Gaze shows where people looked, not what they understood, liked or will buy.</footer>
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
