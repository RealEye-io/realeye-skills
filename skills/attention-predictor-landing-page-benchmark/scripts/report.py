#!/usr/bin/env python3
"""Build the report: main PDF (UI/UX/CRO analysis + guidelines), appendix PDF and a per-AOI CSV of every benchmark page.

  python scripts/report.py ap-work/example [--narrative ap-work/example/narrative.json] [--out reports] [--appendix reference|all|target] [--no-pdf]

--appendix: reference (default) = the target and its reference pages; all = every benchmark page (300+ pages, large PDF); target = only the target.

The narrative (verdict, actions, notes, guidelines, scorecard) is written by the agent after reading facts.md - see
templates/narrative.example.json. Missing parts are filled with data-driven defaults, so the report always builds.
"""
import argparse, csv, html, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import ASSETS_DIR, BLOCKS, CODE, COMP, DEVICES, TR, f1, f2, html_to_pdf, load, median, nm, quantile  # noqa: E402

E = lambda s: html.escape("" if s is None else str(s))  # noqa: E731
ORDER = {"target": 0, "previous": 0, "custom": 1, "saas": 2, "average": 3, "poor": 4}
SHORT = {"message": "Message-led", "balanced": "Balanced", "visual": "Visual-led"}
ST = {"blind": ("Blind spot", "#b3261e", "#fdecec"), "missing": ("Missing", "#b3261e", "#fdecec"), "low": ("Below range", "#8a5300", "#fff1d6"), "ok": ("In range", "#1e6b2a", "#e6f4e7"),
      "high": ("Above range", "#1c5cab", "#e8f1fc"), "absent": ("Not used", "#6b6a66", "#f0efea"), "na": ("n/a", "#6b6a66", "#f0efea")}
ROLE = {"key": "Key", "support": "Supporting", "optional": "Optional"}

CSS = """
body{font:9.6pt/1.42 "Segoe UI",system-ui,Arial,sans-serif;color:#0b0b0b;margin:0}
h1{font-size:21pt;margin:0 0 3pt;line-height:1.15} h2{font-size:13.5pt;margin:15pt 0 5pt;padding-bottom:2pt;border-bottom:1.5px solid #2a78d6} h3{font-size:10.8pt;margin:10pt 0 3pt}
.sub{color:#52514e;margin-bottom:8pt} p{margin:4pt 0} ul,ol{margin:3pt 0 3pt 15pt;padding:0} li{margin:2pt 0}
a{color:#1c5cab;text-decoration:none} .small{font-size:8pt;color:#52514e} .pb{break-before:page}
table.t{border-collapse:collapse;width:100%;font-size:8pt;margin:4pt 0;break-inside:avoid} .t th,.t td{border:1px solid #e1e0d9;padding:2pt 4pt;text-align:right;font-variant-numeric:tabular-nums} .t th{background:#f3f2ee;font-weight:600}
.t td:first-child,.t th:first-child{text-align:left} tr.bad td{background:#fdecec} tr.good td{background:#eaf5ea} tr.me td{background:#e8f1fc;font-weight:600}
table.anat td{text-align:left;vertical-align:top} table.anat td.n{text-align:right}
.tiles{display:flex;gap:7pt;margin:6pt 0} .tile{flex:1;border:1px solid #e1e0d9;border-radius:6pt;padding:6pt 8pt} .tile b{display:block;font-size:17pt;font-weight:600} .tile span{color:#52514e;font-size:8.2pt}
.shot{position:relative;border:1px solid #c3c2b7;overflow:hidden;flex:none} .shot img{position:absolute;left:0;top:0;width:100%;height:100%} .bx{position:absolute;border:1.6px solid;box-sizing:border-box}
.bx span{position:absolute;left:-1px;top:-1px;color:#fff;font:600 6.5pt/1.2 "Segoe UI",sans-serif;padding:0 2px;white-space:nowrap}
.heat{border:1px solid #c3c2b7;display:block} .row{display:flex;gap:8pt;align-items:flex-start} .col{flex:1;min-width:0}
.hg{display:grid;gap:3px;border:1px solid #c3c2b7;padding:3px;background:#fff} .hg div{position:relative} .hg img{width:100%;display:block} .hg span{position:absolute;left:0;top:0;background:rgba(0,0,0,.75);color:#fff;font:600 6.5pt sans-serif;padding:1px 4px}
.sw{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:3px} .leg{font-size:7.4pt;color:#52514e;margin:2pt 0} .leg span{margin-right:8px;white-space:nowrap}
figure.chart{margin:6pt 0;break-inside:avoid} figure.chart figcaption{font-weight:600;font-size:9.2pt;margin-bottom:2pt}
svg text{font:7.6px "Segoe UI",sans-serif;fill:#52514e} svg text.lt{fill:#0b0b0b;font-weight:700} svg text.m{font-size:7.2px}
.call{border-left:3px solid #2a78d6;background:#f4f8fd;padding:5pt 8pt;margin:6pt 0;break-inside:avoid}
.gl{border:1px solid #e1e0d9;border-radius:6pt;padding:6pt 9pt;margin:6pt 0;break-inside:avoid} .gl h3{margin:0 0 3pt} .gl .ev{font-size:8.2pt;color:#52514e}
.tag{display:inline-block;font-size:7pt;font-weight:600;padding:0 5px;border-radius:8px;background:#e8f1fc;color:#1c5cab;margin-left:4px}
.chip{display:inline-block;font-size:7.2pt;font-weight:600;padding:0 6px;border-radius:8px;white-space:nowrap} table.rc td{vertical-align:middle}
.gal{display:grid;grid-template-columns:repeat(3,1fr);gap:7pt} .gal .c{font-size:7.6pt;break-inside:avoid} .gal .c b{font-size:8.4pt}
"""


IMG_CACHE = {"dir": None}


def small(path, maxw):
    """JPEG copy (max width) of a large PNG so PDFs stay small; needs Pillow, otherwise the original is used."""
    p = Path(path)
    if not IMG_CACHE["dir"]:
        return p.resolve().as_uri()
    import hashlib  # short names: deep work folders hit the Windows 260-character path limit
    out = IMG_CACHE["dir"] / (hashlib.md5(str(p.resolve()).encode()).hexdigest()[:12] + f"_{maxw}.jpg")
    if not out.exists():
        try:
            from PIL import Image
            im = Image.open(p).convert("RGB")
            if im.width > maxw:
                im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
            im.save(out, "JPEG", quality=78, optimize=True)
        except Exception:  # noqa: BLE001
            return p.resolve().as_uri()
    return out.resolve().as_uri()


