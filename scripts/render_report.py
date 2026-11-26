"""Render a filled acorn-report.yaml as readable Markdown (acorn-report.md), and draft
ready-to-paste disclosure wording for the manuscript (acorn-disclosure.md).

Usage: python render_report.py acorn-report.yaml checklist.yaml [acorn-report.md]

acorn-disclosure.md is written next to acorn-report.md. It contains the Methods,
Acknowledgements and availability wording from checklist.yaml, filled in from the report.

Anything that still needs human approval (an answer's `todo` field, or an unknown answer)
is shown as a red TODO marker, and listed at the top of the report.
"""
import re
import sys
from pathlib import Path

import yaml

MISSING = {"unknown", "not_applicable", "not_disclosed", "not_available"}


def todo_html(text):
    # The red colour shows in HTML, R Markdown, pandoc and most Markdown previews;
    # the red circle and the word TODO stay visible where colour is stripped (e.g. GitHub).
    return f'<span style="color:#d00000">🔴 <strong>TODO (needs human approval):</strong> {text}</span>'


def label(options, value):
    for o in options or []:
        if isinstance(o, dict) and o["value"] == value:
            return o["label"]
    if value is None:
        return ""
    return str(value).replace("_", " ") if (value in MISSING or options) else str(value)


def cell(x):
    return "" if x is None else str(x).replace("|", "\\|").replace("\n", " ")


def render(report, checklist):
    sources = {o["value"]: o["label"].split(" (")[0] for o in checklist["answer_source"]["options"]}
    answers = report.get("answers") or {}
    meta = report.get("report") or {}

    todos = []
    for s in checklist["sections"]:
        for i in s["items"]:
            e = answers.get(i["id"]) or {}
            if e.get("todo"):
                todos.append((i, e["todo"]))
            elif e.get("source") in (None, "unknown"):
                todos.append((i, "No answer yet: please provide one."))

    out = [f"# ACORN report: {meta.get('title') or ''}", "",
           f"Reported using ACORN v{report.get('acorn_version')} (AI CO-scientist Reporting Norms).", ""]
    names = {"authors": "Authors", "discipline": "Discipline", "doi": "DOI", "report_date": "Report date"}
    details = [f"**{n}:** {meta[k]}" for k, n in names.items() if meta.get(k) and meta[k] not in MISSING]
    if details:
        out += [" · ".join(details), ""]
    if todos:
        out += [todo_html(f"{len(todos)} item(s) need human approval before this report is final:"), ""]
        out += [f"{n}. [{i['id']}. {i['title']}](#{i['id'].lower()}-{i['title'].lower().replace(' ', '-').replace(',', '')}): {t}" for n, (i, t) in enumerate(todos, 1)]
        out.append("")

    for s in checklist["sections"]:
        out += [f"## {s['id']}. {s['title']}", ""]
        for i in s["items"]:
            e = answers.get(i["id"]) or {}
            ans, resp = e.get("answer"), i["response"]
            t = resp["type"]
            out += [f"### {i['id']}. {i['title']}", ""]
            if isinstance(ans, str) and ans in MISSING:
                out.append(label([], ans).capitalize())
            elif t == "single_choice":
                out.append(label(resp["options"], ans))
            elif t == "multi_choice":
                out.append("; ".join(label(resp["options"], v) for v in ans or []) or "None")
            elif "fields" in resp:
                ans = ans or {}
                out += ["| Field | Answer |", "|---|---|"]
                out += [f"| {cell(f['label'])} | {cell(label(f.get('options'), ans.get(f['name'])))} |" for f in resp["fields"]]
            elif t == "table" and "rows" in resp:
                ans, cols = ans or {}, resp["columns"]
                out += ["| Role | " + " | ".join(c["label"] for c in cols) + " |", "|---|" + "---|" * len(cols)]
                for row in resp["rows"]:
                    v = ans.get(row["value"]) or {}
                    out.append(f"| {row['label']} | " + " | ".join(cell(label(c.get('options'), v.get(c['name']))) for c in cols) + " |")
            elif t == "table":
                cols = resp["columns"]
                if ans:
                    out += ["| " + " | ".join(c["label"].split(" (")[0] for c in cols) + " |", "|" + "---|" * len(cols)]
                    for row in ans:
                        out.append("| " + " | ".join(cell(label(c.get('options'), (row or {}).get(c['name']))) for c in cols) + " |")
                else:
                    out.append("None reported.")
            else:
                out.append(cell(ans) if ans is not None else "")
            out += ["", f"*Answered by:* {sources.get(e.get('source'), 'not yet answered')}"]
            if e.get("note"):
                out += ["", f"*Note:* {e['note']}"]
            if e.get("todo"):
                out += ["", todo_html(e["todo"])]
            elif e.get("source") in (None, "unknown"):
                out += ["", todo_html("No answer yet: please provide one.")]
            out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Disclosure wording (Methods, Acknowledgements, availability statement)

