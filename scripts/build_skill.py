"""Sync the agent skill with the checklist source.

Copies checklist/checklist.yaml, the publisher policy table and the report schema into skill/acorn/ and regenerates
skill/acorn/answers-template.yaml. Run with --check to verify the skill is up to date
without changing files (exit code 1 if it is stale).
"""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acorn_data import blank_report, load_checklist, report_schema  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "checklist" / "checklist.yaml"
SKILL = ROOT / "skill" / "acorn"


def template_text(data):
    header = (
        f"# ACORN report. Checklist version {data['meta']['version']}.\n"
        "# Fill in each item using the option codes (the 'value' entries in checklist.yaml), not their labels.\n"
        "# 'source' is one of: agent, human, agent_verified, unknown.\n"
        "# 'todo': what a human still has to approve or provide (shown in red in acorn-report.md). Empty when final.\n"
        "# For a missing answer use a missing-value code: unknown, not_applicable, not_disclosed, not_available.\n"
        "# The file must validate against acorn-report.schema.json in this folder.\n"
    )
    return header + yaml.safe_dump(blank_report(data), sort_keys=False, allow_unicode=True, width=100)


def main(check: bool) -> int:
    data = load_checklist(SRC)
    expected = {
        SKILL / "checklist.yaml": SRC.read_text(encoding="utf-8"),
        SKILL / "publisher-policies.yaml": (ROOT / "checklist" / "publisher-policies.yaml").read_text(encoding="utf-8"),
        SKILL / "answers-template.yaml": template_text(data),
        SKILL / "acorn-report.schema.json": json.dumps(report_schema(data), indent=2) + "\n",
        SKILL / "render_report.py": (ROOT / "scripts" / "render_report.py").read_text(encoding="utf-8"),
    }
    stale = [p for p, text in expected.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if check:
        for p in stale:
            print(f"STALE {p.relative_to(ROOT)}: run python scripts/build_skill.py")
        return 1 if stale else 0
    SKILL.mkdir(parents=True, exist_ok=True)
    for p, text in expected.items():
        p.write_text(text, encoding="utf-8")
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