class Ctx:
    def __init__(self, res, narrative):
        self.res, self.N = res, narrative or {}
        self.T = res["target"]; self.P = res["peers"]; self.G = res["competitor_group"]
        self.all = dict(self.P); self.all[self.T["id"]] = self.T
        self.glabel = lambda g: res["group_labels"].get(g, g) if g != "previous" else "Previous version"
        self.cmp = res.get("_comparison"); self.pid = None
        if self.cmp:  # an earlier version of the same page: shown in the "Old vs new" section, the appendix and the CSV
            self.pid = self.cmp["prev_id"]; self.all[self.pid] = self.cmp["previous"]

    def approach_of(self, sid, dev):
        A = self.res["approach"][dev]
        if self.pid and sid == self.pid:
            return self.cmp["approach"][dev]["old_current"]
        return A["current"] if sid == self.T["id"] else A["members"].get(sid, "balanced")

    def img(self, sid, dev):
        s = self.all[sid]
        p = Path(s[dev]["img"])
        if s is self.T or p.is_absolute():  # the target and its previous version use absolute paths
            return small(p, 1100 if dev == "d" else 420)
        return (ASSETS_DIR / p).resolve().as_uri()

    def shot(self, dev, sid, w, vals=True):
        s = self.all[sid]; W, H = DEVICES[dev]["w"], DEVICES[dev]["h"]
        h = f'<div class="shot" style="width:{w}px;height:{round(w * H / W)}px"><img src="{self.img(sid, dev)}">'
        for k, a in s[dev]["aois"].items():
            b = a.get("box")
            if not b or k == "header":
                continue
            c = CODE.get(k, (k[:2].upper(), "#000"))
            h += (f'<div class="bx" style="border-color:{c[1]};left:{b[0]/W*100}%;top:{b[1]/H*100}%;width:{(b[2]-b[0])/W*100}%;height:{(b[3]-b[1])/H*100}%">'
                  f'<span style="background:{c[1]}">{c[0]}{(" " + f1(a.get("cas_3000"))) if vals else ""}</span></div>')
        return h + "</div>"

    def heat(self, dev, sid, w):
        s = self.all[sid]
        if s[dev].get("heat_files") or s is self.T:
            hf = s[dev].get("heat_files", {})
            if not hf:
                return '<div class="small">Heatmaps: open the heatmap analyser link.</div>'
            cols = 3 if dev == "d" else 6
            cells = "".join(f'<div><img src="{small(hf[c + "_" + t], 360 if dev == "d" else 200)}"><span>{lbl} {int(t) // 1000} s</span></div>'
                            for c, lbl in (("composite_attention", "Composite"), ("speed", "Speed"), ("reach", "Reach"), ("hold", "Hold")) for t in TR if (c + "_" + t) in hf)
            return f'<div class="hg" style="width:{w}px;grid-template-columns:repeat({cols},1fr)">{cells}</div>'
        p = ASSETS_DIR / s[dev].get("heat", "")
        return f'<img class="heat" style="width:{w}px" src="{p.resolve().as_uri()}">' if p.is_file() else ""

    def heat1(self, dev, sid, w, key="composite_attention_3000"):
        hf = self.all[sid][dev].get("heat_files", {})
        return f'<img class="heat" style="width:{w}px" src="{small(hf[key], w * 2)}">' if key in hf else ""

    def links(self, dev, sid):
        s = self.all[sid]; x = s[dev]; u = s.get("url") or ""
        return (f'<a href="{E(x.get("report_url"))}">AOI report</a> · <a href="{E(x.get("analyser_url"))}">Heatmap analyser</a> · '
                f'<a href="{E(u)}">{E(u.replace("https://", "").replace("http://", "").rstrip("/"))}</a>')

    def aoi_table(self, dev, sid, compact=False):
        x = self.all[sid][dev]
        h = ('<table class="t"><tr><th>AOI</th><th>Area %</th><th>CAS 3s</th><th>CAS 6s</th><th>CAS 10s</th><th>Speed 3s</th><th>Reach 3s</th><th>Hold 3s</th>'
             + ("" if compact else "<th>Speed 10s</th><th>Reach 10s</th><th>Hold 10s</th>") + "<th>Attn / area</th></tr>")
        for k, a in sorted(x["aois"].items(), key=lambda kv: -(kv[1].get("cas_3000") or 0)):
            c = CODE.get(k, ("", "#000"))
            h += (f'<tr><td><i class="sw" style="background:{c[1]}"></i>{c[0]} {E(nm(k))}</td><td>{f1(a.get("area"))}</td><td><b>{f1(a.get("cas_3000"))}</b></td>'
                  f'<td>{f1(a.get("cas_6000"))}</td><td>{f1(a.get("cas_10000"))}</td><td>{f1(a.get("speed_3000"))}</td><td>{f1(a.get("reach_3000"))}</td><td>{f1(a.get("hold_3000"))}</td>'
                  + ("" if compact else f'<td>{f1(a.get("speed_10000"))}</td><td>{f1(a.get("reach_10000"))}</td><td>{f1(a.get("hold_10000"))}</td>')
                  + f'<td>{f2(a.get("density"))}</td></tr>')
        return h + "</table>"

    def rank_table(self, dev, keys):
        M = self.res["metrics"][dev]; G = self.G; stat = {r["key"]: r["status"] for r in self.res["approach"][dev]["reference"]["checks"]}
        h = (f'<table class="t"><tr><th>AOI (share of predicted attention, CAS 3 s)</th><th>Target</th><th>SaaS median (IQR)</th><th>Rank vs SaaS</th>'
             + (f'<th>{E(self.glabel(G))} median</th><th>Rank vs {E(self.glabel(G))}</th>' if G else "") + f'<th>All {self.res["benchmark_size"]} pages: rank</th><th>Range check</th></tr>')
        for k in keys:
            x = M.get(k, {}).get("cas_3000")
            if not x:
                continue
            lbl = {"_message": "Message block (eyebrow + headline + subhead)", "_action": "Action block (hero CTAs + form)"}.get(k, nm(k))
            s, c, al = x.get("saas", {}), x.get(G, {}), x.get("all", {})
            h += (f'<tr{" class=bad" if stat.get(k) in ("blind", "missing") else ""}><td>{E(lbl)}</td><td><b>{"none" if x["target"] is None else f1(x["target"])}</b></td>'
                  f'<td>{f1(s.get("med"))} ({f1(s.get("p25"))}–{f1(s.get("p75"))})</td><td>{(str(s["rank"]) + " / " + str(s["of"])) if s.get("rank") else "–"}</td>'
                  + (f'<td>{f1(c.get("med"))}</td><td>{(str(c["rank"]) + " / " + str(c["of"])) if c.get("rank") else "–"}</td>' if G else "") +
                  f'<td>{(str(al["rank"]) + " / " + str(al["of"])) if al.get("rank") else "–"}</td><td>{self.chip(stat[k]) if k in stat else ""}</td></tr>')
        return h + "</table>"

    def profile(self, dev, k):
        M = self.res["metrics"][dev].get(k)
        if not M or M["cas_3000"]["target"] is None:
            return ""
        G = self.G
        h = f'<table class="t"><tr><th>{E(nm(k))}</th><th colspan="3">Composite (CAS)</th><th colspan="3">Speed</th><th colspan="3">Reach</th><th colspan="3">Hold</th></tr><tr><th></th>' + "<th>3s</th><th>6s</th><th>10s</th>" * 4 + "</tr>"
        row = lambda lbl, fn: "<tr><td>" + lbl + "</td>" + "".join("<td>" + fn(M[c + "_" + t]) + "</td>" for c in COMP for t in TR) + "</tr>"  # noqa: E731
        h += row("<b>Target</b>", lambda x: "<b>" + f1(x["target"]) + "</b>") + row("SaaS median", lambda x: f1(x["saas"]["med"]))
        h += row("Rank vs SaaS", lambda x: f'{x["saas"]["rank"]}/{x["saas"]["of"]}' if x["saas"].get("rank") else "–")
        for g in self.res.get("tiers", []):
            h += row(E(self.glabel(g)) + " median", lambda x, g=g: f1(x.get(g, {}).get("med")))
        if G:
            h += row(E(self.glabel(G)) + " median", lambda x: f1(x.get(G, {}).get("med"))) + row("Rank vs " + E(self.glabel(G)), lambda x: f'{x[G]["rank"]}/{x[G]["of"]}' if x.get(G, {}).get("rank") else "–")
        return h + "</table>"

    def chip(self, status):
        s = ST.get(status, ST["na"]); return f'<span class="chip" style="color:{s[1]};background:{s[2]}">{s[0]}</span>'

    def approach_line(self, dev):
        A = self.res["approach"][dev]; R = A["reference"]
        names = ", ".join(E(self.P[i]["name"]) for i in R["ids"])
        src = "hand-picked reference pages" if R.get("custom") else (f"{len(R['ids'])} benchmark pages built the same way" + (" (all groups: too few top-SaaS pages follow this approach)" if R.get("widened") else ""))
        how = "chosen as the intended approach" if A["intended_source"] == "chosen" else "the approach the page follows today"
        return (f'<b>{DEVICES[dev]["label"].capitalize()}: {E(self.res["approach_labels"][A["intended"]])}</b> ({how}; {E(self.res["approach_desc"][A["intended"]])}). '
                + (f'Today the page reads as {E(SHORT[A["current"]])}. ' if A["current"] != A["intended"] else "")
                + (f'<i>Note: {E(A["weak_fit"])}.</i> ' if A.get("weak_fit") else "") + f'Validated against {src}: {names}.')

    def range_table(self, dev):
        A = self.res["approach"][dev]; R = A["reference"]
        h = ('<table class="t rc"><tr><th>Element (CAS 3 s, % of predicted attention)</th><th>Role</th><th>Target</th><th>Reference range (p25–p75)</th><th>Median</th>' + "".join(f"<th>{E(self.glabel(g))} median</th>" for g in self.res.get("tiers", [])) +
             '<th style="text-align:left">Where the target sits (whisker = min–max, band = typical range, line = median)</th><th>Pages</th><th>Status</th></tr>')
        for r in R["checks"]:
            mx = max([v for v in (r["max"], r["target"]) if v is not None] or [1]) * 1.08; W = 190; X = lambda v: 4 + v / mx * (W - 8)  # noqa: E731
            g = ""
            if r["n"] >= 1 and r["min"] is not None:
                g += f'<line x1="{X(r["min"]):.1f}" x2="{X(r["max"]):.1f}" y1="7" y2="7" stroke="#a9a79f" stroke-width="1"/>'
                g += f'<rect x="{X(r["p25"]):.1f}" y="3" width="{max(1.5, X(r["p75"]) - X(r["p25"])):.1f}" height="8" rx="2" fill="#bfe0c2"/><line x1="{X(r["med"]):.1f}" x2="{X(r["med"]):.1f}" y1="2" y2="12" stroke="#1e6b2a" stroke-width="1.2"/>'
            if r["target"] is not None:
                g += f'<circle cx="{X(r["target"]):.1f}" cy="7" r="3.4" fill="{ST[r["status"]][1]}" stroke="#fff" stroke-width="1"/>'
            cls = ' class="bad"' if r["status"] in ("blind", "missing") else ""
            h += (f'<tr{cls}><td>{E(r["label"])}</td><td>{ROLE[r["role"]]}</td><td><b>{"none" if r["target"] is None else f1(r["target"])}</b></td><td>{(f1(r["p25"]) + "–" + f1(r["p75"])) if r["n"] >= 3 else "–"}</td><td>{f1(r["med"]) if r["n"] >= 3 else "–"}</td>' + "".join(f'<td>{f1((r.get("tiers") or {}).get(g, {}).get("med"))}</td>' for g in self.res.get("tiers", [])) +
                  f'<td style="text-align:left"><svg width="{W}" height="14">{g}</svg></td><td style="white-space:nowrap">{r["n"]} / {r["of"]}</td><td>{self.chip(r["status"])}</td></tr>')
        return h + "</table>"

    def spread_chart(self, dev, rows=None, caption=None):
        A = self.res["approach"][dev]; R = A["reference"]; W, lab, rowH = 690, 215, 19; pw = W - lab - 6
        if rows is None:
            rows = [(self.T["name"], A["target_spread"], True)]
            rows.append(("Reference: " + ("hand-picked pages" if R.get("custom") else SHORT[A["intended"]]) + f" (mean of {len(R['ids'])})", R["spread"], False))
            for a in A["by_approach"]:
                if a != A["intended"] or R.get("custom"):
                    rows.append((f'{SHORT[a]} pages (mean of {len(A["by_approach"][a]["ids"])})', A["by_approach"][a]["spread"], False))
        g = ""
        for i, (lbl, sp, me) in enumerate(rows):
            y = 3 + i * rowH; x = lab
            g += f'<text x="{lab - 6}" y="{y + 11}" text-anchor="end" class="{"lt" if me else ""}">{E(lbl)}</text>'
            for k, _, col in BLOCKS:
                w = sp.get(k, 0) / 100 * pw
                if w <= 0:
                    continue
                g += f'<rect x="{x:.1f}" y="{y}" width="{max(.5, w - 1):.1f}" height="{rowH - 5}" fill="{col}"/>'
                if w > 21:
                    g += f'<text x="{x + w / 2:.1f}" y="{y + 10.5}" text-anchor="middle" style="fill:{"#0b0b0b" if k == "other" else "#fff"};font-weight:600">{f1(sp[k])}</text>'
                x += w
        H = 3 + len(rows) * rowH
        return (f'<figure class="chart"><figcaption>{caption or "Attention spread, " + DEVICES[dev]["label"] + ", 3 s: where the first screen spends its attention budget (sums to 100%)"}</figcaption>'
                f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{g}</svg><div class="leg">' + " ".join(f'<span><i class="sw" style="background:{c}"></i>{E(l)}</span>' for _, l, c in BLOCKS)
                + ('</div></figure>' if caption else f'</div><div class="small">{f1(R["distance"])}% of the target\'s attention sits in a different block than in its reference group (0% = same spread).</div></figure>'))

    def bars(self, dev, getter, title):
        """Distribution of one value over the benchmark groups (one dot per page) with the target marked."""
        A = self.res["approach"][dev]; ref = A["reference"]["ids"]; tv = getter(self.T[dev])
        rows = [("Reference: " + ("hand-picked" if A["reference"].get("custom") else SHORT[A["intended"]]), ref, "#3f7d46")]
        rows += [(self.glabel(g), self.res["groups"].get(g, []), c) for g, c in (("saas", "#8a8883"), ("average", "#b9892b"), ("poor", "#b3261e")) if self.res["groups"].get(g)]
        if self.G:
            rows.append((self.glabel(self.G), self.res["groups"].get(self.G, []), "#5b6ee1"))
        data = [(lbl, [v for v in (getter(self.P[i][dev]) for i in ids) if v], len(ids), col) for lbl, ids, col in rows]
        allv = [v for _, vals, _, _ in data for v in vals] + ([tv] if tv else [])
        if not allv:
            return ""
        W, lab, rowH, top = 690, 190, 25, 14; pw = W - lab - 14; mx = max(allv) * 1.06; X = lambda v: lab + v / mx * pw  # noqa: E731
        H = top + len(data) * rowH + 16; g = ""
        step = next(s for s in (.1, .2, .5, 1, 2, 5, 10, 20, 50) if mx / s <= 9)
        k = 0
        while k * step <= mx:
            x = X(k * step); g += f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{H - 14}" stroke="#ecebe6"/><text x="{x:.1f}" y="{H - 4}" text-anchor="middle" class="m">{k * step:g}</text>'; k += 1
        for r, (lbl, vals, of, col) in enumerate(data):
            y = top + r * rowH + rowH / 2
            g += f'<text x="{lab - 8}" y="{y + 3}" text-anchor="end">{E(lbl)} ({len(vals)}/{of})</text>'
            if len(vals) >= 3:
                g += (f'<rect x="{X(quantile(vals, .25)):.1f}" y="{y - 8}" width="{max(1.5, X(quantile(vals, .75)) - X(quantile(vals, .25))):.1f}" height="16" rx="2" fill="{col}" opacity=".18"/>'
                      f'<line x1="{X(median(vals)):.1f}" x2="{X(median(vals)):.1f}" y1="{y - 9}" y2="{y + 9}" stroke="{col}" stroke-width="1.6"/>')
            for j, v in enumerate(sorted(vals)):
                g += f'<circle cx="{X(v):.1f}" cy="{y + ((j * 7) % 11) - 5:.1f}" r="1.9" fill="{col}" opacity=".7"/>'
        if tv:
            g += f'<line x1="{X(tv):.1f}" x2="{X(tv):.1f}" y1="{top - 2}" y2="{H - 14}" stroke="#2a78d6" stroke-width="1.6"/><text x="{X(tv):.1f}" y="{top - 5}" text-anchor="{"end" if tv > mx * .85 else "middle"}" class="lt" style="fill:#2a78d6">{E(self.T["name"])} {f1(tv)}</text>'
        return (f'<figure class="chart"><figcaption>{E(title)}</figcaption><svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{g}</svg>'
                f'<div class="leg">One dot per page that has the element · shaded band = middle half (p25–p75) · line = median · blue line = {E(self.T["name"])}'
                + ("" if tv else " (element not present)") + '. The aim is the reference band, not the right edge.</div></figure>')

    def legend(self):
        return '<div class="leg">' + " ".join(f'<span><i class="sw" style="background:{c[1]}"></i>{c[0]} {E(nm(k))}</span>' for k, c in CODE.items() if k != "header") + "</div>"