SUPERVISION = {
    "0": "The agent only suggested code or text; the authors ran every step themselves.",
    "1": "The authors approved each action of the agent before it ran.",
    "2": "The agent acted within its default permissions, and the authors approved risky actions.",
    "3": "The agent ran largely unattended, or with its permission checks skipped.",
}
TASKS = {
    "conceptualization": "developing research questions and hypotheses",
    "literature": "literature search",
    "methodology": "study design and analysis planning",
    "data_curation": "data cleaning and preparation",
    "formal_analysis": "statistical analysis",
    "derivation": "derivations and proofs",
    "simulation": "simulation and computational modelling",
    "software": "writing code",
    "validation": "testing and checking results",
    "visualization": "creating figures and tables",
    "writing_draft": "drafting text for the manuscript",
    "writing_review": "editing the manuscript text",
    "references": "compiling references",
    "other": "other tasks",
}
WRITING_ROLES = {"writing_draft", "writing_review", "references"}
OTHER_WRITING = {"language_editing": "editing the language", "drafting_text": "drafting text", "translation": "translation",
                 "data_formatting": "formatting the reported data", "code_formatting": "formatting the reported code",
                 "reference_gathering": "gathering references"}
FIGURE_PURPOSES = {"illustrative_figures", "data_visualisation"}
CHECKS = {
    "read_line_by_line": "reading the code line by line",
    "rerun_independently": "re-running analyses independently",
    "tests": "running automated tests",
    "manual_calculation": "checking results by hand",
    "spot_check": "spot-checking",
}
LINK = re.compile(r"(https?://\S+|\b10\.\d{4,9}/\S+)")


def _ok(v):
    return v is not None and str(v).strip() != "" and v not in MISSING


def _join(parts):
    parts = [p for p in parts if p]
    if len(parts) <= 2:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _answer(report, iid):
    return ((report.get("answers") or {}).get(iid) or {}).get("answer")


def disclosure_values(report):
    """Fill the disclosure placeholders from a report. Values that cannot be filled are None."""
    vals = {}
    models = []
    for row in _answer(report, "A1") or []:
        row = row or {}
        name, vid, prov = (row.get(k) for k in ("model_name", "version_id", "provider"))
        if not (_ok(name) or _ok(vid)):
            continue
        main = name if _ok(name) else vid
        extra = [x for x in (vid if _ok(name) and _ok(vid) and vid != name else None, prov) if _ok(x)]
        models.append(main + (f" ({', '.join(extra)})" if extra else ""))
    a2 = _answer(report, "A2")
    product = a2.get("agent_product") if isinstance(a2, dict) else None
    if models:
        vals["agents"] = f"{product} with {_join(models)}" if _ok(product) else _join(models)
    elif _ok(product):
        vals["agents"] = f"{product} with [model name and exact version]"
    else:
        vals["agents"] = None

    c1 = _answer(report, "C1")
    tasks, research, writing = [], [], []
    if isinstance(c1, dict):
        for role, phrase in TASKS.items():
            if (c1.get(role) or {}).get("level") in ("led", "assisted"):
                tasks.append(phrase)
                (writing if role in WRITING_ROLES else research).append(phrase)
    vals["tasks"] = _join(tasks) or None
    vals["research_tasks"] = _join(research) or None

    # Other AI tools (A7): writing help and figures.
    a7 = _answer(report, "A7")
    a7 = [r or {} for r in a7] if isinstance(a7, list) else []

    def tool_name(r):
        name = r.get("tool")
        if not _ok(name):
            return None
        extra = [x for x in (r.get("version_id"), r.get("provider")) if _ok(x) and x != name]
        return name + (f" ({', '.join(extra)})" if extra else "")

    writing_tools = [vals["agents"] or "the AI coding agent"] if writing else []
    for r in a7:
        if r.get("purpose") in OTHER_WRITING:
            if tool_name(r) and tool_name(r) not in writing_tools:
                writing_tools.append(tool_name(r))
            phrase = OTHER_WRITING[r["purpose"]] + (f" ({r['where_used']})" if _ok(r.get("where_used")) else "")
            writing.append(phrase)
    vals["writing_tools"] = _join(writing_tools) or None
    vals["writing_tasks"] = _join(writing) or None
    figs = [f"{tool_name(r)}" + (f" ({r['where_used']})" if _ok(r.get("where_used")) else "")
            for r in a7 if r.get("purpose") in FIGURE_PURPOSES and tool_name(r)]
    vals["figure_tools"] = _join(figs) or None

    a3 = _answer(report, "A3")
    vals["supervision"] = SUPERVISION.get(str(a3)) if a3 is not None else None

    rows = [r or {} for r in (_answer(report, "E1") or []) if isinstance(_answer(report, "E1"), list)]
    methods = []
    for r in rows:
        m = CHECKS.get(r.get("method"))
        if m and m not in methods:
            methods.append(m)
    unverified = [str(r.get("output")) for r in rows if r.get("method") == "not_verified" and _ok(r.get("output"))]
    sentences = []
    if methods:
        sentences.append(f"The authors checked the agent's outputs by {_join(methods)}.")
    if unverified:
        sentences.append(f"The following outputs were not independently verified: {_join(unverified)}.")
    vals["verification"] = " ".join(sentences) or None

    f1 = _answer(report, "F1")
    link = LINK.search(str(f1)) if _ok(f1) and isinstance(f1, str) else None
    vals["location"] = link.group(1).rstrip(".,;)") if link else None
    return vals


