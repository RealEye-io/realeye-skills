"""Shared helpers for the landing-page attention benchmark skill (stdlib only)."""
import json, math, os, re, sys, shutil, subprocess
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # Windows consoles (cp1252) cannot print every character found on web pages
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_DIR / "data"
ASSETS_DIR = SKILL_DIR / "assets" / "benchmark"
JS_DIR = SKILL_DIR / "scripts" / "js"
APP = "https://app.attentionpredictor.com"
DEVICES = {"d": {"label": "desktop", "w": 1440, "h": 900}, "m": {"label": "mobile", "w": 390, "h": 844}}
TR = ["3000", "6000", "10000"]
COMP = ["cas", "speed", "reach", "hold"]

NAMES = {"announce": "Announcement bar", "header": "Header (whole bar)", "logo": "Logo", "nav_links": "Nav links", "nav_cta": "Nav CTA button",
         "eyebrow": "Eyebrow / kicker", "headline": "Headline", "subhead": "Subhead / slogan", "cta_primary": "Primary CTA", "cta_secondary": "Secondary CTA",
         "form": "Sign-up form", "micro": "CTA microcopy", "visual": "Hero visual", "trust": "Trust / logo strip", "rating": "Rating badge",
         "video_link": "Video link", "eu_banner": "Funding banner"}
CODE = {"announce": ("AN", "#6b6b6b"), "header": ("HD", "#444444"), "logo": ("LG", "#8a5a00"), "nav_links": ("NV", "#5b6ee1"), "nav_cta": ("NC", "#0057ff"),
        "eyebrow": ("EY", "#c2185b"), "headline": ("H1", "#d32f2f"), "subhead": ("SH", "#ef6c00"), "cta_primary": ("C1", "#2e7d32"), "cta_secondary": ("C2", "#00897b"),
        "form": ("FM", "#1b5e20"), "micro": ("MI", "#7b1fa2"), "visual": ("VI", "#b28704"), "trust": ("TR", "#00838f"), "rating": ("RT", "#0097a7"),
        "video_link": ("VL", "#6d4c41"), "eu_banner": ("EU", "#455a64")}
GROUP_LABEL = {"target": "Target", "saas": "Top SaaS", "average": "Average SaaS", "poor": "Poorly made SaaS", "custom": "Custom peers"}
TIERS = ["average", "poor"]  # context groups: never the yardstick
MESSAGE_KEYS = ["eyebrow", "headline", "subhead"]
ACTION_KEYS = ["cta_primary", "cta_secondary", "form"]


def nm(k):
    return NAMES.get(k, k.replace("_", " ").capitalize())


def slug(url_or_name):
    s = re.sub(r"^https?://", "", url_or_name.strip()).split("/")[0] if "://" in url_or_name or "." in url_or_name else url_or_name
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()


