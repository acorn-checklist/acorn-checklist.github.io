"""Generate the fillable checklist in LaTeX, R Markdown and Word from checklist/checklist.yaml,
plus the GitHub issue form used for change proposals, the analysis codebook
(checklist/codebook.csv) and the JSON Schema for filled reports (checklist/acorn-report.schema.json).

Usage: python scripts/build_formats.py [--check]

Outputs go to formats/. With --check, nothing is written and the exit code is 1
if any generated file is out of date (the Word file is checked by its text content).
"""
import csv
import io
import json
import sys
from pathlib import Path

import yaml
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from acorn_data import report_schema, variables  # noqa: E402
from render_report import fill_template  # noqa: E402
SRC = ROOT / "checklist" / "checklist.yaml"
OUT = ROOT / "formats"
BLANK_ROWS = 3
BOX = "\u2610"  # ballot box

INTRO = (
    "Use this checklist to report how AI coding agents assisted your research. "
    "Core items should always be reported; optional items when relevant. "
    "For each item, record who provided the answer. "
    "If an answer is missing, say why: unknown, not applicable, not disclosed or not available. "
    "Coding agents can fill in most of this checklist themselves with the ACORN skill."
)


def load():
    return yaml.safe_load(SRC.read_text(encoding="utf-8"))


def source_labels(data):
    return [o["label"] for o in data["answer_source"]["options"]]


# ---------------------------------------------------------------------------
# Neutral description of each item's answer area, shared by all renderers.
# Each block is one of:
#   ("choices", [labels])                     tick boxes
#   ("fields", [(label, [option labels])])    two-column form
#   ("grid", header, [first-column labels])   table with fixed rows
#   ("grid", header, None)                    table with blank rows
#   ("box", None)                             free-text answer box


def nice(value):
    """Display form of an option value, e.g. 'ide_extension' -> 'ide extension'."""
    return str(value).replace("_", " ")


def answer_blocks(item):
    r = item["response"]
    t = r["type"]
    if t in ("single_choice", "multi_choice"):
        return [("choices", [o["label"] for o in r["options"]])]
    if t in ("record", "location") and "fields" in r:
        return [("fields", [(f["label"], [nice(o) for o in f.get("options", [])]) for f in r["fields"]])]
    if t == "location":
        return [("fields", [("Persistent link (DOI, repository, archive)", []), ("Reason if not shared", [])])]
    if t == "table":
        cols = r["columns"]
        if "rows" in r:
            header = ["Role"] + [c["label"] for c in cols]
            return [("grid", header, [row["label"] for row in r["rows"]], cols)]
        return [("grid", [c["label"] for c in cols], None, cols)]
    return [("box", None)]


def option_hint(cols):
    """Footnote-style hints listing allowed values for columns that have options."""
    return [f"{c['label']}: {', '.join(nice(o) for o in c['options'])}" for c in cols if c.get("options")]


def disclosure_blocks(data):
    """The disclosure wording with [bracketed placeholders], or [] for versions without it."""
    d = data.get("disclosure")
    if not d:
        return []
    ph = d.get("placeholders") or {}
    return [(t["label"], t["where"], fill_template(" ".join(t["text"].split()), {}, data["meta"]["version"], ph))
            for t in d["templates"]]


DISCLOSURE_HEADING = "Disclosure wording for your manuscript"


def items(data):
    for s in data["sections"]:
        yield s, None
        for i in s["items"]:
            yield s, i


# ---------------------------------------------------------------------------
# LaTeX


def tex_escape(s):
    rep = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    s = "".join(rep.get(ch, ch) for ch in str(s))
    return s.replace('"', "''")


