# ACORN: AI CO-scientist Reporting Norms

ACORN is a reporting checklist for research that used AI coding agents. It records which agent was used, what it did, who made each decision, and how the work can be reproduced. It is designed for any empirical or formal discipline, and so that the coding agent itself can fill in most of it.

**Status:** version 0.1.0, released 26 November 2026.

## Repository layout

- `checklist/checklist.yaml`: the single source of the checklist. All other formats (LaTeX, RMarkdown, Word, website, agent skill) are generated from it. Its `disclosure` block holds the ready-to-paste Methods, Acknowledgements and availability wording that appears in every format, on the website's Cite & disclose page, and in the `acorn-disclosure.md` the skill drafts from a filled report.
- `checklist/codebook.csv` and `checklist/acorn-report.schema.json`: the analysis codebook and the JSON Schema that completed reports follow (generated).
- `checklist/versions/`: frozen copies of every released version. Create a release with `python scripts/release.py <version>`.
- `scripts/acorn_analyze.py`: turns many completed reports into tables for quantitative and qualitative analysis.
- `examples/`: a fictional completed report.
- `formats/`: fillable Word, LaTeX and R Markdown versions, generated from the source file.
- `site/` and `scripts/build_site.py`: the website, built from the source file into `_site/` and published by GitHub Actions (`.github/workflows/pages.yml`) once the repository is public.
- `skill/`: the agent skill. A coding agent can use it to fill in the checklist for a project. See `skill/README.md`.
- `scripts/validate_checklist.py`: checks the source file (unique IDs, required fields). Run `python scripts/validate_checklist.py`.
- `scripts/build_skill.py`: copies the checklist into the skill and regenerates the blank answer file. Run it after changing the checklist; `--check` verifies the skill is up to date.
- `scripts/build_formats.py`: regenerates the Word, LaTeX and R Markdown versions. Run it after changing the checklist; `--check` verifies they are up to date.

Install the script dependencies with `pip install -r requirements.txt`. GitHub Actions runs these checks and a test build of the website on every push.

## Disclosing ACORN in a paper

Short version for the Acknowledgements:

> AI tools were used in this work and are reported in the ACORN checklist (v0.1.0): [URL/DOI].

The Methods and full Acknowledgements wording, with fill-in fields and copy buttons, is on the website's Cite & disclose page. The agent skill drafts it for you from your completed report. Deposit the completed report under a persistent DOI (Zenodo or OSF) and cite the ACORN version you used.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to propose changes and how decisions are made.

## Related work

Builds on and is compatible with GUIDE-LLM (Feuerriegel et al., 2026, *Nature Human Behaviour*, doi:10.1038/s41562-026-02492-7), which covers LLMs used as research tools. This checklist covers AI coding agents acting as research assistants.
