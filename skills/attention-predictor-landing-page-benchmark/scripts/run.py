#!/usr/bin/env python3
"""Run the whole analysis with one command - for any agent, or by hand.

  python scripts/run.py https://example.com                       # everything, automatically -> report
  python scripts/run.py https://example.com --until review        # capture + box review, then stop to check the boxes
  python scripts/run.py https://example.com --from score           # continue after fixing boxes (overrides.json is applied)
  python scripts/run.py https://example.com --approach message     # validate against a chosen approach
  python scripts/run.py https://example.com --image-d d.png --image-m m.png --overrides boxes.json   # no Playwright

Stages: capture -> review -> score -> analyze -> narrate -> report. Finished stages are skipped on a re-run (resume);
--redo STAGE re-runs from that stage. Options after the URL are passed to the matching script:
  --name --work --wait --click (capture) · --overrides (review) · --approach --approach-mobile --reference --reference-pool
  --competitors --peers (analyze) · --appendix --out --no-pdf (report).
The token comes from ATTENTION_PREDICTOR_API_TOKEN (or a file named in ATTENTION_PREDICTOR_API_TOKEN_FILE); it is never printed.
Exit codes: 0 done, 2 stopped for a decision (see the printed NEXT line), 1 error.
"""
import argparse, os, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import load, slug  # noqa: E402

STAGES = ["capture", "review", "score", "analyze", "narrate", "report"]


def sh(script, *args):
    cmd = [sys.executable, str(HERE / script), *[str(x) for x in args if x is not None]]
    print("\n$ " + " ".join(cmd[1:]), flush=True)
    r = subprocess.run(cmd)
    if r.returncode:
        raise SystemExit(f"{script} failed (exit {r.returncode}) - see the message above")


def opt(name, v):
    return [name, v] if v not in (None, False) else []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url"); ap.add_argument("--name"); ap.add_argument("--work", default="ap-work")
    ap.add_argument("--from", dest="start", choices=STAGES); ap.add_argument("--until", choices=STAGES); ap.add_argument("--redo", choices=STAGES)
    ap.add_argument("--wait"); ap.add_argument("--click", action="append", default=[]); ap.add_argument("--image-d"); ap.add_argument("--image-m")
    ap.add_argument("--overrides"); ap.add_argument("--approach"); ap.add_argument("--approach-mobile"); ap.add_argument("--reference")
    ap.add_argument("--reference-pool"); ap.add_argument("--competitors"); ap.add_argument("--peers")
    ap.add_argument("--appendix"); ap.add_argument("--out"); ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    url = a.url if a.url.startswith("http") else "https://" + a.url
    name = a.name or slug(url); work = Path(a.work) / name
    i0 = STAGES.index(a.start) if a.start else 0; i1 = STAGES.index(a.until) if a.until else len(STAGES) - 1
    redo = STAGES.index(a.redo) if a.redo else (i0 if a.start else 99)
    done = {"capture": (work / "d.png").exists() or (work / "m.png").exists(), "review": (work / "final_d.json").exists() or (work / "final_m.json").exists(),
            "score": (work / "scores_d.json").exists() or (work / "scores_m.json").exists(), "analyze": False, "narrate": (work / "narrative.json").exists(), "report": False}
    if a.overrides and Path(a.overrides).resolve() != (work / "overrides.json").resolve():  # keep the boxes with the work files for later re-runs
        work.mkdir(parents=True, exist_ok=True); (work / "overrides.json").write_bytes(Path(a.overrides).read_bytes())
    ov = str(work / "overrides.json") if (work / "overrides.json").exists() else None
    for i, st in enumerate(STAGES):
        if i < i0 or i > i1:
            continue
        if done[st] and i < redo and st not in ("review",):
            print(f"[{st}] already done - skipped (use --redo {st} to repeat)"); continue
        if st == "capture":
            sh("capture.py", url, "--name", name, "--work", a.work, *opt("--wait", a.wait), *sum([["--click", c] for c in a.click], []),
               *opt("--image-d", a.image_d), *opt("--image-m", a.image_m))
        elif st == "review":
            sh("review.py", work, *opt("--apply", ov))
            warn = [w for d in "dm" for w in ((load(work / f"final_{d}.json") or {}).get("checks") or [])]
            if warn and not ov and a.until is None:
                print(f"\nNOTE: {len(warn)} box warning(s) above. Continuing automatically; for a better report stop with --until review, "
                      f"fix the boxes in {work / 'overrides.json'} and re-run with --from review.")
        elif st == "score":
            if not (os.environ.get("ATTENTION_PREDICTOR_API_TOKEN") or os.environ.get("ATTENTION_PREDICTOR_TOKEN") or os.environ.get("ATTENTION_PREDICTOR_API_TOKEN_FILE")):
                print("\nNEXT: set ATTENTION_PREDICTOR_API_TOKEN (create a token at https://app.attentionpredictor.com/api; never paste it into chat), "
                      f"then run: python {HERE / 'run.py'} {url} --name {name} --from score"); sys.exit(2)
            sh("score.py", work)
        elif st == "analyze":
            sh("analyze.py", work, *opt("--approach", a.approach), *opt("--approach-mobile", a.approach_mobile), *opt("--reference", a.reference),
               *opt("--reference-pool", a.reference_pool), *opt("--competitors", a.competitors), *opt("--peers", a.peers))
        elif st == "narrate":
            sh("narrate.py", work, *(["--force"] if i >= redo and (work / "narrative.json").exists() and (load(work / "narrative.json") or {}).get("_generated_by") else []))
        elif st == "report":
            sh("report.py", work, *opt("--appendix", a.appendix), *opt("--out", a.out), *(["--no-pdf"] if a.no_pdf else []))
    if i1 < len(STAGES) - 1:
        nxt = STAGES[i1 + 1]
        print(f"\nNEXT: stopped after '{STAGES[i1]}'. Check {work}/review_d.png and review_m.png (or the CHECK lines above), put corrections in "
              f"{work / 'overrides.json'} if needed, then run: python {HERE / 'run.py'} {url} --name {name} --from {'review' if STAGES[i1] == 'review' else nxt}")
        sys.exit(2)
    print(f"\nDONE. Read {work / 'facts.md'}; the write-up is {work / 'narrative.json'} (rewrite it in your own words for a better report, then re-run with --from report).")


if __name__ == "__main__":
    main()
