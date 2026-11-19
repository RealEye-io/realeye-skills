#!/usr/bin/env python3
"""Inspect or grow the benchmark dataset.

  python scripts/benchmark.py list                      # pages in the benchmark with their approach per device (bundled + any you added)
  python scripts/benchmark.py add ap-work/example [--group saas|eyetracking|uxresearch|<new>] [--name "Example"]
  python scripts/benchmark.py remove example_com
  python scripts/benchmark.py where                     # which dataset file is in use

Added pages go to a user copy (default ~/.attention-benchmark/benchmark.json, override with AP_BENCHMARK); the bundled
data in the skill stays untouched, so updating the skill never loses your additions.
"""
import argparse, copy, os, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import DATA_DIR, DEVICES, benchmark_path, classify, load, save  # noqa: E402

USER = Path(os.environ.get("AP_BENCHMARK", Path.home() / ".attention-benchmark" / "benchmark.json"))


def user_copy():
    if not USER.exists():
        USER.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(DATA_DIR / "benchmark.json", USER)
    return load(USER)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["list", "add", "remove", "where"]); ap.add_argument("arg", nargs="?")
    ap.add_argument("--group", default="custom"); ap.add_argument("--name")
    a = ap.parse_args()
    if a.cmd == "where":
        print(benchmark_path()); return
    if a.cmd == "list":
        b = load(benchmark_path())
        for sid, s in sorted(b["sites"].items(), key=lambda kv: (kv[1]["group"], kv[1]["name"])):
            print(f'{s["group"]:12} {sid:24} {s["name"]:28} desktop {classify(s["d"])[0]:9} mobile {classify(s["m"])[0]:9} captured {s.get("captured")}  {s.get("url")}')
        print(f'{len(b["sites"])} pages  ({benchmark_path()})'); return
    b = user_copy()
    if a.cmd == "remove":
        b["sites"].pop(a.arg, None); save(USER, b); print("removed", a.arg); return
    work = Path(a.arg); res = load(work / "analysis.json")
    if not res:
        raise SystemExit("run analyze.py first")
    t = copy.deepcopy(res["target"])
    adir = USER.parent / "assets"; adir.mkdir(exist_ok=True)
    rec = {"id": t["id"], "name": a.name or t["name"], "url": t["url"], "group": a.group, "captured": t.get("captured"), "source": f'added from {work}'}
    for dev in DEVICES:
        x = t[dev]
        img = adir / f'{dev}_{t["id"]}.png'; shutil.copy(x["img"], img)
        hf = {}
        for k, p in x.get("heat_files", {}).items():
            dst = adir / f'heat_{dev}_{t["id"]}_{k}{Path(p).suffix}'; shutil.copy(p, dst); hf[k] = str(dst)
        rec[dev] = {"aois": {k: {kk: v for kk, v in a_.items() if kk not in ("density", "trend")} for k, a_ in x["aois"].items()}, "info": x["info"], "page": x.get("page"),
                    "report_url": x.get("report_url"), "analyser_url": x.get("analyser_url"), "img": str(img), "heat_files": hf}
    b["sites"][t["id"]] = rec
    if a.group not in b.get("groups", {}):
        b.setdefault("groups", {})[a.group] = a.group.replace("_", " ").capitalize()
    save(USER, b)
    print(f'added {t["id"]} ({a.group}) -> {USER}  ({len(b["sites"])} pages)')


if __name__ == "__main__":
    main()
