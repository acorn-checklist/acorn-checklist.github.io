"""Release a new ACORN version and archive a frozen copy of it.

Usage: python scripts/release.py VERSION [--date YYYY-MM-DD]

1. Sets meta.version and meta.date in checklist/checklist.yaml.
2. Rebuilds the skill, formats, codebook and schema.
3. Copies checklist.yaml, codebook.csv and acorn-report.schema.json into
   checklist/versions/VERSION/ and records their sha256 in checklist/versions/index.yaml.

After running it, add the release notes to CHANGELOG.md, commit, and create a GitHub release
(which Zenodo can turn into a DOI).
"""
import argparse
import datetime as dt
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "checklist" / "checklist.yaml"
ARCHIVE = ROOT / "checklist" / "versions"
FILES = ["checklist.yaml", "codebook.csv", "acorn-report.schema.json"]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()
    if not SEMVER.match(args.version):
        sys.exit("Release versions look like 1.0.0 (no '-draft').")
    index_path = ARCHIVE / "index.yaml"
    index_text = index_path.read_text(encoding="utf-8")
    index = yaml.safe_load(index_text) or {}
    if any(r["version"] == args.version for r in index.get("releases") or []):
        sys.exit(f"Version {args.version} is already archived.")

    text = SRC.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^  version: .*$", f"  version: {args.version}", text, count=1)
    text = re.sub(r"(?m)^  date: .*$", f"  date: {args.date}", text, count=1)
    SRC.write_text(text, encoding="utf-8")
    cff = ROOT / "CITATION.cff"
    if cff.exists():
        c = re.sub(r"(?m)^version: .*$", f"version: {args.version}", cff.read_text(encoding="utf-8"), count=1)
        c = re.sub(r"(?m)^date-released: .*$", f"date-released: {args.date}", c, count=1)
        cff.write_text(c, encoding="utf-8")
    example = ROOT / "examples" / "acorn-report-example.yaml"
    if example.exists():
        ex = re.sub(r"(?m)^acorn_version: .*$", f"acorn_version: {args.version}", example.read_text(encoding="utf-8"), count=1)
        example.write_text(ex, encoding="utf-8")
    for script in ("build_skill.py", "build_formats.py", "validate_checklist.py"):
        subprocess.run([sys.executable, str(ROOT / "scripts" / script)], check=True)

    dest = ARCHIVE / args.version
    dest.mkdir(parents=True)
    hashes = {}
    for name in FILES:
        src = ROOT / "checklist" / name
        shutil.copy2(src, dest / name)
        hashes[name] = sha256(dest / name)
    entry = {"version": args.version, "date": args.date, "sha256": hashes}
    releases = (index.get("releases") or []) + [entry]
    header = "".join(line + "\n" for line in index_text.splitlines() if line.startswith("#"))
    index_path.write_text(header + yaml.safe_dump({"releases": releases}, sort_keys=False), encoding="utf-8")
    print(f"Archived ACORN {args.version} in {dest.relative_to(ROOT)}. Now update CHANGELOG.md and commit.")


if __name__ == "__main__":
    main()
