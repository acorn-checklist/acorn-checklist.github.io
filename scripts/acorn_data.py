"""Shared definitions for analysing ACORN reports.

Defines, for a given checklist version:
- the analysis variables (one row per variable in the codebook),
- the JSON Schema that filled reports (acorn-report.yaml) must follow,
- how a filled report is flattened into analysis tables.

Variable naming: <item>[_<row>][_<field or column>], e.g. A3, A4_read_files,
C1_formal_analysis_level, F3_total_tokens. Items answered with a variable-length
table (e.g. D1, the decision log) are kept in long format, with counts in the wide table
(e.g. D1_n, D1_approved_by_agent_autonomous_n).
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_checklist(path=None):
    path = Path(path) if path else ROOT / "checklist" / "checklist.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def iter_items(data):
    for s in data["sections"]:
        for i in s["items"]:
            yield s, i


def missing_codes(data):
    return [m["value"] for m in data.get("missing_values", [])]


def _option_values(options):
    return [o["value"] if isinstance(o, dict) else o for o in options]


def _field_measure(f):
    if f.get("options"):
        return "categorical", _option_values(f["options"])
    return f.get("value_type", "text"), []


def variables(data):
    """List of codebook rows describing every variable in the wide analysis table."""
    rows = []

    def add(name, item, section, label, measure, values=(), kind="wide"):
        rows.append({
            "variable": name,
            "table": kind,
            "item_id": item["id"],
            "section": section["id"],
            "tier": item["tier"],
            "introduced_in": item.get("introduced_in", ""),
            "label": label,
            "measure": measure,
            "allowed_values": "|".join(str(v) for v in values),
        })

    sources = [o["value"] for o in data["answer_source"]["options"]]
    for s, i in iter_items(data):
        iid, r, t = i["id"], i["response"], i["response"]["type"]
        if t == "single_choice":
            add(iid, i, s, i["title"], "categorical", _option_values(r["options"]))
        elif t == "multi_choice":
            for o in r["options"]:
                add(f"{iid}_{o['value']}", i, s, f"{i['title']}: {o['label']}", "binary", (0, 1))
        elif t in ("record", "location") and "fields" in r:
            for f in r["fields"]:
                measure, values = _field_measure(f)
                add(f"{iid}_{f['name']}", i, s, f"{i['title']}: {f['label']}", measure, values)
        elif t == "table" and "rows" in r:
            for row in r["rows"]:
                for c in r["columns"]:
                    measure, values = _field_measure(c)
                    add(f"{iid}_{row['value']}_{c['name']}", i, s,
                        f"{i['title']}: {row['label']}: {c['label']}", measure, values)
        elif t == "table":
            add(f"{iid}_n", i, s, f"{i['title']}: number of rows", "integer")
            for c in r["columns"]:
                if c.get("options"):
                    for v in _option_values(c["options"]):
                        add(f"{iid}_{c['name']}_{v}_n", i, s,
                            f"{i['title']}: rows where {c['label']} = {v}", "integer")
            for c in r["columns"]:
                measure, values = _field_measure(c)
                add(f"{iid}.{c['name']}", i, s, f"{i['title']}: {c['label']} (one value per row)",
                    measure, values, kind="rows")
        else:  # text, or location without fields
            add(iid, i, s, i["title"], "text")
        if t in ("single_choice", "multi_choice"):
            add(f"{iid}_note", i, s, f"{i['title']}: note", "text")
        add(f"{iid}_source", i, s, f"{i['title']}: who gave the answer", "categorical", sources)
    return rows


# ---------------------------------------------------------------------------
# JSON Schema for filled reports


def _value_schema(measure, values, missing):
    miss = {"enum": missing}
    if measure == "categorical":
        return {"enum": list(values) + missing + [None]}
    if measure == "integer":
        return {"anyOf": [{"type": "integer", "minimum": 0}, miss, {"type": "null"}]}
    if measure == "number":
        return {"anyOf": [{"type": "number", "minimum": 0}, miss, {"type": "null"}]}
    return {"type": ["string", "null"]}


def _fields_schema(fields, missing):
    props = {}
    for f in fields:
        measure, values = _field_measure(f)
        props[f["name"]] = _value_schema(measure, values, missing)
    return {"type": "object", "properties": props, "additionalProperties": False}


def report_schema(data):
    missing = missing_codes(data)
    sources = [o["value"] for o in data["answer_source"]["options"]]
    items = {}
    for _, i in iter_items(data):
        r, t = i["response"], i["response"]["type"]
        if t == "single_choice":
            ans = {"enum": _option_values(r["options"]) + missing + [None]}
        elif t == "multi_choice":
            ans = {"anyOf": [
                {"type": "array", "items": {"enum": _option_values(r["options"])}, "uniqueItems": True},
                {"enum": missing}, {"type": "null"}]}
        elif "fields" in r:
            ans = _fields_schema(r["fields"], missing)
        elif t == "table" and "rows" in r:
            ans = {"type": "object",
                   "properties": {row["value"]: _fields_schema(r["columns"], missing) for row in r["rows"]},
                   "additionalProperties": False}
        elif t == "table":
            ans = {"anyOf": [{"type": "array", "items": _fields_schema(r["columns"], missing)},
                             {"enum": missing}, {"type": "null"}]}
        else:
            ans = {"type": ["string", "null"]}
        items[i["id"]] = {
            "type": "object",
            "title": f"{i['id']}. {i['title']}",
            "properties": {
                "title": {"type": "string"},
                "answer": ans,
                "source": {"enum": sources + [None]},
                "note": {"type": ["string", "null"]},
                "todo": {"type": ["string", "null"],
                         "description": "What a human still has to approve or provide. Must be empty in a final report."},
            },
            "required": ["answer", "source"],
            "additionalProperties": False,
        }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"ACORN report, checklist version {data['meta']['version']}",
        "type": "object",
        "required": ["acorn_version", "report", "answers"],
        "properties": {
            "acorn_version": {"type": "string"},
            "report": {
                "type": "object",
                "properties": {
                    "report_id": {"type": ["string", "null"], "description": "Unique ID, e.g. the paper DOI or a UUID"},
                    "title": {"type": ["string", "null"]},
                    "authors": {"type": ["string", "null"]},
                    "doi": {"type": ["string", "null"], "description": "DOI of the paper or preprint, once known"},
                    "discipline": {"type": ["string", "null"], "description": "Main research field, e.g. psychology, physics"},
                    "report_date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
                },
                "additionalProperties": False,
            },
            "answers": {"type": "object", "properties": items, "additionalProperties": False},
        },
        "additionalProperties": False,
    }


def blank_report(data):
    """A blank report with the structure the schema expects."""
    answers = {}
    for _, i in iter_items(data):
        r, t = i["response"], i["response"]["type"]
        if t == "table" and "rows" in r:
            ans = {row["value"]: {c["name"]: None for c in r["columns"]} for row in r["rows"]}
        elif t in ("table", "multi_choice"):
            ans = []
        elif "fields" in r:
            ans = {f["name"]: None for f in r["fields"]}
        else:
            ans = None
        answers[i["id"]] = {"title": i["title"], "answer": ans, "source": None, "note": None, "todo": None}
    return {
        "acorn_version": data["meta"]["version"],
        "report": {"report_id": None, "title": None, "authors": None, "doi": None,
                   "discipline": None, "report_date": None},
        "answers": answers,
    }


# ---------------------------------------------------------------------------
# Flattening filled reports


def flatten(report, data):
    """Return (wide, rows, texts) for one report.

    wide:  dict variable -> value (one row of the wide table)
    rows:  list of dicts for variable-length tables (long format)
    texts: list of dicts for every non-empty free-text value (for qualitative coding)
    """
    rid = report.get("report", {}).get("report_id") or ""
    wide = {"report_id": rid, "acorn_version": report.get("acorn_version", "")}
    for k in ("doi", "discipline", "report_date"):
        wide[k] = (report.get("report") or {}).get(k)
    rows, texts = [], []
    answers = report.get("answers") or {}
    codebook = {v["variable"]: v for v in variables(data)}

    def put(var, value):
        wide[var] = value
        if codebook.get(var, {}).get("measure") == "text" and value not in (None, ""):
            texts.append({"report_id": rid, "variable": var, "item_id": codebook[var]["item_id"], "text": value})

    for _, i in iter_items(data):
        iid, r, t = i["id"], i["response"], i["response"]["type"]
        entry = answers.get(iid) or {}
        ans = entry.get("answer")
        put(f"{iid}_source", entry.get("source"))
        if t == "single_choice":
            put(iid, ans)
        elif t == "multi_choice":
            chosen = ans if isinstance(ans, list) else []
            for o in r["options"]:
                put(f"{iid}_{o['value']}", (1 if o["value"] in chosen else 0) if isinstance(ans, list) else ans)
        elif "fields" in r:
            ans = ans if isinstance(ans, dict) else {}
            for f in r["fields"]:
                put(f"{iid}_{f['name']}", ans.get(f["name"]))
        elif t == "table" and "rows" in r:
            ans = ans if isinstance(ans, dict) else {}
            for row in r["rows"]:
                cells = ans.get(row["value"]) or {}
                for c in r["columns"]:
                    put(f"{iid}_{row['value']}_{c['name']}", cells.get(c["name"]))
        elif t == "table":
            table = ans if isinstance(ans, list) else []
            wide[f"{iid}_n"] = len(table) if isinstance(ans, list) else ans
            for c in r["columns"]:
                for v in _option_values(c.get("options", [])):
                    wide[f"{iid}_{c['name']}_{v}_n"] = sum(1 for row in table if (row or {}).get(c["name"]) == v)
            for n, row in enumerate(table, start=1):
                row = row or {}
                rows.append({"report_id": rid, "item_id": iid, "row": n,
                             **{c["name"]: row.get(c["name"]) for c in r["columns"]}})
                for c in r["columns"]:
                    val = row.get(c["name"])
                    if not c.get("options") and c.get("value_type", "text") == "text" and val not in (None, ""):
                        texts.append({"report_id": rid, "variable": f"{iid}.{c['name']}", "item_id": iid,
                                      "row": n, "text": val})
        else:
            put(iid, ans)
        if t in ("single_choice", "multi_choice"):
            put(f"{iid}_note", entry.get("note"))
        elif entry.get("note"):
            texts.append({"report_id": rid, "variable": f"{iid}_note", "item_id": iid, "text": entry["note"]})
    return wide, rows, texts


# ---------------------------------------------------------------------------
# Comparing versions


def diff_versions(old, new):
    """Item-level differences between two checklist versions.

    Returns a dict with lists of item IDs: added, removed, changed (what is asked or how it is
    answered changed, so answers are not directly comparable), reworded (only title, guidance or
    agent instructions changed, so answers remain comparable).
    """
    o = {i["id"]: i for _, i in iter_items(old)}
    n = {i["id"]: i for _, i in iter_items(new)}
    out = {"added": [], "removed": [], "changed": [], "reworded": []}
    for iid in n:
        if iid not in o:
            out["added"].append(iid)
        elif (o[iid]["question"], o[iid]["response"], o[iid]["tier"]) != (n[iid]["question"], n[iid]["response"], n[iid]["tier"]):
            out["changed"].append(iid)
        elif (o[iid]["title"], o[iid]["guidance"], o[iid]["agent_instructions"]) != (
                n[iid]["title"], n[iid]["guidance"], n[iid]["agent_instructions"]):
            out["reworded"].append(iid)
    out["removed"] = [iid for iid in o if iid not in n]
    return out