def auto_narrative(c):
    """Data-driven defaults when the agent did not write a narrative."""
    R = c.res["approach"]["d"]["reference"]["checks"]; pick = lambda *st: [r for r in R if r["status"] in st and r["role"] != "optional"]  # noqa: E731
    out = {"verdict": (f"Blind spots or missing: {', '.join(r['label'] for r in pick('blind', 'missing')) or 'none'}. Below the reference range: {', '.join(r['label'] for r in pick('low')) or 'none'}. "
                       f"In range: {', '.join(r['label'] for r in pick('ok')) or 'none'}. Above range: {', '.join(r['label'] for r in pick('high')) or 'none'}. (Auto-generated summary - add a narrative for a full analysis.)")}
    out["top_actions"] = [f"Bring the {r['label'].lower()} into the reference range: {'none' if r['target'] is None else f1(r['target']) + '%'} today vs {f1(r['p25'])}–{f1(r['p75'])}%." for r in pick("blind", "missing", "low")]
    return out


def tiles(c):
    A = c.res["approach"]
    def tile(v, txt): return f'<div class="tile"><b>{v}</b><span>{txt}</span></div>'
    def pick(dev, *st): return [r["label"] for r in A[dev]["reference"]["checks"] if r["status"] in st and r["role"] != "optional"]
    def rated(dev): return [r for r in A[dev]["reference"]["checks"] if r["role"] != "optional" and r["status"] not in ("na", "absent")]
    bd, bm = pick("d", "blind", "missing"), pick("m", "blind", "missing")
    out = '<div class="tiles">'
    out += tile(SHORT[A["d"]["intended"]], f'Approach validated on desktop, against {len(A["d"]["reference"]["ids"])} pages built the same way. Mobile: {SHORT[A["m"]["intended"]]} ({len(A["m"]["reference"]["ids"])} pages)')
    out += tile(str(len(bd) + len(bm)), "Blind spots or missing elements. Desktop: " + (E(", ".join(bd)) or "none") + ". Mobile: " + (E(", ".join(bm)) or "none"))
    out += tile(f'{len(pick("d", "ok", "high"))} / {len(rated("d"))}', f'Key and supporting elements in or above the reference range on desktop. Mobile: {len(pick("m", "ok", "high"))} / {len(rated("m"))}')
    out += tile(f1(A["d"]["reference"]["distance"]) + "%", f'Of desktop attention sits in a different block than in the reference group (mobile {f1(A["m"]["reference"]["distance"])}%)')
    if c.cmp:
        def n_bad(dev, side): return sum(1 for e in c.cmp["elements"][dev] if e["role"] != "optional" and e["status_" + side] in ("blind", "missing", "low"))
        out += tile(f'{n_bad("d", "old")} → {n_bad("d", "new")}', f'Key and supporting elements that are a blind spot, missing or below range, previous → new version, desktop; mobile {n_bad("m", "old")} → {n_bad("m", "new")} (same reference group for both)')
    return out + "</div>"


