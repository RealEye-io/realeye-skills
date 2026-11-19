---
name: attention-predictor-landing-page-benchmark
description: Analyse and optimise any landing page's first screen with the RealEye Attention Predictor, validated against a bundled benchmark of 150 already-analysed SaaS pages (100 top, 25 average, 25 poorly made) on desktop and mobile. Only the new page is captured and scored. The goal is not to rank first everywhere - it is to find blind spots (e.g. a CTA almost nobody notices) and to bring each element and the overall attention spread to the level of the best pages built the same way (message-led, balanced or visual-led). Delivers a detailed UI/UX/CRO report - approach, range check per element, all attention components (Composite, Speed, Reach, Hold) at 3/6/10 s, heatmaps, improvement guidelines with target ranges - as PDF + appendix + CSV. One command runs everything. Use when asked to analyse, audit, benchmark, optimise or improve a landing page, homepage or hero with attention prediction, heatmaps or the Attention Predictor.
license: MIT (code and instructions). Bundled benchmark data - see DATA-NOTICE.md
compatibility: Any agent that can run shell commands. Python 3.9+, internet access to the target site and app.attentionpredictor.com, an Attention Predictor API token. Playwright Chromium for capture and PDF (or import screenshots from your own browser).
metadata:
  version: "2.0.0"
  repository: "https://github.com/RealEye-io/realeye-skills"
  author: RealEye
  benchmark_captured: "2026-11-13 / 2026-11-16"
---

# Landing-page attention benchmark (Attention Predictor)

When the user asks to analyse landing page X: capture **only X**, score it in the Attention Predictor, validate it against the bundled benchmark (150 SaaS pages; 100 top SaaS are the yardstick, 25 average and 25 poorly made are context), and deliver the report: main PDF, appendix PDF, CSV.

In this file `SKILL_DIR` means the folder that contains this SKILL.md. Run the scripts with the Python 3.9+ interpreter you have (`python`, `python3` or `py`). Work files go to `./ap-work/<slug>/` in the current directory.

## The goal (decides how everything is judged)

Attention is a fixed budget: every screen sums to 100%, so what one element gains another loses. **Rank 1 on every element is never the target.** In this order:

1. **No blind spots** - no important element is missed (a CTA almost nobody notices, a headline lost under a huge visual, a header CTA every similar page has).
2. **Each element at the level of the best pages built the same way** - inside the typical range (p25–p75) of the reference group, not above everyone.
3. **An attention spread that matches the chosen approach** - message, action, visual, trust, header and background split like the reference group's.

Pages are built differently, and that is a legitimate decision, so the approach must be explicit and the page is validated against similarly built pages:

| Approach | Meaning (composite attention at 3 s) |
|---|---|
| `message` Message-led | message block ≥ 2× hero visual, or no hero visual |
| `balanced` Balanced | neither gets 2× the other |
| `visual` Visual-led | hero visual ≥ 2× message block |

If the user said what matters most ("the headline is the hero", "like Stripe"), map it to `--approach` or hand-picked `--reference` pages. If not, do not block on a question: use the approach the page follows today (default), say it was assumed, and offer a re-run with another. A **WEAK FIT** warning means the page has no clear approach yet - choosing one is the first recommendation.

Statuses: **blind spot** (under the 10th percentile of the reference pages), **missing** (most reference pages have it, the target does not), **below range**, **in range**, **above range**, **not used**. Roles: **key** (must not be missed), **supporting** (should be in range), **optional**. Above range is not a win: fine for what the approach puts first, otherwise a sign of where attention can come from.

## Setup (once)

```bash
python SKILL_DIR/scripts/setup.py      # Python packages + Chromium, then checks the token
```

The token comes from the environment variable `ATTENTION_PREDICTOR_API_TOKEN` (or `ATTENTION_PREDICTOR_API_TOKEN_FILE`, a path to a file holding it). The user creates it at https://app.attentionpredictor.com/api. **Never ask the user to paste the token into chat, never print it, never write it to a file yourself.** If it is missing, stop and explain how to set it.

## Run

```bash
python SKILL_DIR/scripts/run.py https://example.com [--approach message|balanced|visual] [--approach-mobile ...]
```

Runs capture → box review → scoring → validation → write-up → report, and resumes where it stopped. It exits with code 2 and a `NEXT:` line when it needs something (a token, or your box check). For the best result:

1. `run.py URL --until review` - captures and detects the element boxes. Read every `CHECK:` line; if you can view images, also look at `ap-work/<slug>/review_d.png` and `review_m.png`. Fix wrong or missing boxes in `ap-work/<slug>/overrides.json` (format and the `--inventory` helper: [references/workflow.md](references/workflow.md), step 2).
2. `run.py URL --from review` - applies the fixes, scores, validates, writes `narrative.json`, builds the report.
3. Read `ap-work/<slug>/facts.md` fully, then rewrite `narrative.json` in your own words following [references/writing-guide.md](references/writing-guide.md), and rebuild with `run.py URL --from report`. The generated write-up is complete and correct, so this step is optional, but it is where the CRO judgement and copy suggestions come from.
4. Check the PDF: `python SKILL_DIR/scripts/preview.py <report>.html --pages 1,2,3` renders pages to PNG (look at them if you can view images).

No local browser? Take 1440×900 and 390×844 first-screen screenshots with your own browser tool and pass `--image-d desk.png --image-m phone.png --overrides boxes.json`; you then give every element box yourself.

Every step can also be run on its own (`capture.py`, `review.py`, `score.py`, `analyze.py`, `narrate.py`, `report.py`) - see [references/workflow.md](references/workflow.md).

## Hand-over

Outputs are in `ap-work/<slug>/report/`: `<slug>-attention-benchmark-<date>.pdf`, `...-appendix.pdf` (target and reference pages), `...-aoi-scores.csv`. Tell the user the approach used (and that it was assumed, if so), the blind spots, what is already in range, and where the files are. Adding the page to the benchmark (`scripts/benchmark.py add`) only when the user asks.

## Facts to state in every report

- Predicted attention (model trained on RealEye webcam eye-tracking sessions), not measured gaze, clicks or conversion; mobile predictions are less validated than desktop.
- "Top SaaS" = the 100 biggest / best-known SaaS companies, not proven best converters; "poorly made" = one reviewer's audit with written criteria; reference groups hold 13–58 pages depending on approach and device.
- On desktop, poorly made pages give the headline a median 8.5% and the message 10.7% of attention against 13.1% and 17.5% for top SaaS; CTA share does not separate the groups (about 2% in all three), and on mobile the groups are close on everything.
- One capture per page; the benchmark was captured on 2026-11-13 and 2026-11-16, the target on its own date. AOI boxes are approximate.

## More

- [references/workflow.md](references/workflow.md) - every script and option, overrides format, screenshot import, competitors, growing the benchmark
- [references/writing-guide.md](references/writing-guide.md) - how to write the analysis
- [references/benchmark-summary.md](references/benchmark-summary.md) - ranges per approach and device, how pages were chosen, all 150 pages
- [references/troubleshooting.md](references/troubleshooting.md) - errors and fixes
- `templates/narrative.example.json`, `templates/overrides.example.json` - examples
