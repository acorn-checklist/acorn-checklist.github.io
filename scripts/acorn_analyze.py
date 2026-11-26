"""Turn many filled ACORN reports into tables for quantitative and qualitative analysis.

Usage:
    python scripts/acorn_analyze.py REPORT_OR_FOLDER [...] --out OUTPUT_FOLDER

Reads acorn-report.yaml or .json files (folders are searched recursively), checks each one
against the JSON Schema for the checklist version it declares, and writes:

    reports_wide.csv   one row per report, one column per variable (see codebook.csv)
    table_rows.csv     one row per entry of a variable-length table (A1, C2, D1, E1, E3), long format
    texts.csv          every free-text answer, one per row, ready for qualitative coding
    codebook.csv       the variables in reports_wide.csv, across all versions present
    validation.csv     schema problems found in each report (empty if none)

Reports made with different checklist versions can be combined: each is read with the
checklist of its own version (from checklist/versions/), and variables that did not exist in a
version are left empty.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acorn_data import ROOT, flatten, load_checklist, report_schema, variables  # noqa: E402

try:
    import jsonschema
except ImportError:  # validation is skipped, with a warning
    jsonschema = None


def checklist_for(version, cache):
    if version in cache:
        return cache[version]
    candidates = [ROOT / "checklist" / "versions" / version / "checklist.yaml", ROOT / "checklist" / "checklist.yaml"]
    data = None
    for path in candidates:
        if path.exists():
            d = load_checklist(path)
            if d["meta"]["version"] == version:
                data = d
                break
    cache[version] = data
    return data


def find_reports(paths):
    for p in map(Path, paths):
        if p.is_dir():
            yield from sorted(f for f in p.rglob("*") if f.suffix in (".yaml", ".yml", ".json") and "acorn" in f.name.lower())
        else:
            yield p


def read_report(path):
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--strict", action="store_true", help="exit with an error if any report has validation problems")
    ap.add_argument("--allow-todo", action="store_true", help="do not count unresolved TODOs as problems for --strict")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if jsonschema is None:
        print("warning: jsonschema is not installed, so reports are not validated (pip install jsonschema)")

    cache, wide_rows, table_rows, texts, problems = {}, [], [], [], []
    codebook, table_columns = {}, ["report_id", "item_id", "row"]
    for n, path in enumerate(find_reports(args.inputs), start=1):
        try:
            report = read_report(path)
        except Exception as exc:  # unreadable file
            problems.append({"file": str(path), "problem": f"could not read: {exc}"})
            continue
        version = str(report.get("acorn_version", ""))
        data = checklist_for(version, cache)
        if data is None:
            problems.append({"file": str(path), "problem": f"unknown ACORN version '{version}'"})
            continue
        if jsonschema is not None:
            validator = jsonschema.Draft202012Validator(report_schema(data))
            for err in validator.iter_errors(report):
                where = "/".join(str(p) for p in err.absolute_path)
                problems.append({"file": str(path), "problem": f"{where}: {err.message}"})
        for iid, entry in (report.get("answers") or {}).items():
            if isinstance(entry, dict) and entry.get("todo"):
                problems.append({"file": str(path), "problem": f"answers/{iid}: unresolved TODO: {entry['todo']}"})
        report.setdefault("report", {})
        if not report["report"].get("report_id"):
            report["report"]["report_id"] = f"{path.stem}-{n}"
        wide, rows, txt = flatten(report, data)
        wide["file"] = str(path)
        wide_rows.append(wide)
        table_rows += rows
        texts += txt
        for v in variables(data):
            codebook.setdefault(v["variable"], v)
        for r in rows:
            table_columns += [k for k in r if k not in table_columns]

    meta_cols = ["report_id", "file", "acorn_version", "doi", "discipline", "report_date"]
    wide_cols = meta_cols + [v for v, c in codebook.items() if c["table"] == "wide"]
    write_csv(out / "reports_wide.csv", wide_rows, wide_cols)
    write_csv(out / "table_rows.csv", table_rows, table_columns)
    write_csv(out / "texts.csv", texts, ["report_id", "item_id", "variable", "row", "text"])
    write_csv(out / "codebook.csv", codebook.values(),
              ["variable", "table", "item_id", "section", "tier", "introduced_in", "label", "measure", "allowed_values"])
    write_csv(out / "validation.csv", problems, ["file", "problem"])
    print(f"{len(wide_rows)} reports, {len(table_rows)} table rows, {len(texts)} text answers, "
          f"{len(problems)} validation problems -> {out}")
    blocking = [p for p in problems if not (args.allow_todo and "unresolved TODO" in p["problem"])]
    return 1 if (args.strict and blocking) else 0


if __name__ == "__main__":
    sys.exit(main())