def build_change(c):
    C = c.cmp; N = c.N; T = c.T; pid = c.pid; lo, ln = C["labels"]["old"], C["labels"]["new"]
    bl = lambda items: "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>" if items else ""  # noqa: E731
    arrow = lambda a, b, d=1: f"{f1(a)} → {f1(b)}"  # noqa: E731
    H = f'<h2 class="pb">2 · Old vs new: what changed on the page and in predicted attention</h2>'
    ref_txt = " and ".join(f'{c.res["approach_labels"][C["approach"][d]["new_intended"]].lower()} ({DEVICES[d]["label"]})' for d in DEVICES)
    H += (f'<p><b>{E(lo)}</b> (captured {E(C["captured"]["old"])}) against <b>{E(ln)}</b> (captured {E(C["captured"]["new"])}), both scored with the same model and compared with the same {C["benchmark_size"]} benchmark pages. '
          f'Statuses for both versions use <b>the same reference group</b> - top-SaaS pages built the {ref_txt} way - so a change of status is a change of the page, not of the yardstick. '
          'The previous version\'s own status (against the approach it followed then) is shown in the scoreboard as well.</p>')
    if C.get("warnings"):
        H += "<p class=\"small\"><b>Note:</b> " + " ".join(E(w) for w in C["warnings"]) + "</p>"
    if N.get("change_verdict"):
        H += f'<div class="call"><b>What changed.</b> {N["change_verdict"]}</div>'
    for dev in DEVICES:
        ap = C["approach"][dev]
        H += f'<h3>{DEVICES[dev]["label"].capitalize()}: {E(SHORT[ap["old_current"]])} → {E(SHORT[ap["new_current"]])}</h3>'
        w = 335 if dev == "d" else 205
        cell = lambda sid, lbl: (f'<div style="width:{w}px;flex:none"><div class="small" style="height:12pt"><b>{E(lbl)}</b></div>{c.shot(dev, sid, w)}<div class="small">Composite heatmap, 3 s</div>{c.heat1(dev, sid, w)}</div>')  # noqa: E731
        H += f'<div class="row" style="gap:{12 if dev == "d" else 10}pt">{cell(pid, lo)}{cell(T["id"], ln)}</div>'
        A = c.res["approach"][dev]
        rows = [(ln, A["target_spread"], True), (lo, C["spread"][dev]["old"], False), ("Reference: " + SHORT[ap["new_intended"]] + f' (mean of {len(A["reference"]["ids"])})', C["spread"][dev]["reference"], False)]
        dist = C.get("distance", {}).get(dev)
        H += c.spread_chart(dev, rows, f"Attention spread, {DEVICES[dev]['label']}, 3 s: previous vs new version vs the reference group"
                            + (f" - share of attention in a different block than in the reference group: {f1(dist['old'])}% → {f1(dist['new'])}% (0% = same spread)" if dist else ""))
        H += ('<table class="t"><tr><th>Element (CAS 3 s, % of predicted attention)</th><th>Role</th><th>Previous</th><th>New</th><th>Change</th><th>Reference range (p25–p75)</th>'
              '<th>Previous status<br><span class="small">own approach</span></th><th>Previous status<br><span class="small">same reference</span></th><th>New status</th></tr>')
        for e in C["elements"][dev]:
            d = e["delta"]
            dcol = "#1e6b2a" if d is not None and d > 0 else ("#b3261e" if d is not None and d < 0 else "#52514e")
            worse = e["role"] != "optional" and e["status_old"] not in ("blind", "missing", "low") and e["status_new"] in ("blind", "missing", "low")
            better = e["role"] != "optional" and e["status_old"] in ("blind", "missing", "low") and e["status_new"] not in ("blind", "missing", "low")
            cls = " class=bad" if worse else (" class=good" if better else "")
            h_ = lambda v: "none" if v is None else f1(v)  # noqa: E731
            H += (f'<tr{cls}><td>{E(e["label"])}</td><td>{ROLE[e["role"]]}</td><td>{h_(e["old"])}</td><td><b>{h_(e["new"])}</b></td>'
                  f'<td style="color:{dcol}">{("%+.1f" % d) if d is not None else "–"}</td><td>{(f1(e["p25"]) + "–" + f1(e["p75"])) if e["n"] >= 3 else "–"}</td>'
                  f'<td>{c.chip(e["status_old_own"])}</td><td>{c.chip(e["status_old"])}</td><td>{c.chip(e["status_new"])}</td></tr>')
        H += "</table>"
        H += ('<p class="small">Green row = a blind spot, missing or below-range element that is now in or above range; red row = the reverse. '
              'Optional elements are listed for completeness and never coloured.</p>')
        lst = []
        if C["resolved"][dev]: lst.append("<b>Resolved:</b> " + E(", ".join(C["resolved"][dev])).lower().capitalize() + ".")
        if C["still_open"][dev]: lst.append("<b>Still open:</b> " + E(", ".join(C["still_open"][dev])) + ".")
        if C["introduced"][dev]: lst.append("<b>New issues:</b> " + E(", ".join(C["introduced"][dev])) + ".")
        if not (C["resolved"][dev] or C["still_open"][dev] or C["introduced"][dev]): lst.append("No key or supporting element changed status.")
        H += bl(lst)
    if N.get("change_notes"):
        H += "<h3>Reading the change</h3>" + bl(N["change_notes"])
    # content comparison
    H += '<h3>What the page says and shows: previous vs new (desktop; mobile where different)</h3>'
    H += '<table class="t anat"><tr><th style="width:16%">Element</th><th style="width:42%">Previous</th><th style="width:42%">New</th></tr>'
    names = [("eyebrow", "Eyebrow"), ("headline", "Headline"), ("subhead", "Subhead"), ("cta", "CTAs (primary | secondary)"), ("micro", "CTA microcopy"), ("rating", "Rating"),
             ("nav_cta", "Header CTA"), ("trust", "Proof strip"), ("visual", "Hero visual")]
    ao, an = C["anatomy"]["d"]["old"], C["anatomy"]["d"]["new"]; mo, mn = C["anatomy"]["m"]["old"], C["anatomy"]["m"]["new"]
    def hl(a_):
        px = f' <span class="small">({round(a_["headline_px"])} px, {a_.get("headline_words") or "?"} words)</span>' if a_.get("headline_px") else ""
        return E(a_.get("headline") or "none") + px
    cellv = lambda a_, k: hl(a_) if k == "headline" else (E(a_.get(k)) if a_.get(k) else "<i>none</i>")  # noqa: E731
    for k, lbl in names:
        H += f'<tr><td><b>{lbl}</b></td><td>{cellv(ao, k)}</td><td>{cellv(an, k)}</td></tr>'
    diff_m = []
    if mo.get("cta_order") != mn.get("cta_order"): diff_m.append(f'CTA order: {E(mo.get("cta_order") or "–")} → {E(mn.get("cta_order") or "–")}')
    if mo.get("headline_px") != mn.get("headline_px"): diff_m.append(f'headline {round(mo["headline_px"]) if mo.get("headline_px") else "?"} px → {round(mn["headline_px"]) if mn.get("headline_px") else "?"} px')
    if mo.get("visual") != mn.get("visual"): diff_m.append(f'hero visual: {E(mo.get("visual") or "none")} → {E(mn.get("visual") or "none")}')
    if diff_m:
        H += f'<tr><td><b>Mobile</b></td><td colspan="2">{"; ".join(diff_m)}</td></tr>'
    H += "</table>"
    # per-AOI
    for dev in DEVICES:
        H += f'<h3>Every element, {DEVICES[dev]["label"]}: previous → new</h3>'
        H += ('<table class="t"><tr><th>AOI</th><th>Area %</th><th>CAS 3 s</th><th>CAS 6 s</th><th>CAS 10 s</th><th>Speed 3 s</th><th>Reach 3 s</th><th>Hold 3 s</th><th>Attn / area</th></tr>')
        for r in C["aois"][dev]:
            k = r["key"]; col = CODE.get(k, ("", "#000"))
            def cell_(m):
                o, n = (r["old"] or {}).get(m), (r["new"] or {}).get(m)
                if o is None and n is None: return "–"
                d = ("" if o is None or n is None else f' <span style="color:{"#1e6b2a" if n - o > 0.05 else ("#b3261e" if n - o < -0.05 else "#52514e")}">({n - o:+.1f})</span>')
                return f'{"–" if o is None else f1(o)} → <b>{"–" if n is None else f1(n)}</b>{d}'
            H += f'<tr><td><i class="sw" style="background:{col[1]}"></i>{col[0]} {E(nm(k))}</td>' + "".join(f"<td>{cell_(m)}</td>" for m in ("area", "cas_3000", "cas_6000", "cas_10000", "speed_3000", "reach_3000", "hold_3000", "density")) + "</tr>"
        H += "</table>"
    H += f'<p class="small">Links: {E(lo)} - {c.links("d", pid)} (desktop), {c.links("m", pid)} (mobile). {E(ln)} - {c.links("d", T["id"])} (desktop), {c.links("m", T["id"])} (mobile).</p>'
    return H



