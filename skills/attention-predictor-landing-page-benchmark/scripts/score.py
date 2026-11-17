#!/usr/bin/env python3
"""Score the captured page in the RealEye Attention Predictor (persisted workflow, so every AOI gets an AOI report link).

  export ATTENTION_PREDICTOR_API_TOKEN=...      (never paste the token into chat; read it from env / a secrets manager)
  python scripts/score.py ap-work/example [--folder-name "LP benchmark example"] [--no-heatmaps]

Steps per device: create folder -> project -> upload screenshot -> wait until ready -> create every AOI from final_<dev>.json
-> AOI report (CAS/Speed/Reach/Hold shares at 3/6/10 s) -> whole-image stats -> download the 12 heatmaps.
Output: <work>/scores_d.json, scores_m.json, heat_<dev>_<component>_<ms>.png
"""
import argparse, json, mimetypes, os, sys, time, uuid, urllib.error, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import APP, DEVICES, NAMES, TR, load, save  # noqa: E402

KEY_OF = {v: k for k, v in NAMES.items()}
HEAT_COMPONENTS = ["composite_attention", "speed", "reach", "hold"]


class API:
    def __init__(self, token, base=APP):
        self.base, self.token = base, token

    def req(self, method, path, body=None, files=None, raw=False, timeout=180, tries=4):
        url = path if path.startswith("http") else self.base + path
        # a browser-like User-Agent: the API sits behind Cloudflare, which rejects Python's default one (error 1010)
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json",
                   "User-Agent": "Mozilla/5.0 (compatible; attention-benchmark-skill/1.0; +https://app.attentionpredictor.com)"}
        data = None
        if files:
            bnd = uuid.uuid4().hex; parts = []
            for k, v in (body or {}).items():
                parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
            for k, p in files.items():
                p = Path(p); ct = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"; filename="{p.name}"\r\nContent-Type: {ct}\r\n\r\n'.encode() + p.read_bytes() + b"\r\n")
            parts.append(f"--{bnd}--\r\n".encode()); data = b"".join(parts)
            headers["Content-Type"] = "multipart/form-data; boundary=" + bnd
        elif body is not None:
            data = json.dumps(body).encode(); headers["Content-Type"] = "application/json"
        last = None
        for i in range(tries):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=timeout) as r:
                    b = r.read()
                    return b if raw else (json.loads(b) if b else {})
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code} {e.read()[:300]!r}"
                if e.code not in (429, 500, 502, 503, 504):
                    raise RuntimeError(f"{method} {path}: {last}") from None
            except Exception as e:  # noqa: BLE001
                last = str(e)
            time.sleep(2 * (i + 1))
        raise RuntimeError(f"{method} {path} failed: {last}")


