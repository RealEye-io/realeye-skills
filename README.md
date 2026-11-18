# RealEye skills

Agent skills for [RealEye](https://www.realeye.io) products. Each skill is a self-contained folder in [`skills/`](skills) that follows the open [Agent Skills](https://agentskills.io/specification) format, so it works with Claude Code, OpenAI Codex, Cursor, Gemini CLI, OpenCode, Hermes Agent and any other agent that can read a `SKILL.md` and run shell commands.

Install only the skills you need - every skill can be installed on its own.

## Skills

| Skill | What it does | Needs |
|---|---|---|
| [attention-predictor-landing-page-benchmark](skills/attention-predictor-landing-page-benchmark) | Analyses a landing page's first screen with the RealEye Attention Predictor and validates it against 150 SaaS landing pages (100 top, 25 average, 25 poorly made). Finds blind spots and gives target ranges and guidelines in a PDF report. | Attention Predictor API token, Python 3.9+ |

## Install one skill

Replace `SKILL` with the skill's folder name from the table, e.g. `attention-predictor-landing-page-benchmark`.

**Any agent, with the [skills CLI](https://github.com/vercel-labs/skills)** (detects the agents you have and asks where to install):

```bash
npx skills add RealEye-io/realeye-skills --skill SKILL
```

Add `-g` to install for all your projects, `-a <agent>` to pick the agent (for example `-a claude-code`, `-a codex`, `-a cursor`, `-a opencode`).

**Claude Code** - this repository is a plugin marketplace with one plugin per skill:

```
/plugin marketplace add RealEye-io/realeye-skills
/plugin install SKILL@realeye-skills
```

**Hermes Agent:**

```bash
hermes skills install RealEye-io/realeye-skills/skills/SKILL
```

**By hand (any agent)** - download just that folder, then copy it to the agent's skills folder. Skills that ship an installer can do the copying:

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/RealEye-io/realeye-skills.git
cd realeye-skills
git sparse-checkout set skills/SKILL
python skills/SKILL/scripts/install.py --list          # if the skill has an installer: shows targets
python skills/SKILL/scripts/install.py --agent detected --setup
```

Where agents look for skills: `~/.agents/skills/` (Codex, Cursor, Gemini CLI, OpenCode), `~/.claude/skills/` (Claude Code), `~/.hermes/skills/<category>/` (Hermes). Restart the agent after installing.

Each skill's own README covers setup, tokens and usage.

## Adding a skill

1. Create `skills/<skill-name>/SKILL.md` with `name` (equal to the folder name) and `description` frontmatter; keep the frontmatter to the open standard fields (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`).
2. Add a `README.md` for people and, if the skill bundles data, a `DATA-NOTICE.md`.
3. Add a plugin entry for it in [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json).
4. Validate: `skills-ref validate skills/<skill-name>` (install with `pip install "git+https://github.com/agentskills/agentskills#subdirectory=skills-ref"`). The CI workflow runs the same check on every push and pull request.

## Licence

Code and instructions: [MIT](LICENSE). Data bundled with a skill (benchmarks, screenshots, heatmaps) is covered by that skill's `DATA-NOTICE.md`.