def build_main(c):
    N = c.N; T = c.T; tid = T["id"]; res = c.res; G = c.G; S = {d: res["stats"][d] for d in DEVICES}
    bl = lambda items: "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>" if items else ""  # noqa: E731  (narrative strings may contain simple HTML)
    H = f'<!doctype html><html><head><meta charset="utf-8"><title>{E(T["name"])}: attention benchmark</title><style>@page{{size:A4;margin:12mm 12mm 13mm}}{CSS}</style></head><body>'
    H += f'<h1>{E(N.get("title") or (T["name"] + " first screen: UI/UX/CRO attention benchmark"))}</h1>'
    grp_desc = ", ".join(f'{len(v)} {E(c.glabel(g))}' for g, v in res["groups"].items() if g not in ("all", "custom"))
    H += (f'<div class="sub">{E(T["name"])} vs {res["benchmark_size"]} benchmark pages ({grp_desc}) · desktop 1440×900 and smartphone 390×844 · every page scored on Composite, '
          f'Speed, Reach and Hold at 3, 6 and 10 s with the RealEye Attention Predictor · target captured {E(T.get("captured"))}; benchmark captured {E(min(p.get("captured", "") for p in c.P.values()))}</div>')
    H += tiles(c)
    H += ('<div class="call"><b>Goal.</b> The aim is not to rank first on every element: attention is a fixed budget, so what one element gains another loses. '
          'The aim is (1) no important element in a blind spot, (2) each element at a level similar to the best pages built the same way, and (3) an attention spread that matches that group. '
          + (N.get("goal") or "") + '</div>')
    H += f'<div class="call"><b>Verdict.</b> {N.get("verdict", "")}</div>'
    if c.cmp and N.get("change_verdict"):
        H += f'<div class="call"><b>Compared with the previous version.</b> {N["change_verdict"]} <span class="small">Details: section 2.</span></div>'
    if N.get("top_actions"):
        H += "<h3>Top actions (details and targets in the guidelines section)</h3><ol>" + "".join(f"<li>{x}</li>" for x in N["top_actions"]) + "</ol>"
    H += ('<p class="small">All values are <b>predicted</b> attention from the RealEye Attention Predictor, not measured eye tracking and not conversion data. '
          '"Share" = the AOI\'s share of the whole screenshot\'s predicted signal (CAS = mean of Speed, Reach and Hold shares).</p>')
    # 1 goal, approach, range check
    H += '<h2 class="pb">1 · Approach and range check: is anything missed, and is attention spread like the best similar pages?</h2>'
    H += ('<p>Pages are built in different ways. Each benchmark page is assigned an approach from how its first screen splits attention between message and hero visual: '
          + "; ".join(f'<b>{E(res["approach_labels"][a])}</b> - {E(res["approach_desc"][a])}' for a in res["approach_labels"]) + '. '
          'The target is validated against the group that follows its approach, not against every page.</p>')
    for dev in DEVICES:
        H += f'<h3>{DEVICES[dev]["label"].capitalize()}</h3><p>{c.approach_line(dev)}</p>' + c.spread_chart(dev) + c.range_table(dev)
    H += ('<p class="small"><b>Status:</b> ' + " ".join(c.chip(s) for s in ("blind", "missing", "low", "ok", "high", "absent")) + ' &nbsp;Blind spot = below nearly all reference pages (under their 10th percentile). '
          'Missing = most reference pages have the element, the target does not. Below / in / above range = against the middle half (p25–p75) of the reference pages. '
          'Above range is not a goal: it is fine for the element the approach puts first, and worth a check when another element is short. '
          'Roles: Key = must not be missed; Supporting = should be in range; Optional = fine to leave out.</p>')
    H += bl(N.get("approach_notes"))
    if c.cmp:
        H += "<!--CHANGE-->"
    # 2 how to read
    H += '<h2>2 · How to read this report and dig into the numbers</h2><table class="t"><tr><th>Term</th><th style="text-align:left">Meaning</th></tr>'
    for a_, b_ in (("Speed share", "Share of the &quot;noticed first&quot; signal in the AOI (initial notice)."), ("Reach share", "Share of the &quot;noticed by many viewers&quot; signal (coverage)."),
                   ("Hold share", "Share of the &quot;attention stays&quot; signal (dwell)."), ("CAS", "Mean of the three shares - the main number. All AOIs plus the background sum to 100%."),
                   ("3 s / 6 s / 10 s", "Cumulative viewing windows: first impression, short look, settled look."),
                   ("Attn / area", "CAS ÷ the AOI's share of the screen. Above 1 = pulls more than its size; separates &quot;too small&quot; from &quot;not attractive&quot;."),
                   ("Reference range", "p25–p75 of the element among the reference pages (same approach). The target of an optimisation is to be inside it."),
                   ("Rank", "Position among pages that have that element; 1 = most attention. Context only: rank 1 is not the goal.")):
        H += f'<tr><td>{a_}</td><td style="text-align:left">{b_}</td></tr>'
    H += "</table>"
    H += (f'<p><b>Evidence.</b> The target\'s AOI reports: {c.links("d", tid)} (desktop) · {c.links("m", tid)} (mobile)'
          + (f' · <a href="{E(T.get("folder_url"))}">folder</a>' if T.get("folder_url") else "") + '. Benchmark pages link to the RealEye workspace where they were scored (login required). '
          'The CSV has one row per page × device × AOI with box, area, CAS/Speed/Reach/Hold at 3/6/10 s and links. The appendix shows every page with heatmaps.</p>')
    # 2 target desktop
    H += f'<h2 class="pb">3 · {E(T["name"])} desktop: what the predictor sees</h2>'
    H += f'<div class="row"><div>{c.shot("d", tid, 360)}<div class="small">AOIs with CAS at 3 s. {c.links("d", tid)}</div></div><div class="col">{c.heat("d", tid, 330)}<div class="small">Heatmaps: rows Composite, Speed, Reach, Hold; columns 3, 6, 10 s.</div></div></div>'
    H += c.legend() + c.aoi_table("d", tid) + bl(N.get("target_notes"))
    # 3 benchmark
    keys = ["_message", "headline", "eyebrow", "subhead", "_action", "cta_primary", "cta_secondary", "form", "micro", "visual", "trust", "nav_cta", "header", "announce"]
    H += f'<h2 class="pb">4 · Context: element by element vs all {res["benchmark_size"]} pages (desktop)</h2>' + c.rank_table("d", keys)
    H += '<p class="small">Ranks are context, not the goal: no page leads on every element. Red = blind spot or missing in the range check (section 1). "none" = the target has no such element. Group sizes vary: not every page has every element.</p>'
    H += bl(N.get("benchmark_notes"))
    for k in ("headline", "cta_primary", "visual"):
        p = c.profile("d", k)
        if p: H += f"<h3>{E(nm(k))} across all components and time windows</h3>" + p
    H += c.bars("d", lambda x: (x["aois"].get("headline") or {}).get("cas_3000"), "Headline share, desktop, composite 3 s")
    H += c.bars("d", lambda x: x.get("message_cas"), "Message block share (eyebrow + headline + subhead), desktop 3 s")
    H += c.bars("d", lambda x: x.get("action_cas"), "Action block share (hero CTAs + sign-up form), desktop 3 s")
    H += c.bars("d", lambda x: (x["aois"].get("visual") or {}).get("cas_3000"), "Hero visual share, desktop 3 s")
    # 4 anatomy
    H += '<h2 class="pb">5 · Hero anatomy: what the reference pages put in the first screen (desktop)</h2><p>The target and its reference pages (same approach). Texts read from the live pages. H1 / CTA / Visual % = composite share at 3 s. All benchmark pages are in the CSV and the appendix.</p>'
    H += '<table class="t anat" style="font-size:7pt"><tr><th>Page</th><th>Approach</th><th>Headline (H1) and subhead</th><th>px</th><th>CTAs (primary | secondary) and microcopy</th><th>Visual</th><th class="n">H1 %</th><th class="n">CTA %</th><th class="n">Vis %</th></tr>'
    show = set([tid] + res["approach"]["d"]["reference"]["ids"] + (res["groups"].get(G, []) if G else []))
    for sid, s in sorted(((k_, v_) for k_, v_ in c.all.items() if k_ in show), key=lambda kv: (ORDER.get(kv[1]["group"], 9), -((kv[1]["d"]["aois"].get("headline") or {}).get("cas_3000") or -1))):
        i = s["d"]["info"]; hd = i.get("headline") or {}; sh = (i.get("subhead") or {}).get("t")
        vis = (i.get("visual") or {}).get("kind") or (i.get("visual") or {}).get("tags") if "visual" in s["d"]["aois"] else (i.get("visual_note") or ("background " + i["bg_media"] if i.get("bg_media") else "none"))
        H += (f'<tr{" class=me" if s is T else ""}><td><b>{E(s["name"])}</b><br><span class="small">{E(c.glabel(s["group"]))}</span></td><td>{SHORT[c.approach_of(sid, "d")]}</td>'
              f'<td>{E(hd.get("t") or "(no headline)")}<br><span class="small">{E((sh or "(no subhead)")[:120])}</span></td><td class="n">{round(hd["f"]) if hd.get("f") else "–"}</td>'
              f'<td>{E((i.get("cta_primary") or {}).get("t") or "(no CTA)")}{(" | " + E(i["cta_secondary"]["t"])) if i.get("cta_secondary") else ""}{("<br><span class=small>" + E(i["micro"][:70]) + "</span>") if i.get("micro") else ""}</td>'
              f'<td>{E(vis)}</td><td class="n">{f1((s["d"]["aois"].get("headline") or {}).get("cas_3000"))}</td><td class="n">{f1(s["d"].get("action_cas"))}</td><td class="n">{f1((s["d"]["aois"].get("visual") or {}).get("cas_3000"))}</td></tr>')
    H += "</table>"
    pv = S["d"]["prevalence"]; n = S["d"]["n_peers"]
    pv = {k_: sum(1 for i_ in res["groups"].get("saas", []) if k_ in c.P[i_]["d"]["aois"]) for k_ in pv} | {"two_ctas": sum(1 for i_ in res["groups"].get("saas", []) if "cta_secondary" in c.P[i_]["d"]["aois"])}
    n = len(res["groups"].get("saas", [])) or n
    auto_pat = [f'Headline box area vs headline share: r = {f2(S["d"]["r_area_headline"])} across {S["d"]["n_headline"]} pages (font size r = {f2(S["d"]["r_font_headline"])}). Peer medians: {f1(S["d"]["headline_font_median"])} px, {S["d"]["headline_words_median"]} words, {f1(S["d"]["headline_area_median"])}% of the screen.',
                f'Standard hero kit among top-SaaS pages: subhead {pv["subhead"]}/{n}, two CTAs {pv["two_ctas"]}/{n}, CTA microcopy {pv["micro"]}/{n}, hero visual {pv["visual"]}/{n}, logo/proof strip {pv["trust"]}/{n}, nav CTA {pv["nav_cta"]}/{n}.']
    H += "<h3>Patterns in the data</h3>" + bl(N.get("patterns") or auto_pat)
    # 5 competitors gallery
    comp_ids = ([i for i in res["groups"].get(G, [])] if G else sorted(res["approach"]["d"]["reference"]["ids"], key=lambda i_: -(c.P[i_]["d"].get("message_cas") or 0) - (c.P[i_]["d"].get("action_cas") or 0)))[:11]
    H += f'<h2 class="pb">6 · {E(c.glabel(G)) if G else "Reference pages (same approach)"} at a glance (desktop)</h2><div class="gal">'
    for sid in [tid] + comp_ids:
        s = c.all[sid]; a = s["d"]["aois"]
        H += (f'<div class="c">{c.shot("d", sid, 222, vals=False)}<b>{E(s["name"])}</b> · {SHORT[c.approach_of(sid, "d")]} · H1 {f1((a.get("headline") or {}).get("cas_3000"))}% · CTA {f1(s["d"].get("action_cas"))}% · Visual {f1((a.get("visual") or {}).get("cas_3000"))}%'
              f'<br>{E((s["d"]["info"].get("headline") or {}).get("t") or "(no headline)")}<br><span class="small">{c.links("d", sid)}</span></div>')
    H += "</div>" + (f'<p><b>Takeaways.</b> {N["competitor_takeaways"]}</p>' if N.get("competitor_takeaways") else "")
    # 6 mobile
    H += '<h2 class="pb">7 · Smartphone (390×844)</h2>'
    H += f'<div class="row"><div>{c.shot("m", tid, 190)}</div><div class="col">{c.heat("m", tid, 500)}<div class="small">Mobile heatmaps: Composite, Speed (top), Reach, Hold (bottom); 3, 6, 10 s each. {c.links("m", tid)}</div>{c.aoi_table("m", tid, True)}</div></div>'
    H += c.rank_table("m", ["_message", "headline", "eyebrow", "subhead", "_action", "cta_primary", "cta_secondary", "visual", "trust", "nav_cta", "header"]) + bl(N.get("mobile_notes"))
    H += c.profile("m", "headline")
    H += c.bars("m", lambda x: (x["aois"].get("headline") or {}).get("cas_3000"), "Headline share, mobile 3 s")
    H += c.bars("m", lambda x: x.get("action_cas"), "Action block share, mobile 3 s")
    # 7 guidelines
    if N.get("guidelines"):
        H += (f'<h2 class="pb">8 · Guidelines: how to improve {E(T["name"])}</h2><p>Ordered by expected impact: blind spots and missing elements first, then elements below the reference range. Targets are the reference range of pages built the same way, not "rank 1"; '
              'lifting one element takes attention from another, so each guideline says where it should come from. Check targets in the Attention Predictor before shipping; conversion impact must be confirmed with a live A/B test.</p>')
        for g_ in N["guidelines"]:
            pts = g_.get("points", [])
            if g_.get("target"): pts = pts + [f'<b>Target:</b> {g_["target"]}']
            H += f'<div class="gl"><h3>{E(g_.get("title"))}<span class="tag">{E(g_.get("tag", ""))}</span></h3>{bl(pts)}<div class="ev">Evidence: {g_.get("evidence", "")}</div></div>'
    if N.get("scorecard"):
        H += '<h3>Target scorecard</h3><table class="t"><tr><th>Metric (CAS 3 s)</th><th>Today desktop</th><th>Target desktop (reference range)</th><th>Today mobile</th><th>Target mobile (reference range)</th></tr>'
        for r in N["scorecard"]:
            H += f'<tr><td>{E(r.get("metric"))}</td><td>{E(r.get("today_d"))}</td><td><b>{E(r.get("target_d"))}</b></td><td>{E(r.get("today_m"))}</td><td><b>{E(r.get("target_m"))}</b></td></tr>'
        H += "</table>"
    # 8 method
    H += ('<h2>9 · Method and limits</h2><ul><li><b>Capture:</b> headless Chromium, desktop 1440×900 and mobile 390×844 (iPhone UA, touch), one capture per page; cookie banners declined or hidden, chat widgets hidden, videos paused. Pages change; results describe the capture date.</li>'
          '<li><b>AOIs:</b> detected from the live DOM (headline text lines, buttons, media, logo rows) and reviewed/corrected on an overlay image before scoring. Boxes are approximate.</li>'
          '<li><b>Scores:</b> AOIs created in the Attention Predictor; AOI report shares (Speed, Reach, Hold, CAS) at 3, 6, 10 s. Ranks/medians per group over pages that have the element.</li>'
          '<li><b>Approach and reference group:</b> each capture is classed from its message : hero-visual attention at 3 s (message-led ≥ 2 : 1, visual-led ≤ 1 : 2, otherwise balanced). The reference group = top-SaaS benchmark pages with the intended approach '
          '(all benchmark pages when fewer than five match, or hand-picked pages). Range check: p25–p75 of the reference pages that have the element; blind spot = under their 10th percentile. Groups are small (see "Pages"), so ranges are indicative.</li>'
          f'<li><b>Benchmark:</b> {res["benchmark_size"]} pages captured {E(min(p.get("captured", "") for p in c.P.values()))}, bundled with the skill; they may have changed since. "Top SaaS" = the biggest / best-known SaaS companies, not proven best converters; "Average" = mid-size, lesser-known SaaS sampled without regard to design; '
          '"Poorly made" = pages that failed written first-screen criteria in a manual audit. Only top-SaaS pages are used as the yardstick; average and poorly made pages are context.</li>'
          '<li><b>Limits:</b> predictions, not measured gaze or clicks; mobile predictions are less validated than desktop; correlations describe this sample, not causation.</li>'
          + "".join(f"<li>{x}</li>" for x in N.get("limits", [])) + "</ul></body></html>")
    if c.cmp:  # the old-vs-new section becomes section 2; later sections move down by one
        import re
        H = re.sub(r"(<h2[^>]*>)(\d+) · ", lambda m: m.group(1) + (str(int(m.group(2)) + 1) if int(m.group(2)) >= 2 else m.group(2)) + " · ", H)
        H = H.replace("<!--CHANGE-->", build_change(c))
    return H


