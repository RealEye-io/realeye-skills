# Workflow: every step and option

`scripts/run.py` runs all of these in order. Use the single scripts when you want control over one step. Paths are relative to the skill folder; work files go to `./ap-work/<slug>/` in the current directory.

## 1. Capture (desktop 1440×900 + mobile 390×844)

```bash
python scripts/capture.py https://example.com --name example_com [--wait 7] [--click d:x,y] [--click m:x,y]
```

Headless Chromium (Playwright). Declines cookie banners (privacy-preserving), hides chat widgets, blocks Google sign-in pop-ups, pauses videos, then probes the DOM for the hero anatomy. Writes `d.png`, `m.png`, `probe_d.json`, `probe_m.json`, `meta.json`.

- A banner survived: re-run with `--click d:x,y` / `--click m:x,y` on its Reject button (screenshot pixel coordinates).
- **No Playwright / no local browser** (sandboxed agents): take the two first-screen screenshots with any browser tool at 1440×900 and 390×844 and import them:
  `python scripts/capture.py https://example.com --name example_com --image-d desk.png --image-m phone.png`
  Nothing is detected in imported images, so every AOI box must come from `overrides.json` (step 2), in screenshot pixels.

## 2. Review the element boxes (AOIs)

```bash
python scripts/review.py ap-work/example_com                      # summary, CHECK warnings, review_d.png / review_m.png
python scripts/review.py ap-work/example_com --inventory d        # every text block (T), button (B), media (M#i) with boxes
python scripts/review.py ap-work/example_com --apply ap-work/example_com/overrides.json
```

AOI keys (same vocabulary as the benchmark, so the comparison is like-for-like): `announce`, `header`, `logo`, `nav_links`, `nav_cta`, `eyebrow`, `headline`, `subhead`, `cta_primary`, `cta_secondary`, `form`, `micro`, `visual`, `trust`, `rating` (plus `video_link`, `eu_banner` for oddities). A stats row or logo row is `trust`; header buttons are `nav_cta`; a headline split over two lines of one sentence is one `headline` box.

`overrides.json` format (also in `templates/overrides.example.json`):

```json
{"d": {"visual": [635, 100, 1320, 640],
       "subhead": {"text": "Accept payments"},
       "cta_primary": {"btn": "Get started", "hd": 0},
       "trust": {"union": [{"text": "Trusted by"}, [100, 700, 1300, 790]]},
       "rating": null,
       "_info": {"headline.t": "Corrected headline"}},
 "m": {}}
```

Explicit boxes are `[x1, y1, x2, y2]` in screenshot pixels (desktop 1440×900, mobile 390×844). Note that `review_d.png` is drawn at 900 px wide: multiply its pixel positions by 1.6 for desktop boxes.

How to check without looking at images: every `CHECK:` line printed by `review.py` (also stored as `checks` in `final_*.json`) flags a likely mistake - no headline, a tiny headline font, no hero CTA, a hero CTA inside the header, a visual box over the whole screen or over the headline, boxes below the fold. Fix what they point at with `--inventory` and overrides. Agents that can view images should also look at `review_d.png` and `review_m.png`; most real-world fixes are a missed CTA, a visual box on empty background, or a stats row tagged as `micro`.

## 3. Score in the Attention Predictor

```bash
python scripts/score.py ap-work/example_com
```

Needs `ATTENTION_PREDICTOR_API_TOKEN` (or `ATTENTION_PREDICTOR_API_TOKEN_FILE` pointing to a file that holds it). Creates a folder → project → uploads each screenshot → waits for the prediction → creates every AOI → reads the AOI report (CAS, Speed, Reach, Hold shares at 3/6/10 s) → downloads the 12 heatmaps per device. About 1–2 minutes. Prints the AOI report links. Runs in the workspace the token belongs to.

## 4. Set the approach and validate against similar pages

```bash
python scripts/analyze.py ap-work/example_com [--approach auto|message|balanced|visual] [--approach-mobile ...]
        [--reference id1,id2] [--reference-pool saas|all|<group>] [--competitors <group>] [--peers id1,id2]
```

- `--approach`: the intended approach. `auto` (default) = the one the page follows today. The reference group = top-SaaS pages with that approach (widened to all pages when fewer than 5 match).
- `--reference`: hand-pick reference pages (ids from `python scripts/benchmark.py list`, which shows each page's approach per device).
- `--competitors` / `--peers`: optional direct competitors, shown as context. The bundled benchmark has no competitor group. If the user names competitors, run steps 1–3 for each, add them with `benchmark.py add ... --group <market>`, then pass `--competitors <market>`.

Writes `analysis.json` and `facts.md`. Per device facts.md starts with "Approach and range check": approach today (and a WEAK FIT warning), the reference pages, the attention spread against the reference mean, each element's value against p10 / p25–p75 / median / max with status and role, the average and poorly made medians, and the result under the other approaches. Then every AOI with all components and windows, attention per area, 3→10 s trends, headline font/words/area, prevalence of hero elements, and ranks (context only).

Re-run with another `--approach` when the user's intent is known and differs, or when the page is a weak fit and the user wants to see the alternative.

## 5. Write the analysis (`narrative.json`)

```bash
python scripts/narrate.py ap-work/example_com            # data-driven draft; keeps an existing file unless --force
```

The draft is complete and safe to publish as is. A capable agent should rewrite it following `references/writing-guide.md` (specific copy directions, the approach decision, budget trade-offs). Fields and a hand-written example: `templates/narrative.example.json`.

## 6. Build and check the report

```bash
python scripts/report.py ap-work/example_com [--appendix reference|all|target] [--out DIR] [--no-pdf]
python scripts/preview.py <report html> --pages 1,2,3        # renders pages to PNG for a visual check
```

Outputs in `ap-work/<slug>/report/`: the main PDF (goal, verdict and status tiles; approach and range check with spread chart and range table per device; how to read; target deep dive with heatmaps; context ranks and per-AOI profiles; distribution charts of reference, top, average and poorly made groups; hero-anatomy table; reference gallery; mobile; guidelines and scorecard; method), the appendix PDF (target and reference pages by default; `all` = every page, about 300 pages), a CSV of every AOI score with links, and the HTML sources. Without a PDF engine the HTML files are complete; print them to PDF.

## 7. Grow the benchmark (optional, ask the user first)

```bash
python scripts/benchmark.py add ap-work/example_com --group saas      # list | add | remove | where
```

Adds the page to the user's own copy (`~/.attention-benchmark/benchmark.json`, or the path in `AP_BENCHMARK`); the bundled data is never modified. Only pages in the reference pool (group `saas`) become reference pages, so add a page there only if it is worth imitating. RealEye and its direct competitors are deliberately not in the bundled benchmark.