def score_device(api, work, dev, folder_id, name, heatmaps=True):
    pg = load(work / f"final_{dev}.json")
    if not pg:
        raise SystemExit(f"missing {work / ('final_' + dev + '.json')} - run review.py first")
    proj = api.req("POST", f"/api/folders/{folder_id}/projects", {"name": f"{name} {DEVICES[dev]['label']}"})["project"]
    pid = proj["id"]
    content = api.req("POST", f"/api/projects/{pid}/contents", {"display_name": f"{name}_{dev}.png"}, files={"image": work / f"{dev}.png"})["content"]
    cid = content["id"]
    print(f"[{dev}] uploaded project {pid} content {cid}; waiting for processing ...", flush=True)
    stats = None
    for _ in range(90):
        try:
            m = api.req("GET", f"/api/contents/{cid}/metrics", tries=1, timeout=60)
            if m.get("attention_stats"):
                stats = m["attention_stats"]; break
        except RuntimeError:
            pass
        time.sleep(4)
    if not stats:
        raise SystemExit(f"[{dev}] prediction not ready after 6 min")
    W, H = pg["vw"], pg["vh"]
    for k, b in pg["aoi"].items():
        body = {"name": NAMES.get(k, k), "type": "rectangle", "coordinates": {"x": b[0] / W, "y": b[1] / H, "width": (b[2] - b[0]) / W, "height": (b[3] - b[1]) / H}}
        api.req("POST", f"/api/contents/{cid}/aois", body)
    rep = api.req("GET", f"/api/projects/{pid}/aoi-report")
    aois = {}
    for a in rep.get("aoi_results", []):
        k = KEY_OF.get(a["name"], a["name"].lower().replace(" ", "_"))
        b = pg["aoi"].get(k)
        o = {"box": b, "area": round((b[2] - b[0]) * (b[3] - b[1]) / (W * H) * 100, 2) if b else None,
             "cov": a["results"]["3000ms"]["cell_attention_scores"]["composite_attention"].get("coverage_pct")}
        for t in TR:
            sh = a["results"][t + "ms"]["attention_shares"]
            o["cas_" + t] = sh.get("cas_pct")
            for c in ("speed", "reach", "hold"):
                o[c + "_" + t] = (sh.get(c) or {}).get("attention_share_pct")
        aois[k] = o
    page = {c: {t: {"mean": stats[c][t + "ms"]["mean"], "std": stats[c][t + "ms"]["std"], "max": stats[c][t + "ms"]["max"]} for t in TR}
            for c in ("composite_attention", "speed", "reach", "hold") if c in stats}
    out = {"device": dev, "project_id": pid, "content_id": cid, "folder_id": folder_id, "aois": aois, "page": page,
           "report_url": f"{APP}/summary/{folder_id}/aois-report/{pid}", "analyser_url": f"{APP}/projects/{pid}/heatmap-analyser", "heat_files": {}}
    if heatmaps:
        hm = api.req("GET", f"/api/contents/{cid}/heatmaps").get("heatmaps", {})
        for c in HEAT_COMPONENTS:
            for t in TR:
                url = (hm.get(c) or {}).get(t + "ms")
                if not url:
                    continue
                try:
                    data = api.req("GET", url, raw=True, timeout=120)
                    is_png = data[:4] == b"\x89PNG"
                    if is_png or data[:3] == b"\xff\xd8\xff":
                        ext = "png" if is_png else "jpg"
                        fn = f"heat_{dev}_{c}_{t}.{ext}"
                        (work / fn).write_bytes(data); out["heat_files"][f"{c}_{t}"] = fn
                except Exception as e:  # noqa: BLE001
                    print(f"[{dev}] heatmap {c} {t}: {e}", file=sys.stderr)
    save(work / f"scores_{dev}.json", out)
    print(f"[{dev}] {len(aois)} AOIs scored, {len(out['heat_files'])} heatmaps saved. AOI report: {out['report_url']}")
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("--folder-name"); ap.add_argument("--no-heatmaps", action="store_true")
    ap.add_argument("--base", default=APP)
    a = ap.parse_args(); work = Path(a.work)
    token = os.environ.get("ATTENTION_PREDICTOR_API_TOKEN") or os.environ.get("ATTENTION_PREDICTOR_TOKEN")
    tf = os.environ.get("ATTENTION_PREDICTOR_API_TOKEN_FILE")
    if not token and tf and Path(tf).expanduser().is_file():
        token = Path(tf).expanduser().read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("Set ATTENTION_PREDICTOR_API_TOKEN (create one at https://app.attentionpredictor.com/api). Do not paste it into chat.")
    api = API(token, a.base)
    who = api.req("GET", "/check-auth")
    if not who.get("authenticated"):
        raise SystemExit("token not accepted by /check-auth")
    meta = load(work / "meta.json", {}) or {}
    name = meta.get("name") or work.name
    folder = api.req("POST", "/api/folders", {"name": a.folder_name or f"LP benchmark {name} {time.strftime('%Y-%m-%d %H%M')}"})["folder"]
    print(f"workspace: {(who.get('company') or {}).get('name')} | folder {folder['id']}")
    for dev in DEVICES:
        if (work / f"final_{dev}.json").exists():
            score_device(api, work, dev, folder["id"], name, not a.no_heatmaps)
    meta.update({"folder_id": folder["id"], "folder_url": f"{APP}/summary/{folder['id']}", "workspace": (who.get("company") or {}).get("name")})
    save(work / "meta.json", meta)


if __name__ == "__main__":
    main()