def build_appendix(c, scope):
    T = c.T
    keep = set(c.res["approach"]["d"]["reference"]["ids"]) | set(c.res["approach"]["m"]["reference"]["ids"]) | set(c.res["groups"].get(c.G, []) if c.G else [])
    ids = [T["id"]] + ([c.pid] if c.pid else []) + [sid for sid, s in sorted(c.P.items(), key=lambda kv: (ORDER.get(kv[1]["group"], 9), kv[1]["name"])) if scope == "all" or (scope == "reference" and sid in keep)]
    H = (f'<!doctype html><html><head><meta charset="utf-8"><title>{E(T["name"])} benchmark appendix</title><style>@page{{size:A4 landscape;margin:9mm 10mm}}{CSS}'
         '.pg{break-after:page} .pg:last-child{break-after:auto} .pg table.t{font-size:7.2pt} .pg .t th,.pg .t td{padding:1.2pt 3pt} h2{margin-top:0}</style></head><body>')
    H += f'<div class="pg"><h1>Appendix: {"every benchmark page" if scope == "all" else ("the target and its reference pages" if scope == "reference" else "the target")}, desktop and mobile</h1><div class="sub">{len(ids) * 2} captures. Each: screenshot with AOIs and CAS at 3 s, the heatmap grid (Composite, Speed, Reach, Hold × 3, 6, 10 s), the AOI table, hero texts and app links.</div>{c.legend()}'
    H += '<table class="t"><tr><th>#</th><th>Site</th><th>Group</th><th>Desktop links</th><th>Mobile links</th></tr>'
    for n, sid in enumerate(ids, 1):
        s = c.all[sid]; H += f'<tr><td>{n}</td><td>{E(s["name"])}</td><td>{E(c.glabel(s["group"]))}</td><td>{c.links("d", sid)}</td><td>{" · ".join(c.links("m", sid).split(" · ")[:2])}</td></tr>'
    H += "</table></div>"

    def texts(i):
        L = []
        if i.get("eyebrow"): L.append("<b>Eyebrow:</b> " + E(i["eyebrow"]))
        hd = i.get("headline") or {}
        L.append("<b>Headline:</b> " + (E(f'{hd.get("t")} ({round(hd["f"]) if hd.get("f") else "?"} px, {hd.get("words")} words)') if hd else "none"))
        if (i.get("subhead") or {}).get("t"): L.append("<b>Subhead:</b> " + E(i["subhead"]["t"]))
        L.append("<b>CTAs:</b> " + E((i.get("cta_primary") or {}).get("t") or "none") + ((" | " + E(i["cta_secondary"]["t"])) if i.get("cta_secondary") else "") + ((" · order: " + E(i["cta_order"])) if i.get("cta_order") else ""))
        for k, lbl in (("micro", "Microcopy"), ("announce", "Announcement"), ("visual_note", "Note")):
            if i.get(k): L.append(f"<b>{lbl}:</b> " + E(i[k]))
        if i.get("nav_cta"): L.append("<b>Nav CTA:</b> " + E(i["nav_cta"].get("all") or i["nav_cta"].get("t")))
        return '<div class="small" style="color:#0b0b0b">' + "<br>".join(L) + "</div>"
    for n, sid in enumerate(ids, 1):
        s = c.all[sid]
        for dev in DEVICES:
            x = s[dev]
            H += (f'<div class="pg"><h2>{dev.upper()}{n} · {E(s["name"])} · {DEVICES[dev]["label"]} <span class="tag">{E(c.glabel(s["group"]))}</span><span class="tag">{SHORT[c.approach_of(sid, dev)]}</span></h2>'
                  f'<div class="small">{c.links(dev, sid)} · headline {f1((x["aois"].get("headline") or {}).get("cas_3000"))}% · message {f1(x.get("message_cas"))}% · action {f1(x.get("action_cas"))}% · visual {f1((x["aois"].get("visual") or {}).get("cas_3000"))}%</div>')
            if dev == "d":
                H += f'<div class="row"><div style="width:470px;flex:none">{c.shot("d", sid, 470)}{texts(x["info"])}</div><div class="col">{c.heat("d", sid, 470)}{c.aoi_table("d", sid, True)}</div></div></div>'
            else:
                H += f'<div class="row"><div style="width:215px;flex:none">{c.shot("m", sid, 215)}</div><div class="col">{c.heat("m", sid, 560)}{c.aoi_table("m", sid, True)}{texts(x["info"])}</div></div></div>'
    return H + "</body></html>"


