#!/usr/bin/env python3
"""Write a complete, data-driven narrative.json from analysis.json - no language model needed.

  python scripts/narrate.py ap-work/example [--force]

Every sentence is generated from the range check (approach, reference ranges, statuses, attention per area, 3->10 s trends),
so any agent - or none - can produce a full report. A capable agent should still read facts.md and rewrite the verdict,
copy directions and guidelines in its own words (see references/writing-guide.md); this file is the safe baseline.
Without --force an existing narrative.json is kept.
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import DEVICES, f1, load, save  # noqa: E402

LEAD = {"message": ("_message", "headline"), "balanced": ("_message", "headline", "visual"), "visual": ("visual",)}
ORDER = ["blind", "missing", "low"]
SHORT = {"message": "message-led", "balanced": "balanced", "visual": "visual-led"}
DEV = {"d": "desktop", "m": "mobile"}


def lab(r):
    s = r["label"]; return s if s[:2].isupper() else s[0].lower() + s[1:]


def rng(r):
    return f"{f1(r['p25'])}–{f1(r['p75'])}%" if r.get("p25") is not None and r["n"] >= 3 else "–"


def val(r):
    return "none" if r["target"] is None else f"{f1(r['target'])}%"


def metric(res, dev, k, m):
    x = res["metrics"][dev].get(k, {}).get(m) or {}
    return x.get("target"), (x.get("saas") or {}).get("med")


class Ctx:
    def __init__(self, res):
        self.res, self.T = res, res["target"]
        self.A = {d: res["approach"][d] for d in DEVICES}
        self.R = {d: self.A[d]["reference"] for d in DEVICES}
        self.rows = {d: {r["key"]: r for r in self.R[d]["checks"]} for d in DEVICES}

    def issues(self, dev):
        out = [r for r in self.R[dev]["checks"] if r["status"] in ORDER and r["role"] != "optional"]
        return sorted(out, key=lambda r: (ORDER.index(r["status"]), {"key": 0, "support": 1}.get(r["role"], 2)))

    def by_design(self, dev, r):
        return r["key"] in LEAD[self.A[dev]["intended"]]

    def donors(self, dev):
        """Elements above range that are not what the approach puts first, plus unassigned background - where attention can come from."""
        d = []
        for r in self.R[dev]["checks"]:
            if r["status"] == "high" and r["target"] is not None and r.get("p75") is not None and not r["key"].startswith("_"):
                if r["key"] in ("cta_primary", "cta_secondary", "nav_cta", "micro") and not (r.get("max") is not None and r["target"] > r["max"]):
                    continue
                d.append((r["target"] - r["p75"], r))
        d.sort(key=lambda x: -x[0])
        names = [f"{lab(r)} ({val(r)}, range {rng(r)})" for _, r in d[:3]]
        oth, ref_oth = self.A[dev]["target_spread"]["other"], (self.R[dev]["spread"] or {}).get("other")
        if ref_oth is not None and oth > ref_oth + 3:
            names.append(f"unassigned background ({f1(oth)}% vs {f1(ref_oth)}% on reference pages)")
        return names

    def diag(self, dev, k):
        """'too small' vs 'unattractive' vs 'fading' for one AOI."""
        dens, dmed = metric(self.res, dev, k, "density")
        area, amed = metric(self.res, dev, k, "area")
        tr, trmed = metric(self.res, dev, k, "trend")
        bits = []
        if area is not None and amed and area < amed * .7:
            bits.append(f"too small: it covers {f1(area)}% of the screen against a top-SaaS median of {f1(amed)}%")
        if dens is not None and dmed and dens < dmed * .8:
            bits.append(f"unattractive for its size: attention per area {f1(dens)} against a median of {f1(dmed)} (contrast, weight, colour or position)")
        if not bits and dens is not None and dmed:
            bits.append(f"size and attractiveness are near normal (area {f1(area)}%, attention per area {f1(dens)} vs median {f1(dmed)})")
        if tr is not None and trmed is not None and tr < trmed - 1:
            bits.append(f"it {'loses attention' if tr < 0 else 'gains less attention than usual'} over time ({f1(tr)} pts from 3 s to 10 s vs a median of {f1(trmed)})")
        return "; ".join(bits)


def spec(c, dev, r):
    """Concrete, element-specific points for one problem element."""
    k = r["key"]; info = c.T[dev]["info"]; S = c.res["stats"][dev]
    h = info.get("headline") or {}; fmed = S.get("headline_font_median")
    if k in ("headline", "_message"):
        pts = []
        if h.get("f") and fmed and h["f"] < fmed * .85:
            pts.append(f"Set the headline larger: {round(h['f'])} px today against a peer median of {round(fmed)} px; aim for {round(fmed)}–{round(fmed * 1.15)} px, 2–3 lines, one size and weight for the whole sentence.")
        else:
            pts.append("Give the headline more room and weight: one size for the whole sentence, 2–3 lines, highest contrast on the page.")
        if "subhead" not in c.T[dev]["aois"]:
            pts.append("Add a one- or two-line subhead directly under it (15–25 words): what the product does, for whom, and the main proof.")
        pts.append("Copy: lead with the outcome for the visitor, keep the category words people search for, avoid internal jargon.")
        return pts
    if k == "subhead":
        return ["Add one or two lines (15–25 words, 18–20 px on desktop) directly under the headline: what it does, for whom, the main proof.",
                "Keep links and video prompts out of the subhead position; put them next to the CTAs."]
    if k in ("cta_primary", "_action"):
        cp = info.get("cta_primary") or {}
        size_now = " (today %sx%s px)" % (cp.get("w"), cp.get("h")) if cp.get("w") else ""
        label_now = ' (today "%s")' % cp["t"] if cp.get("t") else ""
        pts = ["Primary button: filled, the highest-contrast element in the hero, about 48–56 px tall on desktop" + size_now + ".",
               'Label: a specific outcome or next step (e.g. "Start free trial", "Get a demo")' + label_now + ".",
               "Place it directly under the subhead, before any secondary link" + ("." if "micro" in c.T[dev]["aois"] else '; add one line of true microcopy under it (e.g. "No credit card required").')]
        if cp and cp.get("filled") is False:
            pts.insert(0, "The primary CTA is not filled today - give it a solid fill in the brand accent colour.")
        return pts
    if k == "cta_secondary":
        return ["Make the second action explicit: two or three words that name it (\"Book a demo\", \"Read the docs\", \"Watch the tour\").",
                "Same height as the primary, outline or ghost style, directly beside it."]
    if k == "nav_cta":
        return ["Add a filled button at the right end of the header with the same label as the primary CTA (or \"Sign up\" / \"Get started\")."]
    if k == "visual":
        return ["Show the product or its result in the first screen: a real UI screenshot, a short loop or the output the product produces.",
                "Start it at or above the fold line and give it 30–50% of the screen width on desktop."]
    if k == "trust":
        return ["Add one row of 4–6 recognisable customer logos or one proof number under the CTAs, small and in grey."]
    return [f"Bring the {lab(r)} into the reference range."]


def build(res, reviewed=False):
    c = Ctx(res); T = c.T; name = T["name"]; A, R = c.A, c.R
    N = {"title": f"{name} first screen: UI/UX/CRO attention benchmark"}
    ad = A["d"]
    N["goal"] = (f"{name} is validated as a <b>{SHORT[ad['intended']]}</b> page on desktop (against {len(R['d']['ids'])} top-SaaS pages built that way) and "
                 f"as {SHORT[A['m']['intended']]} on mobile ({len(R['m']['ids'])} pages). "
                 + ("The approach was not stated by the owner; it is the one the page follows today." if ad["intended_source"] == "auto" else "The approach was chosen by the owner.")
                 + (f" On desktop it is a weak fit: {ad['weak_fit']}." if ad.get("weak_fit") else ""))
    # verdict
    V = []
    for dev in DEVICES:
        rows = R[dev]["checks"]
        bl = [r for r in rows if r["status"] in ("blind", "missing") and r["role"] != "optional"]
        lo = [r for r in rows if r["status"] == "low" and r["role"] != "optional"]
        ok = [lab(r) for r in rows if r["status"] == "ok" and r["role"] != "optional"]
        hi = [r for r in rows if r["status"] == "high"]
        s = f"<b>{DEV[dev].capitalize()}:</b> "
        if bl:
            s += "blind spot or missing - " + "; ".join(f"{lab(r)} {val(r)} (range {rng(r)})" for r in bl) + ". "
        else:
            s += "no blind spots. "
        if lo:
            s += "Below range - " + "; ".join(f"{lab(r)} {val(r)} ({rng(r)})" for r in lo) + ". "
        if ok:
            s += "In range: " + ", ".join(ok) + ". "
        if hi:
            s += "Above range: " + ", ".join(f"{lab(r)} {val(r)}" + (" (by design)" if c.by_design(dev, r) else "") for r in hi) + "."
        V.append(s.strip())
    N["verdict"] = " ".join(V)
    # actions + guidelines
    acts, G, seen = [], [], set()
    for dev in DEVICES:
        donors = c.donors(dev)
        for r in c.issues(dev):
            key = {"_message": "headline", "_action": "action", "cta_primary": "action"}.get(r["key"], r["key"])
            tag = {"blind": "blind spot", "missing": "missing", "low": "below range"}[r["status"]]
            other = "m" if dev == "d" else "d"
            ro = c.rows[other].get(r["key"])
            target = f"{lab(r)} {rng(r)} {DEV[dev]} (today {val(r)})"
            if (key, dev) in seen:
                continue
            seen.add((key, dev))
            pts = spec(c, dev, r) + ([f"Takes attention from: {'; '.join(donors)}. Each donor should stay inside its own range."] if donors else
                                     ["Takes attention from: the largest element on the screen; re-score to check it stays in its range."])
            ev = f"{val(r)} vs reference p10 {f1(r['p10'])}%, typical {rng(r)}, median {f1(r['med'])}% ({r['n']} of {r['of']} reference pages have it)"
            if not r["key"].startswith("_") and r["target"] is not None:
                d = c.diag(dev, r["key"])
                if d:
                    ev += f"; {d}"
            tiers = r.get("tiers") or {}
            if tiers.get("poor", {}).get("med") is not None:
                ev += f"; poorly made pages: median {f1(tiers['poor']['med'])}%"
            what = "headline and message" if r["key"] in ("_message", "headline") else lab(r)
            if r["key"] == "_message" and c.rows[dev].get("headline", {}).get("target") is not None:
                hr = c.rows[dev]["headline"]; ev += f"; headline alone {val(hr)} vs {rng(hr)} ({hr['status']})"
            G.append({"title": f"G{len(G) + 1} · {'Fix the blind spot' if r['status'] == 'blind' else ('Add' if r['status'] == 'missing' else 'Raise')}: {what}",
                      "tag": f"{DEV[dev]} · {tag}", "points": pts, "target": target + (f"; on {DEV[other]} keep it inside {rng(ro)}" if ro and ro.get('status') in ('ok', 'high') else ""), "evidence": ev})
            acts.append(f"<b>{G[-1]['title'].split(' · ', 1)[1]} ({DEV[dev]}):</b> target {rng(r)} (today {val(r)}).")
    keep_d = [lab(r) for r in R["d"]["checks"] if r["status"] in ("ok", "high") and r["role"] != "optional"]
    keep_m = [lab(r) for r in R["m"]["checks"] if r["status"] in ("ok", "high") and r["role"] != "optional"]
    G.append({"title": f"G{len(G) + 1} · Keep what is in range", "tag": "do not change",
              "points": [f"Desktop: {', '.join(keep_d) or '–'}.", f"Mobile: {', '.join(keep_m) or '–'}.",
                         "Do not push these higher: every extra point comes from an element that is short."],
              "target": "each stays inside or above its reference range after the changes", "evidence": "range check, section 1"})
    G.append({"title": f"G{len(G) + 1} · Validate", "tag": "process",
              "points": ["Mock the changed first screen, score it with this skill and check that every key element is in range and nothing new fell into a blind spot.",
                         "Then run a live A/B test on the conversion that matters (sign-ups, demo requests)."],
              "target": "", "evidence": "predicted attention screens designs; it does not prove conversion."})
    if not acts:
        acts.append("No blind spots or below-range key elements: keep the first screen and use the guidelines only to fine-tune the attention spread.")
    acts.append("<b>Keep</b> the elements that are already in or above range (guideline \"Keep what is in range\").")
    N["top_actions"], N["guidelines"] = acts[:6], G
    # approach notes
    AN = []
    for dev in DEVICES:
        a = A[dev]; sp = a["target_spread"]; rs = R[dev]["spread"]
        AN.append(f"<b>{DEV[dev].capitalize()}:</b> message {f1(sp['message'])}% vs hero visual {f1(sp['visual'])}% → {SHORT[a['current']]} today"
                  + (f" (weak fit: {a['weak_fit']})" if a.get("weak_fit") else "") + f"; {f1(R[dev]['distance'])}% of attention sits in a different block than on the reference pages "
                  f"(reference mean: message {f1(rs.get('message'))}%, action {f1(rs.get('action'))}%, visual {f1(rs.get('visual'))}%).")
        for alt, B in a["by_approach"].items():
            if alt == a["intended"]:
                continue
            sm = B["summary"]
            AN.append(f"If {DEV[dev]} were validated as {SHORT[alt]} ({len(B['ids'])} pages): blind or missing - {', '.join(x.lower() for x in sm['blind'] + sm['missing']) or 'none'}; "
                      f"below range - {', '.join(x.lower() for x in sm['low']) or 'none'}.")
    N["approach_notes"] = AN
    # target notes
    TN = []
    for dev in ("d",):
        aois = sorted(T[dev]["aois"].items(), key=lambda kv: -(kv[1].get("cas_3000") or 0))[:5]
        TN.append("Largest attention shares (3 s): " + "; ".join(f"{k.replace('_', ' ')} {f1(a.get('cas_3000'))}% (area {f1(a.get('area'))}%)" for k, a in aois) + ".")
        for k in ("headline", "cta_primary", "visual"):
            if k in T[dev]["aois"]:
                TN.append(f"{k.replace('_', ' ').capitalize()}: {c.diag(dev, k)}.")
    N["target_notes"] = TN
    M = res["metrics"]["d"]
    BN = [f"Context only: against all {len(res['groups'].get('saas', []))} top-SaaS pages the headline ranks {M['headline']['cas_3000']['saas'].get('rank')} of {M['headline']['cas_3000']['saas'].get('of')} "
          f"and the action block {M['_action']['cas_3000']['saas'].get('rank')} of {M['_action']['cas_3000']['saas'].get('of')} on desktop. Ranks are not the goal."] if M.get("headline", {}).get("cas_3000", {}).get("target") is not None else []
    hr = c.rows["d"].get("headline")
    if hr and hr.get("tiers", {}).get("poor"):
        BN.append(f"Desktop headline {val(hr)} against medians of {f1(hr['med'])}% (reference), {f1(hr['tiers'].get('average', {}).get('med'))}% (average SaaS) and {f1(hr['tiers']['poor']['med'])}% (poorly made SaaS).")
    N["benchmark_notes"] = BN
    N["mobile_notes"] = [V[1]]
    # scorecard
    SC = []
    for k in ("headline", "subhead", "_message", "_action", "cta_primary", "visual"):
        rd, rm = c.rows["d"].get(k), c.rows["m"].get(k)
        if not rd:
            continue
        stl = {"blind": "blind spot", "missing": "missing", "low": "below", "ok": "in range", "high": "above", "absent": "not used", "na": "n/a"}
        tgt = lambda r: ("–" if not r else (f"≥ {f1(r['p25'])}% (range {rng(r)})" if r["status"] == "high" else (("keep " if r["status"] == "ok" else "") + rng(r))))  # noqa: E731
        SC.append({"metric": rd["label"], "today_d": f"{val(rd)} ({stl[rd['status']]})", "target_d": tgt(rd),
                   "today_m": f"{val(rm)} ({stl[rm['status']]})" if rm else "–", "target_m": tgt(rm)})
    N["scorecard"] = SC
    N["limits"] = ["This analysis text was generated automatically from the range check (scripts/narrate.py); copy suggestions are generic directions, not tested copy."]
    if not reviewed:
        N["limits"].append("AOI boxes were detected automatically and not reviewed by eye; check review_d.png / review_m.png if a number looks implausible.")
    N["_generated_by"] = "narrate.py"
    return N


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("--force", action="store_true")
    a = ap.parse_args(); work = Path(a.work)
    res = load(work / "analysis.json")
    if not res or "approach" not in res:
        raise SystemExit("run analyze.py first")
    out = work / "narrative.json"
    if out.exists() and not a.force:
        print(f"{out} exists - kept (use --force to overwrite)"); return
    meta = load(work / "meta.json", {}) or {}
    save(out, build(res, reviewed=bool(meta.get("aoi_reviewed")) or (work / "overrides.json").exists()))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