def fill_template(text, values, version, placeholders):
    """Replace {name} with its value, or with [bracketed placeholder text] where it is missing."""
    def sub(m):
        name = m.group(1)
        if name == "version":
            return str(version)
        v = values.get(name)
        return v if v else f"[{placeholders.get(name, name)}]"
    return re.sub(r"\{(\w+)\}", sub, text)


def render_disclosure(report, checklist):
    d = checklist.get("disclosure")
    if not d:
        return None
    version = report.get("acorn_version") or checklist["meta"]["version"]
    values = disclosure_values(report)
    ph = d.get("placeholders") or {}
    used = [t for t in d["templates"] if not t.get("requires") or values.get(t["requires"])]
    skipped = [t for t in d["templates"] if t not in used]
    needed = []
    for t in used:
        for name in re.findall(r"\{(\w+)\}", t["text"]):
            if name != "version" and name not in needed:
                needed.append(name)
    todos = [f"Fill in: {ph.get(k, k)}." for k in needed if not values.get(k)]
    loc = values.get("location") or ""
    if loc and "doi" not in loc.lower() and not loc.startswith("10."):
        todos.append(f"Replace {loc} with a persistent DOI (e.g. Zenodo or OSF) for the deposited ACORN report.")
    open_items = sum(1 for e in (report.get("answers") or {}).values() if (e or {}).get("todo"))
    if open_items:
        todos.append(f"The report still has {open_items} open TODO(s); re-run this after resolving them, as the wording may change.")
    todos.append("Check your target journal's AI policy and use the pieces it asks for (see the ACORN publisher policy table).")
    title = (report.get("report") or {}).get("title") or ""
    out = [f"# Disclosure wording: {title}", "",
           f"Drafted from the ACORN report (v{version}). Check every sentence against the report, and against your "
           "journal's policy, before you submit. Parts in [square brackets] still need to be filled in.", ""]
    out += [todo_html(f"{len(todos)} thing(s) to do before you use this wording:"), ""]
    out += [f"{n}. {t}" for n, t in enumerate(todos, 1)] + [""]
    for t in used:
        out += [f"## {t['label']}", "", f"*Where:* {' '.join(t['where'].split())}", "",
                "> " + fill_template(" ".join(t["text"].split()), values, version, ph), ""]
    if skipped:
        out += ["## Not needed for this report", ""]
        why = {"writing_tasks": "no AI help with writing or translation (C1 writing roles, A7)",
               "figure_tools": "no AI-generated or AI-edited figures (A7)"}
        out += [f"- {t['label']}: the report records {why.get(t['requires'], 'nothing that needs it')}. If that is wrong, update the report and re-run."
                for t in skipped] + [""]
    if d.get("advice"):
        out += ["## Tips", ""] + [f"- {a}" for a in d["advice"]] + [""]
    return "\n".join(out)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    report = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
    checklist = yaml.safe_load(Path(sys.argv[2]).read_text(encoding="utf-8"))
    target = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(sys.argv[1]).with_suffix(".md")
    target.write_text(render(report, checklist), encoding="utf-8")
    print(f"wrote {target}")
    disclosure = render_disclosure(report, checklist)
    if disclosure:
        dtarget = target.parent / "acorn-disclosure.md"
        dtarget.write_text(disclosure, encoding="utf-8")
        print(f"wrote {dtarget}")


if __name__ == "__main__":
    main()
