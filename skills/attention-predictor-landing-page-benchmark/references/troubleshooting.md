# Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ATTENTION_PREDICTOR_API_TOKEN is not set` | Create a token at https://app.attentionpredictor.com/api and give it to the agent's environment (shell profile, the agent's `.env`, or a secrets manager). Alternative: put it in a file only you can read and set `ATTENTION_PREDICTOR_API_TOKEN_FILE` to its path. Never paste the token into a chat. |
| `HTTP 403 ... error 1010` | The API's Cloudflare rejected the client. `score.py` sends a browser-like User-Agent; keep it. |
| `HTTP 429 Too many requests` | Wait a minute and re-run; finished steps are skipped. Do not score more than about three pages in parallel. |
| `No module named playwright` / Chromium missing | `python scripts/setup.py` (installs Playwright and Pillow, downloads Chromium). |
| No browser possible (sandbox, no install rights) | Take screenshots with the agent's own browser tool and use `capture.py --image-d/--image-m` (see references/workflow.md, step 1). Analysis and report HTML need only Python. |
| Capture shows a bot wall, blank page or pop-up | Increase `--wait`, click the pop-up away with `--click`, or import your own screenshots. Pages behind bot walls cannot be analysed. |
| AOI rejected by the API | Boxes need positive width and height inside the screenshot; `review.py` clamps them. |
| `python` not found | Use `python3` (macOS/Linux) or `py` (Windows). Python 3.9 or newer. |
| Windows path too long | The report is built in a temporary folder and copied to `report/`; `report.py` prints that folder - run `preview.py` on the HTML files there. |
| `analysis.json` has no approach data | It was made by an older version: re-run `analyze.py` (or `run.py ... --redo analyze`). |
| A number looks implausible | Usually a wrong box. Check the `CHECK:` lines and `review_*.png`, fix with overrides, re-run `run.py ... --from review`. |
| Agent does not offer the skill | Restart the agent after installing; check the folder name equals the `name` in SKILL.md; some agents need project skills to be trusted (Hermes: `hermes skills trust`). |
