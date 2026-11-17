#!/usr/bin/env python3
"""Install this skill for one or more AI agents by copying the folder to where each agent looks for skills.

  python scripts/install.py --list                       # show targets and whether each agent seems to be installed
  python scripts/install.py --agent agents claude         # ~/.agents/skills (Codex, Cursor, Gemini CLI, OpenCode) + Claude Code
  python scripts/install.py --agent all                   # every target below
  python scripts/install.py --agent hermes                # Hermes Agent
  python scripts/install.py --project /path/to/repo       # project-level: <repo>/.agents/skills and <repo>/.claude/skills
  python scripts/install.py --dest /some/skills/dir       # any other agent: a folder its skill loader scans
  add --setup to install the Python dependencies afterwards (same as scripts/setup.py)

Copies are plain folders (no symlinks), so they work on every OS. Re-running replaces the earlier copy; your own
benchmark additions live in ~/.attention-benchmark/ and are never touched.
"""
import argparse, shutil, subprocess, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
NAME = SKILL.name
H = Path.home()
TARGETS = {  # agent -> (skills folder, how we guess the agent is present, note)
    "agents": (H / ".agents" / "skills", H / ".agents", "shared folder read by OpenAI Codex, Cursor, Gemini CLI and OpenCode"),
    "claude": (H / ".claude" / "skills", H / ".claude", "Claude Code (CLI, desktop app Code tab, IDE extensions)"),
    "hermes": (H / ".hermes" / "skills" / "marketing", H / ".hermes", "Hermes Agent (skills are grouped in category folders)"),
    "cursor": (H / ".cursor" / "skills", H / ".cursor", "Cursor (also reads ~/.agents/skills)"),
    "gemini": (H / ".gemini" / "skills", H / ".gemini", "Gemini CLI (also reads ~/.agents/skills)"),
    "opencode": (H / ".config" / "opencode" / "skills", H / ".config" / "opencode", "OpenCode (also reads ~/.agents/skills)"),
}
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "ap-work", ".DS_Store")


def copy_to(parent):
    parent = Path(parent).expanduser(); dst = parent / NAME
    if dst.resolve() == SKILL:
        print(f"  {dst}: this is the source folder - skipped"); return
    parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(SKILL, dst, ignore=IGNORE)
    print(f"  installed -> {dst}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", nargs="*", default=[], help="agents | claude | hermes | cursor | gemini | opencode | codex | all | detected")
    ap.add_argument("--project", help="repository folder for project-level install"); ap.add_argument("--dest", action="append", default=[])
    ap.add_argument("--list", action="store_true"); ap.add_argument("--setup", action="store_true")
    a = ap.parse_args()
    if a.list or not (a.agent or a.project or a.dest):
        print(f"Skill: {NAME}  (source {SKILL})\n")
        for k, (p, probe, note) in TARGETS.items():
            print(f"  {k:9} {str(p):55} {'found' if probe.exists() else '-':6} {note}")
        print("\n  codex = agents. Any other agent that reads Agent Skills (SKILL.md folders): --dest <its skills folder>.")
        print("  Agents without skill support: tell the agent to read SKILL.md in this folder and follow it.")
        if not (a.agent or a.project or a.dest):
            print("\nNothing installed - choose --agent, --project or --dest.")
        return
    agents = set()
    for x in a.agent:
        x = x.lower()
        if x == "all":
            agents |= set(TARGETS)
        elif x == "detected":
            agents |= {k for k, (_, probe, _) in TARGETS.items() if probe.exists()} | {"agents"}
        elif x == "codex":
            agents.add("agents")
        elif x in TARGETS:
            agents.add(x)
        else:
            raise SystemExit(f"unknown agent '{x}' - use one of: {', '.join(TARGETS)}, codex, all, detected (or --dest PATH)")
    print(f"Installing {NAME}:")
    for k in sorted(agents):
        copy_to(TARGETS[k][0])
    if a.project:
        for sub in (".agents/skills", ".claude/skills"):
            copy_to(Path(a.project) / sub)
    for d in a.dest:
        copy_to(d)
    if "hermes" in agents:
        print("  Hermes: make the token visible to the agent - add ATTENTION_PREDICTOR_API_TOKEN to ~/.hermes/.env, or list it under "
              "terminal.env_passthrough in ~/.hermes/config.yaml.")
    if a.setup:
        subprocess.call([sys.executable, str(SKILL / "scripts" / "setup.py")])
    else:
        print(f"\nNext: python {SKILL / 'scripts' / 'setup.py'}   (Python packages + Chromium + token check), then restart the agent.")


if __name__ == "__main__":
    main()
