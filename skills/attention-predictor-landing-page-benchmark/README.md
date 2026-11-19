# Landing-page attention benchmark - a skill for any AI agent

Ask your agent *"Analyse landing page https://example.com with the Attention Predictor"* and get a detailed UI/UX/CRO report. The page's first screen is captured on desktop and mobile, scored in the RealEye Attention Predictor (Composite, Speed, Reach and Hold attention at 3, 6 and 10 s for every hero element), and validated against a bundled benchmark of 150 SaaS landing pages: 100 top SaaS pages as the yardstick, 25 average and 25 poorly made pages as context. Output: a main PDF (verdict, approach and range check, heatmaps, guidelines with target ranges), an appendix PDF and a CSV of every score.

**What it optimises for.** Not rank 1 on every element: attention is a fixed budget, so no page can lead everywhere. The skill finds blind spots (for example a CTA almost nobody is predicted to notice), checks that each element sits in the range of the best pages built the same way (message-led, balanced or visual-led), and compares the overall attention spread with that group.

## Works with

The skill follows the open [Agent Skills](https://agentskills.io/specification) format (a folder with `SKILL.md`, `scripts/`, `references/`, `assets/`) and passes the reference validator (`skills-ref validate`). Everything it does runs through plain Python scripts, so any agent that can run shell commands can use it - including agents that cannot view images or write long analyses:

- `scripts/run.py` runs the whole pipeline with one command and resumes where it stopped.
- `scripts/narrate.py` writes the full analysis from the data, so the report is complete even if the agent writes nothing itself.
- `scripts/review.py` prints plain-text `CHECK:` warnings about the detected element boxes, for agents that cannot look at the review images.
- `capture.py --image-d/--image-m` imports screenshots from the agent's own browser when Playwright cannot run.

## Install

From GitHub (repository [RealEye-io/realeye-skills](https://github.com/RealEye-io/realeye-skills)), pick one:

```bash
npx skills add RealEye-io/realeye-skills --skill attention-predictor-landing-page-benchmark          # any agent (skills CLI)
hermes skills install RealEye-io/realeye-skills/skills/attention-predictor-landing-page-benchmark    # Hermes Agent
```

Claude Code: `/plugin marketplace add RealEye-io/realeye-skills`, then `/plugin install attention-predictor-landing-page-benchmark@realeye-skills`.

Then run the one-time setup from the installed folder: `python <skill folder>/scripts/setup.py`.

Or download this folder (or the zip) and run the bundled installer with the agents you use:

```bash
python attention-predictor-landing-page-benchmark/scripts/install.py --list               # targets and which agents are found
python attention-predictor-landing-page-benchmark/scripts/install.py --agent detected --setup
```

| Agent | Command (`--agent ...`) | Folder the skill is copied to |
|---|---|---|
| OpenAI Codex, Cursor, Gemini CLI, OpenCode | `agents` (or `codex`) | `~/.agents/skills/` (read by all four) |
| Claude Code (CLI, desktop app Code tab, IDEs) | `claude` | `~/.claude/skills/` |
| Hermes Agent | `hermes` | `~/.hermes/skills/marketing/` |
| Cursor only / Gemini CLI only / OpenCode only | `cursor` / `gemini` / `opencode` | `~/.cursor/skills/`, `~/.gemini/skills/`, `~/.config/opencode/skills/` |
| One repository, for everyone who uses it | `--project <repo>` | `<repo>/.agents/skills/` and `<repo>/.claude/skills/` |
| Any other skill-aware agent | `--dest <folder>` | the folder its skill loader scans |

`--setup` installs Playwright, Pillow and Chromium and checks the token. Restart the agent afterwards.

Other ways to install:

- **Claude desktop / claude.ai (chat):** Settings → Capabilities → Skills → upload the zip. The chat sandbox needs network access to the analysed site and app.attentionpredictor.com, and may not be able to run a browser; then use the screenshot import, or use Claude Code.
- **Hermes:** `hermes skills install <url to SKILL.md>` also works when the folder is hosted (Hermes fetches `scripts/`, `references/`, `assets/` with it). Alternatively add the unzipped folder's parent to `skills.external_dirs` in `~/.hermes/config.yaml`. Project-level skills need `hermes skills trust`.
- **Agents without skill support:** put the folder anywhere and tell the agent: *"Read SKILL.md in <folder> and follow it to analyse https://example.com."*

## API token

Create a token at https://app.attentionpredictor.com/api and make it visible to the agent as the environment variable `ATTENTION_PREDICTOR_API_TOKEN` - in your shell profile, the agent's environment file (Hermes: `~/.hermes/.env` or `terminal.env_passthrough`), or your secrets manager. Alternatively set `ATTENTION_PREDICTOR_API_TOKEN_FILE` to the path of a file that only you can read. Never paste the token into a chat. Scores are saved in the Attention Predictor workspace the token belongs to.

## Requirements

Python 3.9 or newer; internet access to the analysed site and app.attentionpredictor.com; Playwright with Chromium for capture and PDF (installed by `scripts/setup.py`); Pillow (optional, keeps PDFs small). Tested on Windows; the scripts use only portable Python.

## Use

Ask: *"Analyse landing page https://example.com using the Attention Predictor"* - optionally *"we want a message-led page"*, *"validate it against Stripe and Intercom"*, *"our competitors are …"*, *"add it to the benchmark"*.

By hand, from any folder:

```bash
S=~/.agents/skills/attention-predictor-landing-page-benchmark     # or wherever you installed it
python $S/scripts/run.py https://example.com --until review      # capture + element boxes; check the CHECK lines / review images
python $S/scripts/run.py https://example.com --from review       # score, validate, write up, report
```

Results land in `./ap-work/<slug>/report/`.

## What is inside

- `SKILL.md` - instructions for the agent (loaded when the skill is used).
- `scripts/` - `run.py` (whole pipeline), `capture.py`, `review.py`, `score.py`, `analyze.py`, `narrate.py`, `report.py`, `preview.py`, `benchmark.py`, `setup.py`, `install.py`.
- `references/` - step-by-step workflow, writing guide, troubleshooting, benchmark summary (ranges per approach, how pages were chosen, all 150 pages).
- `data/benchmark.json` - 150 pages × 2 devices: element boxes, areas, Composite/Speed/Reach/Hold shares at 3/6/10 s, hero texts, page stats. Captured 2026-11-13 and 2026-11-16. Benchmark AOI-report links open only for the workspace that scored them.
- `assets/benchmark/` - screenshots and heatmap grids of those pages.
- `templates/` - example analysis and box corrections.

Pages you analyse can be added to your own copy of the benchmark with `scripts/benchmark.py add` (stored in `~/.attention-benchmark/`); the bundled data is never changed. All results are model predictions of attention, not measured eye tracking or conversion data.

## Licence

Scripts and instructions: MIT (`LICENSE`). Benchmark data, screenshots and heatmaps: see `DATA-NOTICE.md`.
