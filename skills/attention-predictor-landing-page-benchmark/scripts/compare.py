#!/usr/bin/env python3
"""Compare a page with an earlier version of the same page (e.g. before / after a redesign). Both must be analysed already.

  python scripts/compare.py ap-work/new --previous ap-work/old [--label-old "Old design"] [--label-new "New design"]

Needs analysis.json in both folders (run analyze.py on each, against the same benchmark). Writes <new>/comparison.json, which
report.py turns into an "Old vs new" section and narrate.py into a change summary.

Statuses are judged against the SAME reference group for both versions (the group chosen for the new page), so a change of
status is a change of the page, not of the yardstick. The old page's own status (against the group it followed then) is kept too.
"""
import argparse, copy, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import DEVICES, f1, load, save  # noqa: E402
from analyze import CHECKS  # noqa: E402

BAD = ("blind", "missing", "low")
GOOD = ("ok", "high")
TEXT_KEYS = ["eyebrow", "headline", "subhead", "cta", "cta_order", "micro", "rating", "nav_cta", "trust", "visual", "announce"]


def txt(v):
    if v is None:
        return None
    if isinstance(v, dict):
        return v.get("t") or v.get("label") or v.get("kind") or v.get("all") or None
    return str(v)


def anatomy(t, dev):
    i = t[dev]["info"]; h = i.get("headline") or {}
    cp, cs = i.get("cta_primary") or {}, i.get("cta_secondary") or {}
    vis = i.get("visual") or {}
    return {"eyebrow": txt(i.get("eyebrow")), "headline": txt(h), "headline_px": h.get("f"), "headline_words": h.get("words"), "headline_lines": h.get("lines"),
            "subhead": txt(i.get("subhead")), "cta": " | ".join(x for x in (cp.get("t"), cs.get("t")) if x) or None,
            "cta_primary_filled": cp.get("filled"), "cta_order": i.get("cta_order"), "micro": txt(i.get("micro")), "rating": txt(i.get("rating")),
            "nav_cta": txt(i.get("nav_cta")), "trust": txt(i.get("trust")) if isinstance(i.get("trust"), dict) else None,
            "visual": txt(vis) or (vis.get("tags") if isinstance(vis, dict) else None), "announce": txt(i.get("announce")),
            "has": sorted(t[dev]["aois"].keys())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work"); ap.add_argument("--previous", required=True); ap.add_argument("--label-old"); ap.add_argument("--label-new")
    a = ap.parse_args(); work, pwork = Path(a.work), Path(a.previous)
    new, old = load(work / "analysis.json"), load(pwork / "analysis.json")
    for nm, r, w in (("current", new, work), ("previous", old, pwork)):
        if not r or "approach" not in r:
            raise SystemExit(f"{w}: no usable analysis.json for the {nm} version - run analyze.py there first")
    nmeta, ometa = load(work / "meta.json", {}) or {}, load(pwork / "meta.json", {}) or {}
    warn = []
    if new["benchmark_size"] != old["benchmark_size"] or set(new["peers"]) != set(old["peers"]):
        warn.append("the two analyses used different benchmark pages - statuses against the same reference may differ; re-run analyze.py on both")
    lo = a.label_old or f"Previous version ({ometa.get('captured', '?')})"; ln = a.label_new or f"Current version ({nmeta.get('captured', '?')})"
    T, O = new["target"], old["target"]
    out = {"labels": {"old": lo, "new": ln}, "captured": {"old": ometa.get("captured"), "new": nmeta.get("captured")}, "warnings": warn,
           "benchmark_size": new["benchmark_size"], "approach": {}, "distance": {}, "spread": {}, "elements": {}, "aois": {}, "anatomy": {}, "resolved": {}, "introduced": {}, "still_open": {}}
    prev = copy.deepcopy(O); prev["id"] = O["id"] + "_previous"; prev["name"] = lo; prev["group"] = "previous"; prev["captured"] = ometa.get("captured")
    out["prev_id"] = prev["id"]; out["previous"] = prev
    for dev in DEVICES:
        An, Ao = new["approach"][dev], old["approach"][dev]
        intended = An["intended"]
        out["approach"][dev] = {"old_current": Ao["current"], "new_current": An["current"], "old_intended": Ao["intended"], "new_intended": intended,
                                "old_weak_fit": Ao.get("weak_fit"), "new_weak_fit": An.get("weak_fit"), "same_reference": An["reference"].get("custom") is not True and intended in Ao["by_approach"]}
        out["spread"][dev] = {"old": Ao["target_spread"], "new": An["target_spread"], "reference": An["reference"]["spread"]}
        if out["approach"][dev]["same_reference"]:  # share of attention in a different block than in the reference group, same group for both versions
            out["distance"][dev] = {"old": Ao["by_approach"][intended]["distance"], "new": An["reference"]["distance"]}
        new_rows = {r["key"]: r for r in An["reference"]["checks"]}
        own_rows = {r["key"]: r for r in Ao["reference"]["checks"]}
        same_rows = {r["key"]: r for r in Ao["by_approach"][intended]["checks"]} if out["approach"][dev]["same_reference"] else own_rows
        els, res_, intro, still = [], [], [], []
        for k, label, _ in CHECKS:
            n, o = new_rows.get(k), own_rows.get(k)
            if not n or not o:
                continue
            s_same = (same_rows.get(k) or o)["status"]
            e = {"key": k, "label": label, "role": n["role"], "old": o["target"], "new": n["target"],
                 "delta": (round(n["target"] - o["target"], 2) if n["target"] is not None and o["target"] is not None else None),
                 "p25": n.get("p25"), "p75": n.get("p75"), "med": n.get("med"), "n": n["n"], "of": n["of"],
                 "status_old_own": o["status"], "status_old": s_same, "status_new": n["status"]}
            els.append(e)
            if n["role"] == "optional":
                continue
            if s_same in BAD and n["status"] not in BAD:
                res_.append(label)
            elif s_same not in BAD and n["status"] in BAD and n["status"] != "na":
                intro.append(label)
            elif s_same in BAD and n["status"] in BAD:
                still.append(label)
        out["elements"][dev] = els
        out["resolved"][dev], out["introduced"][dev], out["still_open"][dev] = res_, intro, still
        keys = sorted(set(T[dev]["aois"]) | set(O[dev]["aois"]), key=lambda k: -max((T[dev]["aois"].get(k) or {}).get("cas_3000") or 0, (O[dev]["aois"].get(k) or {}).get("cas_3000") or 0))
        out["aois"][dev] = []
        for k in keys:
            row = {"key": k}
            for side, t in (("old", O), ("new", T)):
                x = t[dev]["aois"].get(k)
                row[side] = None if not x else {m: x.get(m) for m in ("area", "cas_3000", "cas_6000", "cas_10000", "speed_3000", "reach_3000", "hold_3000", "density")}
            out["aois"][dev].append(row)
        out["anatomy"][dev] = {"old": anatomy(O, dev), "new": anatomy(T, dev)}
    save(work / "comparison.json", out)
    for dev in DEVICES:
        ap_ = out["approach"][dev]
        print(f"{DEVICES[dev]['label']}: {ap_['old_current']} -> {ap_['new_current']} | resolved: {', '.join(out['resolved'][dev]) or 'none'} | "
              f"still open: {', '.join(out['still_open'][dev]) or 'none'} | new issues: {', '.join(out['introduced'][dev]) or 'none'}")
    for w in warn:
        print("WARNING:", w)
    print(f"wrote {work / 'comparison.json'}")


if __name__ == "__main__":
    main()