def render_tex(data):
    m = data["meta"]
    e = tex_escape
    out = [
        r"\documentclass[10pt,a4paper]{article}",
        r"\usepackage[margin=2cm]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{amssymb,array,longtable,tabularx,enumitem,xcolor,titlesec}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\newcommand{\abox}{$\square$}",
        r"\newcommand{\answerline}{\rule{0pt}{2.2em}}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{4pt}",
        r"\titleformat{\subsection}{\normalfont\bfseries}{}{0pt}{}",
        "% Generated from checklist/checklist.yaml by scripts/build_formats.py. Do not edit by hand.",
        r"\begin{document}",
        rf"{{\LARGE\bfseries {e(m['name'])}: {e(m['full_name'])}}}\\[2pt]",
        rf"{{\large Reporting checklist for research assisted by AI coding agents}}\\[2pt]",
        rf"Version {e(m['version'])} ({e(m['date'])})",
        "",
        e(INTRO),
        "",
        r"\textbf{Project title:} \hrulefill\\[4pt]",
        r"\textbf{Authors:} \hrulefill\\[4pt]",
        r"\textbf{Date completed:} \hrulefill",
        "",
    ]
    sources = "\\quad ".join(r"\abox{} " + e(s) for s in source_labels(data))
    for s, i in items(data):
        if i is None:
            out += [rf"\section*{{{e(s['id'])}. {e(s['title'])}}}", rf"\emph{{{e(s['purpose'])}}}", ""]
            continue
        out += [
            rf"\subsection*{{{e(i['id'])}. {e(i['title'])} \normalfont\small({e(i['tier'])})}}",
            rf"\textbf{{{e(i['question'])}}}\\",
            rf"{{\small\color{{darkgray}}\emph{{{e(i['guidance'].strip())}}}}}",
            "",
        ]
        for block in answer_blocks(i):
            kind = block[0]
            if kind == "choices":
                out.append(r"\begin{itemize}[label={},leftmargin=1em,itemsep=0pt]")
                out += [rf"\item \abox{{}} {e(o)}" for o in block[1]]
                out.append(r"\end{itemize}")
                out.append(r"Note: \hrulefill")
            elif kind == "fields":
                out.append(r"\begin{tabularx}{\linewidth}{|>{\raggedright\arraybackslash}p{0.38\linewidth}|X|}\hline")
                for label, opts in block[1]:
                    cell = "\\enspace ".join(r"\abox{} " + e(o) for o in opts) if opts else r"\answerline"
                    out.append(rf"{e(label)} & {cell} \\ \hline")
                out.append(r"\end{tabularx}")
            elif kind == "grid":
                _, header, rows, cols = block
                n = len(header)
                spec = "|" + "|".join([r">{\raggedright\arraybackslash}X"] * n) + "|"
                out.append(rf"{{\small\begin{{tabularx}}{{\linewidth}}{{{spec}}}\hline")
                out.append(" & ".join(rf"\textbf{{{e(h)}}}" for h in header) + r" \\ \hline")
                body_rows = rows if rows is not None else [None] * BLANK_ROWS
                for row in body_rows:
                    cells = ([e(row)] + [""] * (n - 1)) if row is not None else [r"\answerline"] + [""] * (n - 1)
                    out.append(" & ".join(cells) + r" \\ \hline")
                out.append(r"\end{tabularx}}")
                for hint in option_hint(cols):
                    out.append(rf"{{\footnotesize {e(hint)}}}\\")
            else:
                out.append(r"\fbox{\parbox{\dimexpr\linewidth-2\fboxsep-2\fboxrule}{\rule{0pt}{4em}}}")
        out += ["", rf"{{\small Answered by: {sources}}}", ""]
    if disclosure_blocks(data):
        d = data["disclosure"]
        out += [r"\clearpage", rf"\section*{{{e(DISCLOSURE_HEADING)}}}", e(" ".join(d["intro"].split())), ""]
        for label, where, text in disclosure_blocks(data):
            out += [rf"\subsection*{{{e(label)}}}", rf"{{\small\emph{{Where: {e(where)}}}}}",
                    r"\begin{quote}", e(text), r"\end{quote}", ""]
        out.append(r"\textbf{Tips}")
        out.append(r"\begin{itemize}[itemsep=0pt]")
        out += [rf"\item {e(a)}" for a in d.get("advice", [])]
        out += [r"\end{itemize}", ""]
    out += [r"\end{document}", ""]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# R Markdown


