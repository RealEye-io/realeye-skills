#!/usr/bin/env python3
"""Compare the scored page with the benchmark: first against the pages built the same way (its approach), then against everything.

  python scripts/analyze.py ap-work/example [--approach auto|message|balanced|visual] [--approach-mobile ...] [--reference id1,id2]
                                            [--reference-pool saas|all|<group>] [--competitors eyetracking] [--peers stripe_com,notion_com]

The goal of an optimisation is NOT rank 1 on every element (attention is a fixed budget). It is: no important element in a blind spot, and
an attention spread like the best pages that follow the same approach.
--approach       : the intended approach of the page (see common.APPROACHES). auto = the approach the page follows today.
--reference      : hand-picked benchmark ids to validate against (instead of "same approach within the reference pool").
--reference-pool : where reference pages come from; default saas (the top-SaaS set). Widened to all pages when fewer than 5 match.

--competitors : optional benchmark group to show as the target's direct competitors (a group you added with benchmark.py add --group <market>).
                Use --peers to hand-pick competitor ids instead. Default: no competitor group.
The bundled benchmark has three groups: saas (100 top pages = the reference pool), average and poor (25 each, context only).
Output: <work>/analysis.json (everything the report needs) and <work>/facts.md (plain-text findings for writing the narrative).
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import (TIERS, ACTION_KEYS, APPROACHES, APPROACH_DESC, BLOCKS, classify, spread, COMP, DEVICES, GROUP_LABEL, MESSAGE_KEYS, TR, f1, f2, load, load_benchmark, median, nm, pearson,  # noqa: E402
                    quantile, rank_of, save, slug)

AOI_KEYS = ["headline", "subhead", "eyebrow", "cta_primary", "cta_secondary", "form", "micro", "visual", "trust", "nav_links", "nav_cta", "logo", "header", "announce", "rating"]
METRICS = [c + "_" + t for t in TR for c in COMP]


def derive(rec, dev):
    x = rec[dev]; W, H = DEVICES[dev]["w"], DEVICES[dev]["h"]
    for k, a in x["aois"].items():
        if a.get("area") is None and a.get("box"):
            b = a["box"]; a["area"] = round((b[2] - b[0]) * (b[3] - b[1]) / (W * H) * 100, 2)
        a["density"] = round(a["cas_3000"] / a["area"], 2) if a.get("area") and a.get("cas_3000") is not None else None
        a["trend"] = round(a["cas_10000"] - a["cas_3000"], 2) if a.get("cas_10000") is not None and a.get("cas_3000") is not None else None
    x["message_cas"] = round(sum(x["aois"][k]["cas_3000"] for k in MESSAGE_KEYS if k in x["aois"]), 2)
    x["action_cas"] = round(sum(x["aois"][k]["cas_3000"] for k in ACTION_KEYS if k in x["aois"]), 2)
    hv = x["aois"].get("headline", {}).get("cas_3000"); vv = x["aois"].get("visual", {}).get("cas_3000")
    x["hv_ratio"] = round(hv / vv, 2) if hv is not None and vv else None
    return rec


def metric(rec, dev, k, m):
    x = rec[dev]
    if k == "_message":
        return x.get("message_cas") if m == "cas_3000" else None
    if k == "_action":
        return x.get("action_cas") if m == "cas_3000" else None
    a = x["aois"].get(k)
    return a.get(m) if a else None


# element, role per approach: key = must not be missed, support = should be in range, optional = fine to leave out
CHECKS = [("_message", "Message block", {"message": "key", "balanced": "key", "visual": "key"}),
          ("headline", "Headline", {"message": "key", "balanced": "key", "visual": "key"}),
          ("subhead", "Subhead / slogan", {"message": "support", "balanced": "support", "visual": "support"}),
          ("_action", "Action block (hero CTAs + form)", {"message": "key", "balanced": "key", "visual": "key"}),
          ("cta_primary", "Primary CTA", {"message": "key", "balanced": "key", "visual": "key"}),
          ("cta_secondary", "Secondary CTA", {"message": "support", "balanced": "support", "visual": "support"}),
          ("micro", "CTA microcopy", {"message": "optional", "balanced": "optional", "visual": "optional"}),
          ("visual", "Hero visual", {"message": "optional", "balanced": "key", "visual": "key"}),
          ("trust", "Trust / proof strip", {"message": "optional", "balanced": "optional", "visual": "optional"}),
          ("nav_cta", "Nav CTA button", {"message": "support", "balanced": "support", "visual": "support"})]
STATUS_LABEL = {"blind": "BLIND SPOT", "missing": "MISSING", "low": "below range", "ok": "in range", "high": "above range", "absent": "not used (fine: optional or many reference pages skip it)", "na": "n/a"}


def check_rows(target, peers, ref_ids, dev, approach):
    """Each element of the target vs the range of the reference pages (p25-p75 = typical range, below p10 = blind spot)."""
    rows = []
    for k, label, roles in CHECKS:
        tv = metric(target, dev, k, "cas_3000")
        if k.startswith("_") and not tv:
            tv = None
        vals = [metric(peers[i], dev, k, "cas_3000") for i in ref_ids]; vals = [v for v in vals if v]
        n = len(vals); prev = n / len(ref_ids) if ref_ids else 0
        role = roles.get(approach, "support")
        if role == "key" and prev < .5:
            role = "support"
        r = {"key": k, "label": label, "role": role, "target": tv, "n": n, "of": len(ref_ids), "p10": quantile(vals, .1), "p25": quantile(vals, .25), "med": median(vals),
             "p75": quantile(vals, .75), "min": min(vals) if vals else None, "max": max(vals) if vals else None}
        if k == "cta_primary" and tv is None and "form" in target[dev]["aois"]:
            r["status"] = "na"; r["note"] = "sign-up form instead of a button - see the action block"
        elif tv is None:
            r["status"] = "missing" if role != "optional" and prev >= (.5 if role == "key" else 2 / 3) else "absent"
        elif n < 3:
            r["status"] = "na"; r["note"] = "too few reference pages have it"
        else:
            r["status"] = "blind" if tv < r["p10"] else ("low" if tv < r["p25"] else ("high" if tv > r["p75"] else "ok"))
        rows.append(r)
    return rows


def approach_block(target, peers, dev, intended, ref_pool, ref_custom):
    cur, note = classify(target[dev]); members = {sid: classify(s[dev])[0] for sid, s in peers.items()}
    intended = cur if intended in (None, "auto") else intended
    tsp = spread(target[dev]); by = {}
    for a in APPROACHES:
        ids = [i for i, m in members.items() if m == a and (ref_pool == "all" or peers[i]["group"] == ref_pool)]; widened = False
        if len(ids) < 5:
            ids = [i for i, m in members.items() if m == a]; widened = True
        sps = [spread(peers[i][dev]) for i in ids]
        mean = {b[0]: round(sum(s[b[0]] for s in sps) / len(sps), 1) for b in BLOCKS} if sps else {}
        dist = round(sum(abs(tsp[b[0]] - mean.get(b[0], 0)) for b in BLOCKS) / 2, 1) if sps else None
        rows = check_rows(target, peers, ids, dev, a)
        by[a] = {"ids": ids, "widened": widened, "spread": mean, "distance": dist, "checks": rows,
                 "summary": {st: [r["label"] for r in rows if r["status"] == st and (r["role"] != "optional" or st in ("ok", "high"))] for st in ("blind", "missing", "low", "ok", "high")}}
    out = {"current": cur, "weak_fit": note, "intended": intended, "intended_source": "auto" if intended == cur else "chosen", "members": members, "target_spread": tsp,
           "by_approach": by, "reference_pool": ref_pool, "closest_by_spread": min((a for a in by if by[a]["distance"] is not None), key=lambda a: by[a]["distance"], default=None)}
    if ref_custom:
        ids = [i for i in ref_custom if i in peers]; sps = [spread(peers[i][dev]) for i in ids]
        mean = {b[0]: round(sum(s[b[0]] for s in sps) / len(sps), 1) for b in BLOCKS}
        out["reference"] = {"ids": ids, "widened": False, "custom": True, "spread": mean, "distance": round(sum(abs(tsp[b[0]] - mean[b[0]]) for b in BLOCKS) / 2, 1),
                            "checks": check_rows(target, peers, ids, dev, intended)}
    else:
        out["reference"] = dict(by[intended], custom=False)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("--competitors"); ap.add_argument("--peers")
    ap.add_argument("--approach", default="auto", choices=["auto"] + list(APPROACHES)); ap.add_argument("--approach-mobile", choices=["auto"] + list(APPROACHES))
    ap.add_argument("--reference"); ap.add_argument("--reference-pool", default="saas")
    a = ap.parse_args(); work = Path(a.work)
    meta = load(work / "meta.json", {}) or {}
    bench = load_benchmark()
    tid = meta.get("name") or work.name
    target = {"id": tid, "name": meta.get("display_name") or meta.get("url", tid).replace("https://", "").rstrip("/"), "url": meta.get("url"), "group": "target",
              "captured": meta.get("captured"), "folder_url": meta.get("folder_url"), "workspace": meta.get("workspace")}
    for dev in DEVICES:
        fin, sc = load(work / f"final_{dev}.json"), load(work / f"scores_{dev}.json")
        if not fin or not sc:
            raise SystemExit(f"missing final_{dev}.json or scores_{dev}.json in {work}")
        target[dev] = {"aois": sc["aois"], "info": fin["info"], "page": sc.get("page"), "report_url": sc["report_url"], "analyser_url": sc["analyser_url"],
                       "img": str((work / f"{dev}.png").resolve()), "heat_files": {k: str((work / v).resolve()) for k, v in sc.get("heat_files", {}).items()}}
        derive(target, dev)
    peers = {sid: s for sid, s in bench["sites"].items() if sid != tid and slug(s.get("url", "")) != slug(target["url"] or "x")}
    for s in peers.values():
        for dev in DEVICES:
            derive(s, dev)
    groups = {}
    for sid, s in peers.items():
        groups.setdefault(s["group"], []).append(sid)
    comp_group = a.competitors if a.competitors in groups else None
    if a.peers:
        groups["custom"] = [p.strip() for p in a.peers.split(",") if p.strip() in peers]; comp_group = "custom"
    groups["all"] = list(peers)
    res = {"target": target, "peers": peers, "groups": groups, "competitor_group": comp_group, "group_labels": dict(GROUP_LABEL, **bench.get("groups", {}), all="All benchmark pages"),
           "benchmark_size": len(peers), "metrics": {}, "stats": {}, "approach": {},
           "approach_labels": APPROACHES, "approach_desc": APPROACH_DESC}
    ref_custom = [p.strip() for p in a.reference.split(",")] if a.reference else None
    pool = a.reference_pool if a.reference_pool == "all" or a.reference_pool in groups else "saas"
    for dev in DEVICES:
        res["tiers"] = [g for g in TIERS if g in groups]
        res["approach"][dev] = approach_block(target, peers, dev, a.approach if dev == "d" else (a.approach_mobile or a.approach), pool, ref_custom)
    for dev in DEVICES:
        M = {}
        for k in AOI_KEYS + ["_message", "_action"]:
            M[k] = {}
            for m in (["cas_3000"] if k.startswith("_") else METRICS + ["density", "trend", "area"]):
                tv = metric(target, dev, k, m); o = {"target": tv}
                for g, ids in groups.items():
                    vals = [metric(peers[i], dev, k, m) for i in ids]; vals = [v for v in vals if v is not None]
                    r, of = rank_of(tv, vals)
                    o[g] = {"n": len(vals), "med": median(vals), "p25": quantile(vals, .25), "p75": quantile(vals, .75),
                            "min": min(vals) if vals else None, "max": max(vals) if vals else None, "rank": r if vals else None, "of": of}
                M[k][m] = o
        res["metrics"][dev] = M
        allp = list(peers.values()) + [target]
        hl = [(s[dev]["aois"]["headline"].get("area"), s[dev]["aois"]["headline"].get("cas_3000")) for s in allp if "headline" in s[dev]["aois"]]
        fs = [((s[dev]["info"].get("headline") or {}).get("f"), s[dev]["aois"]["headline"].get("cas_3000")) for s in allp if "headline" in s[dev]["aois"]]
        prev = {k: sum(1 for s in peers.values() if k in s[dev]["aois"]) for k in AOI_KEYS}
        prev["two_ctas"] = prev["cta_secondary"]
        fonts = [(s[dev]["info"].get("headline") or {}).get("f") for s in peers.values()]
        words = [(s[dev]["info"].get("headline") or {}).get("words") for s in peers.values()]
        res["stats"][dev] = {"r_area_headline": pearson(hl), "r_font_headline": pearson(fs), "n_headline": len(hl), "prevalence": prev, "n_peers": len(peers),
                             "headline_font_median": median(fonts), "headline_words_median": median(words),
                             "headline_area_median": median([s[dev]["aois"]["headline"].get("area") for s in peers.values() if "headline" in s[dev]["aois"]])}
    save(work / "analysis.json", res)
    (work / "facts.md").write_text(facts(res), encoding="utf-8")
    for dev in DEVICES:  # context: where the average and the poorly made pages sit on each checked element
        blocks = [res["approach"][dev]["reference"]] + list(res["approach"][dev]["by_approach"].values())
        for B in blocks:
            for r in B["checks"]:
                r["tiers"] = {}
                for g in res["tiers"]:
                    vals = [metric(peers[i], dev, r["key"], "cas_3000") for i in groups[g]]; vals = [v for v in vals if v]
                    r["tiers"][g] = {"n": len(vals), "of": len(groups[g]), "med": median(vals), "p25": quantile(vals, .25), "p75": quantile(vals, .75)}
    save(work / "analysis.json", res); (work / "facts.md").write_text(facts(res), encoding="utf-8")
    print(f"analysis.json + facts.md written ({len(peers)} benchmark pages; competitor group: {comp_group or 'none'})")
    for dev in DEVICES:
        A = res["approach"][dev]; R = A["reference"]
        st = lambda s: ", ".join(r["label"] for r in R["checks"] if r["status"] == s and r["role"] != "optional") or "none"  # noqa: E731
        print(f"{DEVICES[dev]['label']}: today {APPROACHES[A['current']]}; validated as {APPROACHES[A['intended']]} against {len(R['ids'])} reference pages | "
              f"blind spots: {st('blind')} | missing: {st('missing')} | below range: {st('low')}")


def facts(res):
    T = res["target"]; G = res["competitor_group"]
    L = [f"# Facts for {T['name']} (vs {res['benchmark_size']} benchmark pages: " + ", ".join(f"{len(v)} {res['group_labels'].get(g, g)}" for g, v in res["groups"].items() if g != "all")
         + f"; competitors = {res['group_labels'].get(G, G) if G else 'none set'})", ""]
    L += ["GOAL: not rank 1 everywhere (attention is a fixed budget: what one element gains, another loses). The goal is (1) no key element in a blind spot or missing,",
          "(2) every key/support element inside the typical range (p25-p75) of the best pages built the same way, (3) an overall attention spread like that group's.",
          "Average-SaaS and poorly-made-SaaS medians are shown as context (where not to be); they are never the target.",
          "'above range' is not a win by itself: check what pays for it. Ranks further down are context only.", ""]
    for dev in DEVICES:
        x = T[dev]; M = res["metrics"][dev]; S = res["stats"][dev]; A = res["approach"][dev]; R = A["reference"]
        L.append(f"## {DEVICES[dev]['label']}")
        L.append(f"### Approach and range check ({DEVICES[dev]['label']})")
        L.append(f"Approach today: {APPROACHES[A['current']]} ({APPROACH_DESC[A['current']]})" + (f" - WEAK FIT: {A['weak_fit']}" if A["weak_fit"] else "")
                 + f". Validated as: {APPROACHES[A['intended']]} ({'same as today, assumed' if A['intended_source'] == 'auto' else 'chosen'}). Closest group by overall spread: {APPROACHES.get(A['closest_by_spread'])}.")
        L.append(f"Reference pages ({len(R['ids'])}{', hand-picked' if R.get('custom') else ''}{', widened beyond the ' + A['reference_pool'] + ' pool (too few matches)' if R.get('widened') else ''}): "
                 + ", ".join(res["peers"][i]["name"] for i in R["ids"]))
        L.append("Spread % (message / action / visual / trust / header / unassigned): target " + " / ".join(f1(A["target_spread"][b[0]]) for b in BLOCKS) + " | reference mean "
                 + " / ".join(f1(R["spread"][b[0]]) for b in BLOCKS) + f" | {f1(R['distance'])}% of attention sits in a different block than in the reference")
        L.append("Range check (CAS 3 s; role; target vs reference p10 | p25-p75 | median | max; pages having it):")
        for r in R["checks"]:
            L.append(f"- {r['label']} [{r['role']}]: {'none' if r['target'] is None else f1(r['target'])} vs p10 {f1(r['p10'])} | {f1(r['p25'])}-{f1(r['p75'])} | med {f1(r['med'])} | max {f1(r['max'])} "
                     f"({r['n']}/{r['of']}) => {STATUS_LABEL[r['status']]}" + (f" ({r['note']})" if r.get("note") else "")
                     + "".join(f" | {res['group_labels'].get(g, g)} med {f1(v['med'])} ({v['n']}/{v['of']})" for g, v in (r.get("tiers") or {}).items()))
        for a_ in APPROACHES:
            if a_ == A["intended"] and not R.get("custom"):
                continue
            B = A["by_approach"][a_]; sm = B["summary"]
            L.append(f"If validated as {APPROACHES[a_]} instead ({len(B['ids'])} pages, spread distance {f1(B['distance'])}%): blind/missing: {', '.join(sm['blind'] + sm['missing']) or 'none'}; "
                     f"below range: {', '.join(sm['low']) or 'none'}; above range: {', '.join(sm['high']) or 'none'}")
        L.append(f"### Details and context ({DEVICES[dev]['label']})")
        L.append("AOIs by CAS 3s (CAS/Speed/Reach/Hold @3s | CAS 6s | CAS 10s | area% | attn/area):")
        for k, a in sorted(x["aois"].items(), key=lambda kv: -(kv[1].get("cas_3000") or 0)):
            L.append(f"- {nm(k)}: {f1(a.get('cas_3000'))}/{f1(a.get('speed_3000'))}/{f1(a.get('reach_3000'))}/{f1(a.get('hold_3000'))} | {f1(a.get('cas_6000'))} | {f1(a.get('cas_10000'))} | {f1(a.get('area'))} | {f1(a.get('density'))}")
        L.append(f"Message block {f1(x['message_cas'])}% | action block {f1(x['action_cas'])}% | headline/visual ratio {x.get('hv_ratio')}")
        L.append("Ranks, context only - rank 1 is not the goal (CAS 3 s; rank 1 = most attention; flags: LOW = bottom 20% vs SaaS, HIGH = top 20%):")
        for k in ["_message", "headline", "eyebrow", "subhead", "_action", "cta_primary", "cta_secondary", "form", "micro", "visual", "trust", "nav_cta", "header", "announce"]:
            o = M[k]["cas_3000"]; s, c = o["saas"], o.get(G, {})
            if o["target"] is None:
                L.append(f"- {nm(k) if not k.startswith('_') else k}: NONE on target (present on {s['n']} SaaS pages)"); continue
            flag = " LOW" if s.get("rank") and s["rank"] / s["of"] > .8 else (" HIGH" if s.get("rank") and s["rank"] <= max(3, s["of"] * .2) else "")
            L.append(f"- {k if k.startswith('_') else nm(k)}: {f1(o['target'])} | SaaS med {f1(s['med'])} (IQR {f1(s['p25'])}-{f1(s['p75'])}) rank {s['rank']}/{s['of']}"
                     + (f" | competitors med {f1(c.get('med'))} rank {c.get('rank')}/{c.get('of')}" if G else "") + flag)
        for k in ("headline", "cta_primary", "visual"):
            if k in x["aois"]:
                d_ = M[k]["density"]; ar = M[k]["area"]
                L.append(f"{nm(k)}: attn/area {f1(d_['target'])} (SaaS med {f1(d_['saas']['med'])}), area {f1(ar['target'])}% (SaaS med {f1(ar['saas']['med'])}%), "
                         f"3s->10s {f1(M[k]['trend']['target'])} pts (SaaS med {f1(M[k]['trend']['saas']['med'])})")
        h = x["info"].get("headline") or {}
        L.append(f"Headline: \"{h.get('t')}\" {h.get('f')}px {h.get('words')} words (peer medians {f1(S['headline_font_median'])}px, {S['headline_words_median']} words, area {f1(S['headline_area_median'])}%); "
                 f"r(area, headline share) = {f2(S['r_area_headline'])}, r(font, share) = {f2(S['r_font_headline'])} over {S['n_headline']} pages")
        i = x["info"]
        L.append(f"Subhead: \"{(i.get('subhead') or {}).get('t', '')}\" | CTAs: {i.get('cta_order')} (primary filled: {(i.get('cta_primary') or {}).get('filled')}) | microcopy: {i.get('micro')} | nav CTA: {(i.get('nav_cta') or {}).get('all')} | trust: {i.get('trust')} | visual: {i.get('visual')}")
        L.append("Prevalence among peers: " + ", ".join(f"{k} {v}/{S['n_peers']}" for k, v in S["prevalence"].items() if k in ("subhead", "eyebrow", "two_ctas", "micro", "trust", "form", "visual", "nav_cta", "announce")))
        L.append("")
    L.append("Top headline pages (desktop): " + "; ".join(f"{s['name']} {f1(s['d']['aois']['headline']['cas_3000'])}% ({(s['d']['info'].get('headline') or {}).get('f')}px)"
                                                       for s in sorted([s for s in res["peers"].values() if 'headline' in s['d']['aois']], key=lambda s: -s['d']['aois']['headline']['cas_3000'])[:5]))
    if G:
        L.append(f"Competitor pages ({G}): " + "; ".join(f"{res['peers'][i]['name']}: \"{(res['peers'][i]['d']['info'].get('headline') or {}).get('t')}\"" for i in res["groups"].get(G, [])))
    return "\n".join(L)


if __name__ == "__main__":
    main()