def write_csv(c, path):
    cols = ["device", "site", "name", "group", "approach", "aoi", "x1", "y1", "x2", "y2", "area_pct", "coverage_pct"] + [f"{m}_share_{t}ms" for t in TR for m in COMP] + ["attn_per_area", "aoi_report_url", "heatmap_analyser_url"]
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh); w.writerow(cols)
        for sid, s in c.all.items():
            for dev in DEVICES:
                for k, a in s[dev]["aois"].items():
                    b = a.get("box") or ["", "", "", ""]
                    w.writerow([DEVICES[dev]["label"], sid, s["name"], s["group"], c.approach_of(sid, dev), k, *b, a.get("area"), a.get("cov")] + [a.get(f"{m}_{t}") for t in TR for m in COMP]
                               + [a.get("density"), s[dev].get("report_url"), s[dev].get("analyser_url")])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("--narrative"); ap.add_argument("--out"); ap.add_argument("--appendix", default="reference", choices=["reference", "all", "target"])
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args(); work = Path(a.work)
    res = load(work / "analysis.json")
    if not res:
        raise SystemExit("run analyze.py first")
    narrative = load(a.narrative or work / "narrative.json")
    cmp_ = load(work / "comparison.json")
    if cmp_:
        res["_comparison"] = cmp_
    c = Ctx(res, None)
    if not narrative:
        print("no narrative.json - using data-driven defaults (write one for the full analysis; see templates/narrative.example.json)")
        import narrate  # full data-driven narrative (same as scripts/narrate.py)
        narrative = narrate.build(res, reviewed=(work / "overrides.json").exists(), cmp=cmp_)
    c.N = narrative
    final = Path(a.out or work / "report"); final.mkdir(parents=True, exist_ok=True)
    import shutil, tempfile
    out = Path(tempfile.mkdtemp(prefix="ap-report-"))  # build in a short path: deep folders hit the Windows 260-character limit
    import tempfile
    IMG_CACHE["dir"] = Path(tempfile.gettempdir()) / "ap-img-cache"; IMG_CACHE["dir"].mkdir(exist_ok=True)
    base = f'{c.T["id"]}-attention-benchmark-{time.strftime("%Y-%m-%d")}'
    (out / f"{base}.html").write_text(build_main(c), encoding="utf-8")
    (out / f"{base}-appendix.html").write_text(build_appendix(c, a.appendix), encoding="utf-8")
    write_csv(c, out / f"{base}-aoi-scores.csv")
    if not a.no_pdf:
        ok1 = html_to_pdf(out / f"{base}.html", out / f"{base}.pdf")
        ok2 = html_to_pdf(out / f"{base}-appendix.html", out / f"{base}-appendix.pdf", landscape=True)
        print("PDF:", "ok" if ok1 and ok2 else "failed (HTML files are complete; print them to PDF)")
    long = lambda p: ("\\\\?\\" + str(p.resolve())) if sys.platform == "win32" else str(p)  # noqa: E731  (extended-length path)
    for f in sorted(out.glob(base + "*")):
        shutil.copyfile(f, long(final / f.name))
        print(f"{final / f.name}  {f.stat().st_size / 1e6:.1f} MB")
    print(f"(built in {out}; preview the HTML files there if the report folder path is very long)")


if __name__ == "__main__":
    main()