def md_cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def render_rmd(data):
    m = data["meta"]
    out = [
        "---",
        f'title: "{m["name"]}: {m["full_name"]}"',
        f'subtitle: "Reporting checklist for research assisted by AI coding agents, version {m["version"]}"',
        "output:",
        "  html_document: default",
        "  word_document: default",
        "  pdf_document: default",
        "---",
        "",
        "<!-- Generated from checklist/checklist.yaml by scripts/build_formats.py. Do not edit by hand. -->",
        "<!-- Fill in each 'Answer' and tick one 'Answered by' box: replace [ ] with [x]. -->",
        "",
        INTRO,
        "",
        "**Project title:** ",
        "",
        "**Authors:** ",
        "",
        "**Date completed:** ",
        "",
    ]
    sources = " ".join(f"[ ] {s}" for s in source_labels(data))
    for s, i in items(data):
        if i is None:
            out += [f"# {s['id']}. {s['title']}", "", f"*{s['purpose']}*", ""]
            continue
        out += [
            f"## {i['id']}. {i['title']} ({i['tier']})",
            "",
            f"**{i['question']}**",
            "",
            f"*Guidance:* {i['guidance'].strip()}",
            "",
        ]
        for block in answer_blocks(i):
            kind = block[0]
            if kind == "choices":
                out += [f"- [ ] {o}" for o in block[1]] + ["", "Note: ", ""]
            elif kind == "fields":
                out += ["| Field | Answer |", "|---|---|"]
                for label, opts in block[1]:
                    cell = " ".join(f"[ ] {o}" for o in opts)
                    out.append(f"| {md_cell(label)} | {md_cell(cell)} |")
                out.append("")
            elif kind == "grid":
                _, header, rows, cols = block
                out.append("| " + " | ".join(md_cell(h) for h in header) + " |")
                out.append("|" + "---|" * len(header))
                body_rows = rows if rows is not None else [""] * BLANK_ROWS
                for row in body_rows:
                    out.append("| " + " | ".join([md_cell(row)] + [" "] * (len(header) - 1)) + " |")
                out.append("")
                hints = option_hint(cols)
                if hints:
                    out += [f"*Allowed values.* {'; '.join(hints)}", ""]
            else:
                out += ["Answer: ", ""]
        out += [f"*Answered by:* {sources}", ""]
    if disclosure_blocks(data):
        d = data["disclosure"]
        out += [f"# {DISCLOSURE_HEADING}", "", " ".join(d["intro"].split()), ""]
        for label, where, text in disclosure_blocks(data):
            out += [f"## {label}", "", f"*Where:* {where}", "", f"> {text}", ""]
        out += ["**Tips**", ""] + [f"- {a}" for a in d.get("advice", [])] + [""]
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Word


def render_docx(data):
    m = data["meta"]
    doc = Document()
    styles = doc.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(10)
    doc.add_heading(f"{m['name']}: {m['full_name']}", level=0)
    doc.add_paragraph(f"Reporting checklist for research assisted by AI coding agents. Version {m['version']} ({m['date']}).")
    doc.add_paragraph(INTRO)
    for label in ("Project title", "Authors", "Date completed"):
        p = doc.add_paragraph()
        p.add_run(f"{label}: ").bold = True
    sources = "   ".join(f"{BOX} {s}" for s in source_labels(data))
    grey = RGBColor(0x55, 0x55, 0x55)

    def table(rows, cols):
        t = doc.add_table(rows=rows, cols=cols)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        return t

    for s, i in items(data):
        if i is None:
            doc.add_heading(f"{s['id']}. {s['title']}", level=1)
            doc.add_paragraph().add_run(s["purpose"]).italic = True
            continue
        doc.add_heading(f"{i['id']}. {i['title']} ({i['tier']})", level=2)
        doc.add_paragraph().add_run(i["question"]).bold = True
        g = doc.add_paragraph().add_run(i["guidance"].strip())
        g.italic = True
        g.font.color.rgb = grey
        g.font.size = Pt(9)
        for block in answer_blocks(i):
            kind = block[0]
            if kind == "choices":
                for o in block[1]:
                    doc.add_paragraph(f"{BOX} {o}")
                doc.add_paragraph("Note: ")
            elif kind == "fields":
                t = table(len(block[1]), 2)
                for r, (label, opts) in enumerate(block[1]):
                    t.cell(r, 0).text = label
                    t.cell(r, 1).text = "   ".join(f"{BOX} {o}" for o in opts)
            elif kind == "grid":
                _, header, rows, cols = block
                body_rows = rows if rows is not None else [""] * BLANK_ROWS
                t = table(len(body_rows) + 1, len(header))
                for c, h in enumerate(header):
                    t.cell(0, c).text = h
                    for run in t.cell(0, c).paragraphs[0].runs:
                        run.bold = True
                for r, row in enumerate(body_rows, start=1):
                    t.cell(r, 0).text = row
                for hint in option_hint(cols):
                    hp = doc.add_paragraph().add_run(hint)
                    hp.font.size = Pt(8)
            else:
                t = table(1, 1)
                t.cell(0, 0).text = "\n\n"
        sp = doc.add_paragraph().add_run(f"Answered by:   {sources}")
        sp.font.size = Pt(9)
    if disclosure_blocks(data):
        d = data["disclosure"]
        doc.add_page_break()
        doc.add_heading(DISCLOSURE_HEADING, level=1)
        doc.add_paragraph(" ".join(d["intro"].split()))
        for label, where, text in disclosure_blocks(data):
            doc.add_heading(label, level=2)
            w = doc.add_paragraph().add_run(f"Where: {where}")
            w.italic = True
            w.font.size = Pt(9)
            doc.add_paragraph(text, style="Quote")
        doc.add_paragraph().add_run("Tips").bold = True
        for a in d.get("advice", []):
            doc.add_paragraph(a, style="List Bullet")
    buf = io.BytesIO()
    doc.core_properties.title = f"{m['name']}: {m['full_name']}"
    doc.save(buf)
    return buf.getvalue()


