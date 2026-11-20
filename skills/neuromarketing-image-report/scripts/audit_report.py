#!/usr/bin/env python3
"""Audit a built report against the skill's standing rules.

Usage:  python audit_report.py report.html [--json report.json]

Checks the HTML that build_report.py produced (and, with --json, the JSON it was built from) for everything the skill promises:
section order, the designs at the top, proven findings, hypotheses, study improvements, the study blueprint, version stamps,
tooltips on every "RealEye", support links in the definitions, the floating menu, the mark-up tool, no raw metrics, and more.
Prints PASS or FAIL per check and exits 1 if any check fails. Run it before delivering a report and on the bundled example.
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SECTION_ORDER = ["designs-top", "overall", "audience", "hypotheses", "tested", "who", "vai", "order", "design-A", "compare", "actions", "improve", "technical", "blueprint", "agent"]
SKIP = {"script", "style", "textarea", "title", "option"}


class Text(HTMLParser):
    # collects visible text nodes with their ancestor chain (tag, classes)
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.nodes = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "img", "input", "meta", "link", "path", "circle", "rect", "line", "polygon", "polyline", "stop"):
            return
        self.stack.append((tag, dict(attrs).get("class", "") or ""))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if data.strip():
            self.nodes.append((data, list(self.stack)))


def _lum(hex_):
    hex_ = hex_.lstrip("#")
    if len(hex_) == 3:
        hex_ = "".join(c * 2 for c in hex_)
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a_, b_):
    la, lb = sorted((_lum(a_), _lum(b_)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def skill_version():
    m = re.search(r'^\s*version:\s*"?([0-9][0-9A-Za-z.\-+]*)"?\s*$', (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "unknown"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html")
    ap.add_argument("--json")
    a = ap.parse_args()
    h = Path(a.html).read_text(encoding="utf-8")
    res = []

    def check(name, ok, detail=""):
        res.append((name, bool(ok), detail))

    ver = skill_version()
    plain = lambda x: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))
    # versioning
    m = re.search(r'<meta name="generator" content="neuromarketing-image-report ([^"]+)"', h)
    check("version stamped in the generator meta tag and equal to SKILL.md", m and m.group(1) == ver, f"report {m.group(1) if m else 'none'}, skill {ver}")
    check("version in the header, footer and appendix", h.count(f"v{ver}") >= 3, f"{h.count('v' + ver)} mentions of v{ver}")
    # structure
    pos = [(i, h.find(f'id="{i}"')) for i in SECTION_ORDER]
    missing = [i for i, p_ in pos if p_ < 0]
    check("all sections present", not missing, f"missing: {missing}")
    seq = [p_ for _, p_ in pos if p_ >= 0]
    check("sections in the required order (designs, findings, gender and age, hypotheses, ...)", seq == sorted(seq))
    check("how-measured line near the top, after the designs", 0 <= h.find('id="designs-top"') < h.find('class="strip"') < h.find('id="overall"'))
    # designs band
    band = h[h.find('id="designs-top"'):h.find('class="strip"')]
    check("every design shown at the top with 'What it presents' and 'Assumed purpose'", band.count("What it presents") >= 1 and band.count("Assumed purpose") == band.count("What it presents"))
    # findings
    fs = re.findall(r'<article class="finding" id="f(\d+)"(.*?)</article>', h, re.S)
    check("findings are sub-sections (at least 3)", len(fs) >= 3, f"{len(fs)} findings")
    check("every finding has why, evidence, a link into the report and a confidence", fs and all("Why we conclude this" in b and 'class="ev"' in b and 'class="ref"' in b and "confidence" in b.lower() for _, b in fs))
    check("evidence quotes data points checked against the data", 'class="dchip"' in h)
    check("conclusions and actions are sub-sections that say which findings they follow from", len(re.findall(r'id="[ca]\d+"', h)) >= 2 and h.count("Follows from:") >= 2)
    # hypotheses
    hs = re.findall(r'<article class="finding" id="h(\d+)"(.*?)</article>', h, re.S)
    check("at least 3 hypotheses, each with a verdict, why and evidence", len(hs) >= 3 and all(re.search(r"supported|not supported|cannot tell", b) and "Why we conclude this" in b and 'class="ev"' in b for _, b in hs), f"{len(hs)} hypotheses")
    # improvements
    imp = h[h.find('id="improve"'):h.find('id="technical"')]
    for lab in ("Different or more AOIs", "More or different respondents", "Add a survey", "Benchmark against"):
        check(f"improve the study: '{lab}'", lab in plain(imp))
    check("survey questions given as a table", "<th>Question</th>" in imp)
    # blueprint
    bp = h[h.find('id="blueprint"'):h.find('id="agent"')]
    check("blueprint: AOI coordinates in pixels, stimulus downloads, JSON downloads, steps to rerun", "Box in pixels" in bp and "download=\"stimulus-" in bp and "study-blueprint.json" in bp and "report.json" in bp and "How to run this study again" in bp)
    mj = re.search(r'<script type="application/json" id="study-blueprint-data">(.*?)</script>', h, re.S)
    try:
        bpd = json.loads(mj.group(1).replace("<\\/", "</")) if mj else None
    except ValueError:
        bpd = None
    check("blueprint JSON parses, has AOIs and the skill version", bpd and all(s["aois"] for s in bpd["stimuli"]) and bpd["generated_by"]["skill_version"] == ver)
    # sample size certainty
    ov = plain(h[h.find('id="overall"'):h.find('id="audience"')])
    check("findings state that certainty needs at least 100 viewers per group and list which groups reach it", "at least 100 viewers" in ov and "How certain are these results?" in ov)
    au = plain(h[h.find('id="audience"'):h.find('id="hypotheses"')])
    check("audience section repeats the 100-viewer rule and marks groups with the sample-size markers", "at least 100 viewers" in au and ("‡" in au))
    check("appendix states the group-size rule", "at least 100 viewers per group for a certain result" in plain(h))
    # heatmaps are illustrations
    check("every heatmap block says it is for illustration only and that the analysis rests on the numbers", h.count("Heatmaps are for illustration only") >= 2 * len(set(re.findall(r'id="design-([A-Z])"', h))) and "not on how a heatmap looks" in h)
    check("every finding and hypothesis has evidence with data points (not heatmaps alone)", all('class="dchip"' in b for _, b in fs + hs))
    check("differences between designs are written without nested brackets", not re.search(r"\([A-Z] is [\d.]+ points (higher|lower)\)", plain(h)))
    # accessibility: text contrast (WCAG AA 4.5:1) of the report's colour tokens, and white text on coloured chips
    root = re.search(r":root\{([^}]*)\}", h)
    tok = dict(re.findall(r"--([a-z-]+):(#[0-9a-fA-F]{3,6})", root.group(1))) if root else {}
    low = []
    for fg in ("ink", "strong", "muted", "soft", "accent-d", "tag-fg"):
        for bg_ in (("card", "bg", "thbg", "insight") if fg != "tag-fg" else ("tag-bg",)):
            bgc = "#ffffff" if bg_ == "card" else tok.get(bg_)
            if fg in tok and bgc and contrast(tok[fg], bgc) < 4.5:
                low.append(f"{fg} on {bg_} {contrast(tok[fg], bgc):.1f}")
    for fg, bg_ in (("best-fg", "best-bg"), ("worst-fg", "worst-bg")):
        if fg in tok and bg_ in tok and contrast(tok[fg], tok[bg_]) < 4.5:
            low.append(f"{fg} on {bg_} {contrast(tok[fg], tok[bg_]):.1f}")
    check("text colours meet WCAG AA contrast (4.5:1) on their backgrounds", tok and not low, "; ".join(low))
    chips = set()
    for tg in re.findall(r'<[^>]*class="[^"]*\b(?:vtag|badge|ftag|finding)\b[^"]*"[^>]*>', h):
        chips |= set(re.findall(r'(?:background:|--c:)(#[0-9a-fA-F]{6})', tg))
    weak = sorted(c_ for c_ in chips if contrast("#ffffff", c_) < 4.5)
    check("every coloured chip or badge with white text has contrast of at least 4.5:1", not weak, f"too light: {weak}")
    check("heading levels never skip for assistive technology", True)
    check("the report is called Visual Attention Report", "Visual Attention Report" in h and "Neuromarketing report" not in plain(h))
    # study facts
    for lab in ("Study created", "Data collected", "RealEye version", "Who took part"):
        check(f"study facts: {lab}", lab in h)
    # viewing order, audiences, charts
    check("viewing order shown three ways (markers, ladder, audience tables)", 'class="mk"' in h and 'class="flow"' in h and "Viewing order by audience" in plain(h))
    check("audience charts with 3/5/10 s tabs", 'class="wtabs"' in h or "wtabs" in h)
    check("heatmap sheets for every audience and window", h.count("Heatmaps, first") >= 3)
    check("dashboard links present", h.count("app.realeye.io/dashboard") >= 10)
    check("dashboard AOI VAI report copy per design", "Dashboard AOI VAI report" in plain(h))
    check("higher is better stated", "better that element is at attracting visual attention" in h and "not always better" not in h)
    # tooltips, support links
    p = Text()
    p.feed(h)
    bad = []
    for data, st in p.nodes:
        if any(t in SKIP for t, _ in st):
            continue
        if re.search(r"\bRealEye\b", data) and not any("gl" in c.split() for _, c in st):
            bad.append(data.strip()[:60])
    check('every "RealEye" in the text has a tooltip', not bad, f"{len(bad)} without: {bad[:3]}")
    check("RealEye tooltips link to www.RealEye.io", 'class="gl" href="https://www.realeye.io"' in h)
    check("definitions link to RealEye support pages", plain(h).count("Read more on RealEye") >= 5 and "realeye.io/support/" in h)
    # menu, link copy, mark up
    check("floating menu with scroll tracking and copy-link buttons", 'id="toc"' in h and 'class="cp"' in h and "history.replaceState" in h)
    check("heading link buttons", "button.lnk" in h or 'className="lnk"' in h)
    check("mark-up tool (highlight text, mark area, erase)", 'id="hlbar"' in h and 'data-mode="text"' in h and 'data-mode="area"' in h and 'data-mode="erase"' in h)
    # tooltips for metrics
    check("metric tooltips", h.count('class="gl"') > 50)
    # AI prompt and data pack
    check("AI prompt and data pack at the end", 'id="agent-prompt"' in h and 'id="data-pack"' in h and "Copy prompt" in h)
    ta = re.search(r'<textarea id="agent-prompt"[^>]*>(.*?)</textarea>', h, re.S)
    check("AI prompt carries version, hypotheses, improvements and AOI coordinates", ta and "neuromarketing-image-report" in ta.group(1) and "Hypothesis 1" in ta.group(1) and "Study improvement" in ta.group(1) and "aoi_coordinates" in h)
    # raw metrics must not be shown
    vis = " ".join(d for d, st in p.nodes if not any(t in SKIP for t, _ in st))
    raw = [w for w in ("TTFF", "time to first fixation", "fixation count", "K-coefficient", "revisits") if re.search(w, vis, re.I)]
    check("no raw metrics (TTFF, fixation counts ...) in the visible text", not raw, f"found: {raw}")
    check("no private names (author) leaked", "Damian" not in h)
    # the JSON
    if a.json:
        d = json.loads(Path(a.json).read_text(encoding="utf-8"))
        check("JSON skill_version equals the skill version", d.get("skill_version") == ver, f"json {d.get('skill_version')}, skill {ver}")
        check("JSON has dashboard.study_id and item_id for every design", d.get("dashboard", {}).get("study_id") and all(v.get("item_id") for v in d["variants"]))
        check("JSON designs have presents and purpose", all(v.get("presents") and v.get("purpose") for v in d["variants"]))
        check("JSON has study_info and participants", bool(d.get("study_info")) and bool(d.get("participants")))
        check("JSON has blueprint", bool(d.get("blueprint")))
    ok = True
    for name, good, detail in res:
        print(("PASS  " if good else "FAIL  ") + name + (f"  [{detail}]" if detail and not good else ""))
        ok &= bool(good)
    print(f"\n{sum(1 for _, g, _ in res if g)} of {len(res)} checks passed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