def load(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8-sig"))


def save(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def benchmark_path():
    """User copy (grows as pages are added) if present, else the bundled dataset."""
    user = Path(os.environ.get("AP_BENCHMARK", Path.home() / ".attention-benchmark" / "benchmark.json"))
    return user if user.exists() else DATA_DIR / "benchmark.json"


def load_benchmark():
    return load(benchmark_path())


def median(a):
    a = sorted(x for x in a if x is not None and not (isinstance(x, float) and math.isnan(x)))
    if not a:
        return None
    m = len(a) // 2
    return a[m] if len(a) % 2 else (a[m - 1] + a[m]) / 2


def quantile(a, p):
    a = sorted(x for x in a if x is not None)
    if not a:
        return None
    i = (len(a) - 1) * p; lo, hi = math.floor(i), math.ceil(i)
    return a[lo] + (a[hi] - a[lo]) * (i - lo)


def rank_of(v, others):
    """1 = highest. Returns (rank, out_of) counting the target itself."""
    vals = [x for x in others if x is not None]
    if v is None:
        return None, len(vals) + 1
    return sum(1 for x in vals if x > v) + 1, len(vals) + 1


def pearson(pairs):
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return None
    mx = sum(p[0] for p in pairs) / n; my = sum(p[1] for p in pairs) / n
    sx = math.sqrt(sum((p[0] - mx) ** 2 for p in pairs)); sy = math.sqrt(sum((p[1] - my) ** 2 for p in pairs))
    if not sx or not sy:
        return None
    return sum((p[0] - mx) * (p[1] - my) for p in pairs) / (sx * sy)


def f1(v):
    return "–" if v is None else f"{round(v + 0.0, 1):.1f}"


def f2(v):
    return "–" if v is None else f"{round(v + 0.0, 2):.2f}"


def find_browser():
    """Chrome/Edge/Chromium executable for PDF rendering when Playwright is not available."""
    cands = [os.environ.get("CHROME_PATH", ""), shutil.which("google-chrome") or "", shutil.which("chromium") or "", shutil.which("chromium-browser") or "",
             shutil.which("msedge") or "", r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for c in cands:
        if c and Path(c).exists():
            return c
    return None


def html_to_pdf(html_path, pdf_path, landscape=False):
    """Playwright Chromium if installed, else a local Chrome/Edge in headless mode. Returns True on success."""
    html_path, pdf_path = Path(html_path).resolve(), Path(pdf_path).resolve()
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto(html_path.as_uri(), wait_until="networkidle")
            pg.pdf(path=str(pdf_path), prefer_css_page_size=True, print_background=True, landscape=landscape)
            b.close()
        return pdf_path.exists()
    except Exception as e:  # noqa: BLE001
        err = e
    br = find_browser()
    if not br:
        print(f"PDF: no Playwright ({err}) and no Chrome/Edge found; open the HTML and print to PDF.", file=sys.stderr)
        return False
    import tempfile
    prof = tempfile.mkdtemp(prefix="appdf_")
    subprocess.run([br, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files", f"--user-data-dir={prof}",
                    f"--print-to-pdf={pdf_path}", html_path.as_uri()], timeout=300, capture_output=True)
    shutil.rmtree(prof, ignore_errors=True)
    return pdf_path.exists()


# ---- approach (how the first screen spends attention) --------------------------------------------------------------
APPROACHES = {"message": "Message-led", "balanced": "Balanced (message + visual)", "visual": "Visual-led"}
APPROACH_DESC = {"message": "the text carries the screen: message block gets at least 2x the hero visual's attention (or there is no hero visual)",
                 "balanced": "message and hero visual share the screen: neither gets 2x the other",
                 "visual": "the product/visual carries the screen: hero visual gets at least 2x the message block's attention"}
BLOCKS = [("message", "Message (eyebrow + headline + subhead)", "#d32f2f"), ("action", "Action (hero CTAs + form)", "#2e7d32"), ("visual", "Hero visual", "#b28704"),
          ("trust", "Trust / proof", "#00838f"), ("nav", "Header + announcement", "#5b6ee1"), ("other", "Background / unassigned", "#d9d7cf")]


def spread(x):
    """Attention spread of one capture over the main blocks (CAS 3 s, sums to 100)."""
    g = lambda k: (x["aois"].get(k) or {}).get("cas_3000") or 0  # noqa: E731
    s = {"message": sum(g(k) for k in MESSAGE_KEYS), "action": sum(g(k) for k in ACTION_KEYS), "visual": g("visual"), "trust": g("trust") + g("rating"),
         "nav": g("header") + g("announce")}
    tot = sum(s.values())
    if tot > 100:  # overlapping boxes
        s = {k: v * 100 / tot for k, v in s.items()}; tot = 100
    s["other"] = 100 - tot
    return {k: round(v, 1) for k, v in s.items()}


def classify(x):
    """Approach of one capture from its message : visual balance (CAS 3 s). Returns (approach, weak_fit_note or None)."""
    sp = spread(x); m, v = sp["message"], sp["visual"]
    a = "visual" if v > 0 and v >= 2 * m else ("message" if m >= 2 * v else "balanced")
    note = None
    if m + v < 12:
        note = f"message + visual get only {m + v:.1f}% together, so the page has no clear approach yet"
    elif a == "visual" and m < 6:
        note = f"visual-led mostly because the message is weak ({m:.1f}%), not necessarily by design"
    elif a == "message" and v == 0 and m < 12:
        note = f"text-only first screen with a weak message ({m:.1f}%)"
    return a, note