def docx_text(blob):
    d = Document(io.BytesIO(blob))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        parts += [c.text for row in t.rows for c in row.cells]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# GitHub issue form for change proposals (its item list must match the checklist)


def render_issue_form(data):
    items_list = [f"{i['id']}. {i['title']}" for s in data["sections"] for i in s["items"]]
    form = {
        "name": "Propose a change to ACORN",
        "description": "Suggest a change to an item, a new item, or a change to the checklist as a whole.",
        "title": "[Item] ",
        "labels": ["proposal"],
        "body": [
            {"type": "markdown", "attributes": {"value": (
                "Thank you for helping improve ACORN. Proposals are public and are reviewed by the research team "
                "(see the Contribute page on the website for how decisions are made).")}},
            {"type": "dropdown", "id": "item", "attributes": {
                "label": "Which item does this concern?",
                "options": items_list + ["New item", "Whole checklist or structure"]},
             "validations": {"required": True}},
            {"type": "dropdown", "id": "change_type", "attributes": {
                "label": "Type of change",
                "options": ["Clarify wording or guidance", "Change what the item asks", "Add a new item",
                            "Remove or merge an item", "Change the answer options", "Other"]},
             "validations": {"required": True}},
            {"type": "textarea", "id": "proposal", "attributes": {
                "label": "Proposed change", "description": "Give the new wording if you can."},
             "validations": {"required": True}},
            {"type": "textarea", "id": "rationale", "attributes": {
                "label": "Why is this change needed?",
                "description": "For example, a situation in your field that the current item does not handle well."},
             "validations": {"required": True}},
            {"type": "input", "id": "field", "attributes": {
                "label": "Your research field",
                "placeholder": "e.g. experimental psychology, computational social science, physics"}},
            {"type": "input", "id": "orcid", "attributes": {
                "label": "ORCID iD (optional, for credit)", "placeholder": "0000-0000-0000-0000"}},
            {"type": "checkboxes", "id": "terms", "attributes": {
                "label": "Acknowledgement",
                "options": [{"label": "I understand this proposal and the discussion of it are public.", "required": True}]}},
        ],
    }
    header = "# Generated from checklist/checklist.yaml by scripts/build_formats.py. Do not edit by hand.\n"
    return header + yaml.safe_dump(form, sort_keys=False, allow_unicode=True, width=120)


# ---------------------------------------------------------------------------
# Data products for analysing many reports


CODEBOOK_COLUMNS = ["variable", "table", "item_id", "section", "tier", "introduced_in", "label", "measure", "allowed_values"]


def render_codebook(data):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CODEBOOK_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(variables(data))
    return buf.getvalue()


def render_schema(data):
    return json.dumps(report_schema(data), indent=2) + "\n"


# ---------------------------------------------------------------------------


def main(check):
    data = load()
    text_outputs = {
        OUT / "acorn-checklist.tex": render_tex(data),
        OUT / "acorn-checklist.Rmd": render_rmd(data),
        ROOT / ".github" / "ISSUE_TEMPLATE" / "change-proposal.yml": render_issue_form(data),
        ROOT / "checklist" / "codebook.csv": render_codebook(data),
        ROOT / "checklist" / "acorn-report.schema.json": render_schema(data),
    }
    docx_path = OUT / "acorn-checklist.docx"
    docx_blob = render_docx(data)
    if check:
        stale = [p for p, t in text_outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        if not docx_path.exists() or docx_text(docx_path.read_bytes()) != docx_text(docx_blob):
            stale.append(docx_path)
        for p in stale:
            print(f"STALE {p.relative_to(ROOT)}: run python scripts/build_formats.py")
        return 1 if stale else 0
    for p, t in text_outputs.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")
        print(f"wrote {p.relative_to(ROOT)}")
    # python-docx embeds timestamps, so only rewrite the Word file when its content changed.
    if not docx_path.exists() or docx_text(docx_path.read_bytes()) != docx_text(docx_blob):
        docx_path.write_bytes(docx_blob)
        print(f"wrote {docx_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
