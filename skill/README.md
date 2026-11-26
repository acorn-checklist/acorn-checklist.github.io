# ACORN agent skill

This folder lets an AI coding agent fill in the ACORN checklist for your project, asking you only for what it cannot find out itself.

## Use it with any agent

Copy the `acorn/` folder into your project and tell your agent:

> Read `acorn/SKILL.md` and follow it to fill in the ACORN report for this project.

It writes three files: `acorn-report.yaml` (machine-readable), `acorn-report.md` (for your supplementary material) and `acorn-disclosure.md`, which has ready-to-paste Methods, Acknowledgements and availability wording filled in from your report, and a check against the AI policies of the major publishers and of the journal you plan to submit to. Tell the agent your target journal to get that check. If you already have a report and only want the wording, tell your agent:

> Read `acorn/SKILL.md`, then draft the Methods and Acknowledgements wording from `acorn-report.yaml`.

## Install it as a skill

If your agent supports the Agent Skills format (a folder containing a `SKILL.md` file), copy the `acorn/` folder into the agent's skills directory. For example, for Claude Code use `.claude/skills/acorn/` in your project, or `~/.claude/skills/acorn/` for all projects. Check your agent's documentation for its skills directory. The agent then uses the skill when you ask it to report or document its use of AI.

## Tip: start logging at the beginning of a project

Ask your agent at the start of a project to "keep an ACORN log". It will record decisions, ideas, alternative analyses and errors in `ACORN_LOG.md` as you work, which makes the final report far more complete.

## For maintainers

`acorn/checklist.yaml` and `acorn/answers-template.yaml` are generated from `checklist/checklist.yaml`. After changing the checklist, run `python scripts/build_skill.py`.
