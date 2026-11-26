"""Build the ACORN website from checklist/checklist.yaml into _site/.

Usage: python scripts/build_site.py [output_dir]

The site is plain static HTML (no JavaScript framework), so it works on GitHub Pages.
The GitHub repository used for links is read from the GITHUB_REPOSITORY environment
variable (set automatically in GitHub Actions), falling back to site/config.yaml.
"""
import html
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlencode

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acorn_data import diff_versions, iter_items, load_checklist  # noqa: E402
import build_formats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = ROOT / "site"

ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" '
    'd="M12 2c.6 0 1 .4 1 1v1.1c3.9.4 7 2.9 7 6.4H4c0-3.5 3.1-6 7-6.4V3c0-.6.4-1 1-1Z" opacity=".55"/>'
    '<path fill="currentColor" d="M5 12h14c0 5-3.1 9.5-7 10-3.9-.5-7-5-7-10Z"/></svg>'
)

NAV = [("index.html", "Home"), ("checklist.html", "Checklist"), ("use.html", "How to use"),
       ("disclose.html", "Cite & disclose"), ("versions.html", "Versions"), ("contribute.html", "Contribute")]


def esc(s):
    return html.escape(str(s), quote=True)


class Site:
    def __init__(self, out: Path):
        self.out = out
        self.data = yaml.safe_load((ROOT / "checklist" / "checklist.yaml").read_text(encoding="utf-8"))
        self.config = yaml.safe_load((SITE_SRC / "config.yaml").read_text(encoding="utf-8"))
        self.repo = os.environ.get("GITHUB_REPOSITORY") or self.config["default_repository"]
        self.repo_url = f"https://github.com/{self.repo}"
        self.meta = self.data["meta"]

    # -- helpers -------------------------------------------------------------

    def proposal_url(self, item=None):
        params = {"template": "change-proposal.yml"}
        if item:
            params["title"] = f"[{item['id']}] "
            params["item"] = f"{item['id']}. {item['title']}"
        else:
            params["title"] = "[New item] "
            params["item"] = "New item"
        return f"{self.repo_url}/issues/new?{urlencode(params)}"

    def page(self, path, title, body, current=None, depth=0, description=None, head_extra=""):
        up = "../" * depth
        current_attr = ' aria-current="page"'
        nav = "".join(
            f'<a href="{up}{href}"{current_attr if href == current else ""}>{esc(label)}</a>'
            for href, label in NAV
        )
        desc = description or f"{self.meta['name']}: {self.meta['full_name']}. A reporting checklist for research assisted by AI coding agents."
        doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="stylesheet" href="{up}style.css">
<link rel="icon" href="{up}favicon.svg" type="image/svg+xml">
{head_extra}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="wrap">
<a class="brand" href="{up}index.html">{ICON}<span>{esc(self.meta['name'])}</span></a>
<nav class="main" aria-label="Main">{nav}</nav>
</div></header>
<main id="main"><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
{esc(self.meta['name'])} ({esc(self.meta['full_name'])}), version {esc(self.meta['version'])}.
<a href="{self.repo_url}">Source on GitHub</a> ·
<a href="{self.repo_url}/blob/main/CHANGELOG.md">Changelog</a>
</div></footer>
</body>
</html>
"""
        target = self.out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(doc, encoding="utf-8")

    def answer_format(self, item):
        r = item["response"]
        t = r["type"]
        li = []
        if t in ("single_choice", "multi_choice"):
            kind = "Choose one" if t == "single_choice" else "Choose all that apply"
            li.append(f"<li>{kind}: " + "; ".join(esc(o["label"]) for o in r["options"]) + "</li>")
        if "fields" in r:
            for f in r["fields"]:
                opts = f" ({', '.join(esc(str(o).replace('_', ' ')) for o in f['options'])})" if f.get("options") else ""
                li.append(f"<li>{esc(f['label'])}{opts}</li>")
        if t == "table":
            if "rows" in r:
                li.append("<li>One row per role: " + "; ".join(esc(x["label"]) for x in r["rows"]) + "</li>")
            li.append("<li>Columns: " + "; ".join(
                esc(c["label"]) + (f" ({', '.join(esc(str(o).replace('_', ' ')) for o in c['options'])})" if c.get("options") else "")
                for c in r["columns"]) + "</li>")
        if t == "text":
            li.append("<li>Free text</li>")
        if t == "location" and "fields" not in r:
            li.append("<li>Persistent link (DOI, repository, archive), or the reason it is not shared</li>")
        return f'<ul class="answer-format">{"".join(li)}</ul>'

    def item_html(self, item, link_prefix="items/", heading="h3", standalone=False, archived=False):
        tier = item["tier"]
        introduced = f" · Introduced in version {esc(item['introduced_in'])}" if item.get("introduced_in") else ""
        guide = ", ".join(item.get("guide_llm", []) or [])
        guide_txt = f" · GUIDE-LLM: {esc(guide)}" if guide else ""
        linked = not (standalone or archived)
        title = f'<a href="{link_prefix}{item["id"]}.html">{esc(item["title"])}</a>' if linked else esc(item["title"])
        discuss = f'<a class="btn" href="{link_prefix}{item["id"]}.html">Discuss</a>' if linked else ""
        actions = "" if archived else (
            f'<div class="actions"><a class="btn" href="{esc(self.proposal_url(item))}">Propose a change</a>{discuss}</div>')
        return f"""<article class="item" id="{item['id']}">
<div class="item-head"><span class="id">{item['id']}</span><{heading}>{title}</{heading}><span class="pill {tier}">{tier}</span></div>
<p class="question">{esc(item['question'])}</p>
<p class="guidance">{esc(item['guidance'].strip())}</p>
<details><summary>Answer format</summary>{self.answer_format(item)}</details>
<details><summary>Instructions for coding agents</summary><p class="small">{esc(item['agent_instructions'].strip())}</p></details>
<p class="meta">Every answer also records who gave it: agent, human, agent checked by a human, or unknown.{guide_txt}{introduced}</p>
{actions}
</article>"""

    def site_url(self):
        owner, name = self.repo.split("/", 1)
        if name.lower() == f"{owner.lower()}.github.io":  # an organisation or user site is served at the root
            return f"https://{owner.lower()}.github.io/"
        return f"https://{owner.lower()}.github.io/{name}/"

    def citation_text(self):
        c = self.config["citation"]
        names = [f"{a['family']}, {a['given'][0]}." for a in c["authors"]]
        authors = names[0] if len(names) == 1 else ", ".join(names[:-1]) + ", & " + names[-1]
        return (f"{authors} ({c['year']}). {self.meta['name']}: {self.meta['full_name']} "
                f"(Version {self.meta['version']}) [Reporting checklist]. {self.site_url()}")

    def bibtex(self):
        c = self.config["citation"]
        key = f"{c['authors'][0]['family'].lower()}{c['year']}acorn"
        names = " and ".join(f"{a['family']}, {a['given']}" for a in c["authors"])
        return (f"@misc{{{key},\n  author = {{{names}}},\n"
                f"  title = {{{{{self.meta['name']}}}: {self.meta['full_name']}}},\n"
                f"  year = {{{c['year']}}},\n  version = {{{self.meta['version']}}},\n"
                f"  howpublished = {{\\url{{{self.site_url()}}}}},\n  note = {{Reporting checklist}}\n}}")

    def citation_html(self):
        return (f'<pre class="cite">{esc(self.citation_text())}</pre>'
                f'<details><summary>BibTeX</summary><pre>{esc(self.bibtex())}</pre></details>')

    # -- pages ---------------------------------------------------------------

    def build_index(self):
        n_items = sum(len(s["items"]) for s in self.data["sections"])
        n_core = sum(i["tier"] == "core" for s in self.data["sections"] for i in s["items"])
        sections = "".join(
            f'<div class="card"><span class="id">{s["id"]}</span> <strong>{esc(s["title"])}</strong><p class="muted small">{esc(s["purpose"])}</p></div>'
            for s in self.data["sections"]
        )
        body = f"""
<h1>{esc(self.meta['name'])}: {esc(self.meta['full_name'])}</h1>
<p class="lead">A reporting checklist for research that used AI coding agents. It records which agent was used, what it did,
who made each decision, and how others can reproduce the work. It is meant for any empirical or formal discipline,
and the coding agent itself can fill in most of it.</p>
<div class="actions">
<a class="btn primary" href="checklist.html">Read the checklist</a>
<a class="btn" href="use.html">How to use it</a>
<a class="btn" href="contribute.html">Propose a change</a>
</div>

<h2>Why ACORN</h2>
<div class="cards cols-2">
<div class="card"><strong>Compliant with publisher AI policies</strong><p class="muted small">ACORN covers what Elsevier, Springer Nature, Taylor &amp; Francis, Wiley, SAGE, Science and PNAS ask authors to disclose about AI.
Your agent checks these policies, and your target journal's, for changes each time it fills in a report, and flags any gap before you submit.
<a href="policies.html">See the policy comparison</a>.</p></div>
<div class="card"><strong>Simple to complete</strong><p class="muted small">ACORN comes with a skill for your coding agent.
Your agent fills in what it can find, asks you only for the rest in one numbered list, and drafts your Methods and Acknowledgements wording.
<a href="use.html">See how to use it</a> or <a href="disclose.html">get the wording</a>.</p></div>
<div class="card"><strong>Reproducible by people and agents</strong><p class="muted small">ACORN records models, permissions, environments, code and, where they can be shared, transcripts.
An independent researcher or agent can use the report to retrace the steps and rerun the analyses.
<a href="checklist.html#section-F">See the reproducibility items</a>.</p></div>
<div class="card"><strong>Living and open to revision</strong><p class="muted small">ACORN is a living standard that changes as agents and publisher policies change.
Anyone can propose a revision, every proposal and decision is public, and earlier versions stay available.
<a href="contribute.html">Propose a change</a> or <a href="versions.html">see all versions</a>.</p></div>
</div>

<h2>What it covers</h2>
<p class="muted">{n_items} items ({n_core} core, {n_items - n_core} optional) in {len(self.data['sections'])} sections.</p>
<div class="cards cols-4">{sections}</div>

<h2>Downloads</h2>
<div class="cards">
<div class="card"><strong>Agent skill</strong><p class="small"><a href="downloads/acorn-skill.zip">acorn-skill.zip</a></p></div>
<div class="card"><strong>Word</strong><p class="small"><a href="downloads/acorn-checklist.docx">acorn-checklist.docx</a></p></div>
<div class="card"><strong>LaTeX</strong><p class="small"><a href="downloads/acorn-checklist.tex">acorn-checklist.tex</a></p></div>
<div class="card"><strong>R Markdown</strong><p class="small"><a href="downloads/acorn-checklist.Rmd">acorn-checklist.Rmd</a></p></div>
<div class="card"><strong>Machine-readable</strong><p class="small"><a href="downloads/checklist.yaml">checklist.yaml</a></p></div>
<div class="card"><strong>For analysis</strong><p class="small"><a href="downloads/codebook.csv">codebook.csv</a> · <a href="downloads/acorn-report.schema.json">report schema</a></p></div>
</div>
<h2>Analyse reports</h2>
<p>Completed reports are structured data, so reports from many papers can be pooled and analysed, quantitatively and qualitatively.
<a href="analyse.html">See how to analyse ACORN reports</a>.</p>

<p class="small muted">See <a href="examples.html">example reports</a>, including <a href="examples/acorn-self-report.html">the report on how ACORN itself was built</a>.
Looking for an earlier version? <a href="versions.html">All versions</a> stay available.</p>

<h2>How to cite and disclose</h2>
<p>Ready-to-paste wording for your Methods and Acknowledgements, with copy buttons, is on the
<a href="disclose.html">Cite &amp; disclose</a> page. Please cite ACORN as:</p>
{self.citation_html()}

"""
        self.page("index.html", f"{self.meta['name']}: {self.meta['full_name']}", body, current="index.html")

    def build_checklist(self, data=None, path="checklist.html", depth=0, archived=False):
        data = data or self.data
        version = data["meta"]["version"]
        up = "../" * depth
        if archived:
            intro = (f'<p class="notice">This is the archived version {esc(version)} ({esc(data["meta"]["date"])}). '
                     f'It is kept unchanged so that reports made with it can be read and compared. '
                     f'<a href="{up}checklist.html">See the current version</a> or <a href="{up}versions.html">all versions</a>.</p>')
        else:
            intro = (f'<p class="lead">Version {esc(version)}. Core items should always be reported; optional items when relevant. '
                     f'<a href="versions.html">Earlier versions</a></p>')
        parts = [
            f"<h1>The checklist{' (version ' + esc(version) + ')' if archived else ''}</h1>",
            intro,
            '<nav aria-label="Sections"><p class="small">' + " · ".join(
                f'<a href="#section-{s["id"]}">{s["id"]}. {esc(s["title"])}</a>' for s in data["sections"]) + "</p></nav>",
        ]
        for s in data["sections"]:
            parts.append(f'<h2 class="section-head" id="section-{s["id"]}">{s["id"]}. {esc(s["title"])}</h2>')
            parts.append(f'<p class="muted">{esc(s["purpose"])}</p>')
            parts += [self.item_html(i, archived=archived) for i in s["items"]]
        if not archived:
            parts.append(f'<p class="actions"><a class="btn" href="{esc(self.proposal_url())}">Propose a new item</a></p>')
        title = f"Checklist {version}: {self.meta['name']}" if archived else f"Checklist: {self.meta['name']}"
        self.page(path, title, "\n".join(parts), current=None if archived else "checklist.html", depth=depth)

    def build_item_pages(self):
        g = self.config.get("giscus", {})
        for s in self.data["sections"]:
            for i in s["items"]:
                if g.get("enabled"):
                    discussion = f"""<h2>Discussion</h2>
<p class="muted small">Comments are stored in this project's GitHub Discussions and need a GitHub account. For a concrete change, please use <a href="{esc(self.proposal_url(i))}">Propose a change</a>.</p>
<script src="https://giscus.app/client.js" data-repo="{esc(self.repo)}" data-repo-id="{esc(g['repo_id'])}"
 data-category="{esc(g['category'])}" data-category-id="{esc(g['category_id'])}" data-mapping="specific"
 data-term="{esc(i['id'])}: {esc(i['title'])}" data-strict="1" data-reactions-enabled="1" data-emit-metadata="0"
 data-input-position="top" data-theme="preferred_color_scheme" data-lang="en" data-loading="lazy" crossorigin="anonymous" async></script>"""
                else:
                    discussion = f"""<h2>Discussion</h2>
<p class="notice small">Comment threads for each item will appear here. Until then, use <a href="{esc(self.proposal_url(i))}">Propose a change</a>.</p>"""
                body = f"""<p class="small"><a href="../checklist.html#{i['id']}">← Back to the checklist</a> · Section {s['id']}: {esc(s['title'])}</p>
{self.item_html(i, heading="h1", standalone=True)}
{discussion}"""
                self.page(f"items/{i['id']}.html", f"{i['id']}. {i['title']}: {self.meta['name']}", body, depth=1,
                          description=i["question"])

    def build_use(self):
        body = f"""
<h1>How to use ACORN</h1>
<p class="lead">There are two ways: let your coding agent fill it in (recommended), or fill in a form yourself.</p>

<h2>1. Let your coding agent fill it in</h2>
<p>Download <a href="downloads/acorn-skill.zip">acorn-skill.zip</a> and unzip it into your project, so that it contains <code>acorn/SKILL.md</code>. Then tell your agent:</p>
<pre>Read acorn/SKILL.md and follow it to fill in the ACORN report for this project.</pre>
<p>If your agent supports the Agent Skills format, you can instead install the <code>acorn</code> folder as a skill
(for example in <code>.claude/skills/</code> for Claude Code; check your agent's documentation for its skills folder).</p>
<p>The agent will:</p>
<ol>
<li>gather what it can find itself: its model and settings, the git history, project instruction files and package versions;</li>
<li>draft every item, recording who provided each answer;</li>
<li>ask you everything it could not find, in one message;</li>
<li>write <code>acorn-report.yaml</code> and a readable <code>acorn-report.md</code> for your supplementary material;</li>
<li>draft the Methods, Acknowledgements and availability wording for your manuscript in <code>acorn-disclosure.md</code>, filled in from the report;</li>
<li>check the AI policies of the major publishers for changes, and check your target journal's policy, flagging any gaps or conflicts (see <a href="policies.html">publisher policies</a>).</li>
</ol>
<p>The agent will not guess, and it will not publish or deposit anything itself.</p>

<p>See <a href="examples.html">example reports</a>, including <a href="examples/acorn-self-report.html">the report on how ACORN itself was built</a>.</p>

<h2>Tip: start an ACORN log at the beginning of a project</h2>
<p>Ask your agent to "keep an ACORN log". It records decisions, ideas, alternative analyses and errors in <code>ACORN_LOG.md</code> as you work,
so the final report is far more complete, especially the decision log.</p>

<h2>2. Fill in a form yourself</h2>
<p>Download the <a href="downloads/acorn-checklist.docx">Word</a>, <a href="downloads/acorn-checklist.tex">LaTeX</a> or
<a href="downloads/acorn-checklist.Rmd">R Markdown</a> version, fill it in, and include it in your supplementary material.</p>

<h2>Where to report it</h2>
<p>Deposit the completed report with your replication package under a persistent DOI (for example on Zenodo or OSF), and say in the
manuscript that AI coding agents were used and reported with ACORN, citing the version. The <a href="disclose.html">Cite &amp; disclose</a>
page has ready-to-paste Methods and Acknowledgements wording with copy buttons. Please cite ACORN as:</p>
{self.citation_html()}
"""
        self.page("use.html", f"How to use: {self.meta['name']}", body, current="use.html")

    def build_disclose(self):
        from render_report import CHECKS, SUPERVISION, TASKS, WRITING_ROLES, fill_template
        d = self.data["disclosure"]
        version = self.meta["version"]
        ph = d["placeholders"]
        c1 = next(i for _, i in iter_items(self.data) if i["id"] == "C1")
        a3 = next(i for _, i in iter_items(self.data) if i["id"] == "A3")
        e1 = next(i for _, i in iter_items(self.data) if i["id"] == "E1")
        task_boxes = "".join(
            f'<label><input type="checkbox" name="task" value="{esc(TASKS[r["value"]])}"{" data-writing" if r["value"] in WRITING_ROLES else ""}> {esc(r["label"].split(" (")[0])}</label>'
            for r in c1["response"]["rows"])
        check_labels = {o: o.replace("_", " ") for o in e1["response"]["columns"][1]["options"]}
        check_boxes = "".join(
            f'<label><input type="checkbox" name="check" value="{esc(CHECKS[v])}"> {esc(check_labels[v].capitalize())}</label>'
            for v in CHECKS)
        levels = "".join(f'<option value="{esc(SUPERVISION[o["value"]])}">{esc(o["label"].split(":")[0])}: {esc(o["label"].split(": ", 1)[1])}</option>'
                         for o in a3["response"]["options"])
        cards = []
        for t in d["templates"]:
            text = " ".join(t["text"].split())
            plain = fill_template(text, {}, version, ph)
            cards.append(f"""<div class="card template" data-id="{esc(t['id'])}">
<div class="template-head"><strong>{esc(t['label'])}</strong><button class="btn copy" type="button" hidden>Copy</button></div>
<p class="muted small">Where: {esc(t['where'])}</p>
<p class="wording">{esc(plain)}</p>
</div>""")
        templates_json = json.dumps({t["id"]: " ".join(t["text"].split()) for t in d["templates"]})
        tips = "".join(f"<li>{esc(a)}</li>" for a in d["advice"])
        body = f"""
<h1>Cite &amp; disclose</h1>
<p class="lead">Ready-to-paste wording for disclosing AI coding agents in your manuscript. Let your agent write it for you from your completed report,
or fill in the fields and copy the text.</p>
<p class="muted">{esc(" ".join(d["intro"].split()))}</p>
<p class="small">See <a href="policies.html">how ACORN meets the AI policies of the major publishers</a>, and what each one asks for.</p>

<h2>Let your agent write it</h2>
<p>When the <a href="use.html">ACORN skill</a> fills in your report, it also writes <code>acorn-disclosure.md</code>: the wording below,
filled in from your report and tailored to your project. To get it for a report you already have, tell your agent:</p>
<pre>Read acorn/SKILL.md, then draft the Methods and Acknowledgements wording from acorn-report.yaml.</pre>
<p class="small">See <a href="examples/fictional-example-disclosure.html">the wording drafted from the fictional example report</a>.</p>

<h2>Fill in the details</h2>
<form class="disclose-form" id="disclose-form" onsubmit="return false">
<label class="field">Agent and model, with exact version
<input type="text" id="f-agents" placeholder="e.g. Example Agent CLI 2.3 with example-model-2026-09-01 (Example Provider)"></label>
<fieldset><legend>What the agent did</legend><div class="boxes">{task_boxes}</div>
<label class="field small">Other tasks (optional) <input type="text" id="f-tasks-other" placeholder="e.g. translating survey items"></label></fieldset>
<label class="field">Human oversight (item A3)
<select id="f-supervision"><option value="">Choose a level</option>{levels}</select></label>
<fieldset><legend>How the authors checked the agent's outputs (item E1)</legend><div class="boxes">{check_boxes}</div></fieldset>
<label class="field">Other AI tools used for writing or translation, with versions (item A7, optional)
<input type="text" id="f-writing-tools" placeholder="e.g. Example Chat Assistant (example-chat-2026-08)"></label>
<label class="field">What those tools did (optional)
<input type="text" id="f-writing-other" placeholder="e.g. editing the language of the Introduction"></label>
<label class="field">AI-generated or AI-edited figures: tool, version and figure (optional)
<input type="text" id="f-figures" placeholder="e.g. Example Image Tool 3 (Figure 1, schematic of the study design)"></label>
<label class="field">Link to your completed ACORN report (a DOI is best)
<input type="text" id="f-location" placeholder="e.g. https://doi.org/10.5281/zenodo.0000000"></label>
<p class="small muted">Nothing you type leaves your browser. ACORN version {esc(version)} is filled in automatically.</p>
</form>

<h2>Your wording</h2>
<p class="small muted">Parts in [square brackets] still need your details.</p>
<div class="templates">{''.join(cards)}</div>

<h2>Tips</h2>
<ul class="spaced">{tips}</ul>

<h2 id="cite">How to cite ACORN</h2>
{self.citation_html()}

<script>
(function () {{
  var T = {templates_json};
  var PH = {json.dumps(ph)};
  var VERSION = {json.dumps(version)};
  var form = document.getElementById("disclose-form");
  function join(a) {{ a = a.filter(Boolean); return a.length < 3 ? a.join(" and ") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]; }}
  function checked(name) {{ return Array.prototype.map.call(form.querySelectorAll('input[name="' + name + '"]:checked'), function (x) {{ return x.value; }}); }}
  function values() {{
    var boxes = Array.prototype.slice.call(form.querySelectorAll('input[name="task"]:checked'));
    var tasks = boxes.map(function (x) {{ return x.value; }});
    var research = boxes.filter(function (x) {{ return !x.hasAttribute("data-writing"); }}).map(function (x) {{ return x.value; }});
    var writing = boxes.filter(function (x) {{ return x.hasAttribute("data-writing"); }}).map(function (x) {{ return x.value; }});
    var other = document.getElementById("f-tasks-other").value.trim();
    if (other) {{ tasks.push(other); research.push(other); }}
    var agents = document.getElementById("f-agents").value.trim();
    var wtools = document.getElementById("f-writing-tools").value.trim();
    var wother = document.getElementById("f-writing-other").value.trim();
    if (wother) writing.push(wother);
    var writingTools = [];
    if (boxes.some(function (x) {{ return x.hasAttribute("data-writing"); }})) writingTools.push(agents || "the AI coding agent");
    if (wtools) writingTools.push(wtools);
    var checks = checked("check");
    return {{
      agents: agents,
      tasks: join(tasks),
      research_tasks: join(research),
      supervision: document.getElementById("f-supervision").value,
      verification: checks.length ? "The authors checked the agent's outputs by " + join(checks) + "." : "",
      writing_tools: join(writingTools),
      writing_tasks: join(writing),
      figure_tools: document.getElementById("f-figures").value.trim(),
      location: document.getElementById("f-location").value.trim()
    }};
  }}
  function esc(s) {{ return s.replace(/[&<>"]/g, function (c) {{ return {{"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}}[c]; }}); }}
  function fill(text, v, html) {{
    return text.replace(/[{{](\\w+)[}}]/g, function (_, k) {{
      if (k === "version") return VERSION;
      if (v[k]) return html ? esc(v[k]) : v[k];
      var p = "[" + (PH[k] || k) + "]";
      return html ? '<span class="ph">' + esc(p) + "</span>" : p;
    }});
  }}
  function update() {{
    var v = values();
    document.querySelectorAll(".template").forEach(function (card) {{
      var t = T[card.dataset.id];
      card.querySelector(".wording").innerHTML = fill(t, v, true);
      card.dataset.plain = fill(t, v, false);
    }});
  }}
  form.addEventListener("input", update);
  form.addEventListener("change", update);
  document.querySelectorAll(".template .copy").forEach(function (b) {{
    b.hidden = false;
    b.addEventListener("click", function () {{
      var text = b.closest(".template").dataset.plain;
      var done = function () {{ b.textContent = "Copied"; setTimeout(function () {{ b.textContent = "Copy"; }}, 1500); }};
      if (navigator.clipboard && window.isSecureContext) {{
        navigator.clipboard.writeText(text).then(done, function () {{ fallback(text); done(); }});
      }} else {{ fallback(text); done(); }}
    }});
  }});
  function fallback(text) {{
    var ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "absolute"; ta.style.left = "-9999px";
    document.body.appendChild(ta); ta.select();
    try {{ document.execCommand("copy"); }} catch (e) {{}}
    document.body.removeChild(ta);
  }}
  update();
}})();
</script>
"""
        self.page("disclose.html", f"Cite & disclose: {self.meta['name']}", body, current="disclose.html",
                  description="Ready-to-paste Methods and Acknowledgements wording for disclosing AI coding agents, and how to cite ACORN.")

    CELL = {"required": ("●", "Required", "req"), "recommended": ("○", "Recommended", "rec"),
            "not_allowed": ("✕", "Not allowed", "no"), "exempt": ("–", "Exempt", "na"),
            "not_exempt": ("●", "Not exempt", "req"), "not_mentioned": ("·", "Not mentioned", "na")}
    STATUS = {"covered": "Covered", "partial": "Partly covered", "skill_check": "Checked by the skill"}

    def build_policies(self):
        pol = yaml.safe_load((ROOT / "checklist" / "publisher-policies.yaml").read_text(encoding="utf-8"))
        pubs = pol["publishers"]
        head = "".join(f'<th scope="col">{esc(x["name"])}</th>' for x in pubs)
        rows = []
        for r in pol["requirements"]:
            cells = []
            for x in pubs:
                raw = str(r["cells"][x["id"]])
                kind, _, note = raw.partition(":")
                sym, label, cls = self.CELL[kind.strip()]
                note = note.strip()
                cells.append(f'<td class="pc {cls}"><span aria-hidden="true">{sym}</span> {esc(label)}'
                             + (f'<br><span class="small muted">{esc(note)}</span>' if note else "") + "</td>")
            rows.append(f'<tr><th scope="row">{esc(r["requirement"])}</th><td class="small">{esc(r["acorn"])}'
                        f'<br><span class="pill {"optional" if r["status"] != "covered" else ""}">{esc(self.STATUS[r["status"]])}</span></td>{"".join(cells)}</tr>')
        summaries = "".join(
            f'<div class="card"><strong>{esc(x["name"])}</strong>{" <span class=\"muted small\">(#" + str(x["rank"]) + " by number of journals)</span>" if x.get("rank") else ""}'
            f'<p class="small">{esc(" ".join(x["summary"].split()))}</p>'
            f'<p class="small muted">Policy date: {esc(x["policy_date"])}. ' + " · ".join(f'<a href="{esc(u)}">Source {i + 1}</a>' for i, u in enumerate(x["urls"])) + "</p></div>"
            for x in pubs)
        body = f"""
<h1>Publisher AI policies</h1>
<p class="lead">How ACORN meets the AI policies of the five largest academic publishers by number of journals, plus Science and PNAS.</p>
<p class="notice small">Policies last checked on {esc(pol['last_checked'])}. Policies change often, and individual journals can add their own rules.
The ACORN skill re-checks these pages and your target journal's policy when it fills in your report, and tells you about any changes or gaps.</p>
<p>A completed ACORN report contains everything these policies ask authors to disclose. The <a href="disclose.html">disclosure wording</a> covers each place
they ask for it: the Methods, the Acknowledgements or a separate AI declaration, figure legends, and the cover letter.</p>
<div class="table-wrap policy-table"><table>
<thead><tr><th scope="col">Requirement</th><th scope="col">In ACORN</th>{head}</tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="small muted">● required · ○ recommended · ✕ not allowed · – exempt from disclosure · · not mentioned in the policy.
"Checked by the skill" marks rules about what may be done with AI, or what authors must check without reporting it; the skill flags them when they apply.</p>
<h2>Policy summaries</h2>
<div class="cards">{summaries}</div>
<p class="small">Spotted a policy change? <a href="{esc(self.proposal_url())}">Tell us</a>, or edit
<a href="{self.repo_url}/blob/main/checklist/publisher-policies.yaml">checklist/publisher-policies.yaml</a>.</p>
"""
        self.page("policies.html", f"Publisher AI policies: {self.meta['name']}", body,
                  description="How the ACORN checklist meets the AI policies of Elsevier, Springer Nature, Taylor & Francis, Wiley, SAGE, Science and PNAS.")

    def build_contribute(self):
        body = f"""
<h1>Contribute</h1>
<p class="lead">ACORN is a living standard. Anyone can propose a change, and every proposal and decision is public.</p>

<h2>Propose a change</h2>
<ul class="spaced">
<li><strong>Change an item.</strong> Use the <em>Propose a change</em> button on any item in the <a href="checklist.html">checklist</a>. It opens a short form with the item already filled in.</li>
<li><strong>Suggest a new item.</strong> <a href="{esc(self.proposal_url())}">Open the proposal form</a> and choose "New item".</li>
<li><strong>Discuss.</strong> Each item has its own page for discussion. General questions go to <a href="{self.repo_url}/discussions">Discussions</a>.</li>
<li><strong>Edit directly.</strong> Comfortable with GitHub? Open a pull request that changes <code>checklist/checklist.yaml</code>.</li>
</ul>
<p class="muted small">Proposals are made with a GitHub account, so each one is linked to a real person and recorded publicly with its date.
You can add your ORCID iD to the form so that we can credit you.</p>

<h2>How decisions are made</h2>
<div class="table-wrap"><table>
<thead><tr><th>Type of change</th><th>Examples</th><th>How it is decided</th><th>Version</th></tr></thead>
<tbody>
<tr><td>Minor</td><td>Clarified wording, examples, typo fixes</td><td>Reviewed by the research team on a rolling basis</td><td>0.1.0 → 0.1.1</td></tr>
<tr><td>Major</td><td>Adding, removing or redefining items</td><td>Decided by the research team at a scheduled review, with the reasons published on the proposal</td><td>0.1 → 0.2</td></tr>
<tr><td>Conceptual</td><td>Restructuring the checklist</td><td>A new consultation round with the community</td><td>1.x → 2.0</td></tr>
</tbody></table></div>
<p>Every release is listed in the <a href="{self.repo_url}/blob/main/CHANGELOG.md">changelog</a>. Item IDs are never reused, so reports that cite an item stay unambiguous.</p>

<h2>Credit</h2>
<p>Contributors whose proposals are accepted are listed in the repository's <code>CONTRIBUTORS.md</code> and acknowledged in the release notes.</p>
"""
        self.page("contribute.html", f"Contribute: {self.meta['name']}", body, current="contribute.html")

    # -- versions --------------------------------------------------------------

    def releases(self):
        index = yaml.safe_load((ROOT / "checklist" / "versions" / "index.yaml").read_text(encoding="utf-8")) or {}
        out = []
        for rel in index.get("releases") or []:
            data = load_checklist(ROOT / "checklist" / "versions" / rel["version"] / "checklist.yaml")
            out.append((rel, data))
        return out  # oldest first

    def version_downloads(self, data, folder, source_dir):
        folder.mkdir(parents=True, exist_ok=True)
        for name in ("checklist.yaml", "codebook.csv", "acorn-report.schema.json"):
            shutil.copy2(source_dir / name, folder / name)
        (folder / "acorn-checklist.tex").write_text(build_formats.render_tex(data), encoding="utf-8")
        (folder / "acorn-checklist.Rmd").write_text(build_formats.render_rmd(data), encoding="utf-8")
        (folder / "acorn-checklist.docx").write_bytes(build_formats.render_docx(data))

    @staticmethod
    def download_links(prefix):
        files = [("checklist.yaml", "YAML"), ("codebook.csv", "Codebook"), ("acorn-report.schema.json", "Report schema"),
                 ("acorn-checklist.docx", "Word"), ("acorn-checklist.tex", "LaTeX"), ("acorn-checklist.Rmd", "R Markdown")]
        return " · ".join(f'<a href="{prefix}{f}">{label}</a>' for f, label in files)

    @staticmethod
    def diff_html(diff, against):
        if not any(diff.values()):
            return f'<span class="muted">No item changes since {esc(against)}</span>'
        names = {"added": "Added", "removed": "Removed", "changed": "Changed (answers not directly comparable)",
                 "reworded": "Reworded only"}
        return "<br>".join(f"{names[k]}: {', '.join(v)}" for k, v in diff.items() if v) + f'<br><span class="muted small">Compared with {esc(against)}</span>'

    def build_versions(self):
        releases = self.releases()
        rows = []
        latest = releases[-1] if releases else None
        if not latest or latest[0]["version"] != self.meta["version"]:
            diff = self.diff_html(diff_versions(latest[1], self.data), latest[0]["version"]) if latest else '<span class="muted">First version</span>'
            rows.append(f"""<tr><td><strong>{esc(self.meta['version'])}</strong><br><span class="pill">current</span></td>
<td>{esc(self.meta['date'])}</td><td>{sum(1 for _ in iter_items(self.data))}</td>
<td><a href="checklist.html">View</a><br><span class="small">{self.download_links('downloads/')}</span></td><td class="small">{diff}</td></tr>""")
        for n in range(len(releases) - 1, -1, -1):
            rel, data = releases[n]
            v = rel["version"]
            folder = f"v/{v}/"
            self.build_checklist(data, path=f"{folder}checklist.html", depth=2, archived=True)
            self.version_downloads(data, self.out / folder, ROOT / "checklist" / "versions" / v)
            diff = self.diff_html(diff_versions(releases[n - 1][1], data), releases[n - 1][0]["version"]) if n else '<span class="muted">First release</span>'
            current = ' <span class="pill">current</span>' if v == self.meta["version"] else ""
            rows.append(f"""<tr><td><strong>{esc(v)}</strong>{current}</td><td>{esc(rel['date'])}</td><td>{sum(1 for _ in iter_items(data))}</td>
<td><a href="{folder}checklist.html">View</a><br><span class="small">{self.download_links(folder)}</span></td><td class="small">{diff}</td></tr>""")
        empty = "" if releases else '<p class="notice small">No version has been released yet. Each release will be archived here permanently.</p>'
        body = f"""
<h1>Versions</h1>
<p class="lead">Every released version of ACORN stays available here unchanged, so that any report can be read with the version it was made with.</p>
{empty}
<div class="table-wrap"><table>
<thead><tr><th>Version</th><th>Date</th><th>Items</th><th>Checklist and files</th><th>What changed</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<h2>How versions work</h2>
<ul>
<li><strong>Patch</strong> (e.g. 1.0.0 → 1.0.1): wording or guidance clarified. Answers stay comparable.</li>
<li><strong>Minor</strong> (e.g. 1.0 → 1.1): items added, removed or changed.</li>
<li><strong>Major</strong> (e.g. 1.x → 2.0): the checklist is restructured.</li>
</ul>
<p>Item IDs are never reused, and every item records the version it was introduced in. Each report states the ACORN version it used,
so reports from different versions can be combined (see <a href="analyse.html">Analyse reports</a>).
The full history is in the <a href="{self.repo_url}/blob/main/CHANGELOG.md">changelog</a>.</p>
"""
        self.page("versions.html", f"Versions: {self.meta['name']}", body, current="versions.html")

    def build_analyse(self):
        body = f"""
<h1>Analyse reports</h1>
<p class="lead">Completed ACORN reports are structured data, so that reports from many papers can be pooled and analysed,
both quantitatively and qualitatively.</p>

<h2>How reports are structured</h2>
<ul>
<li><strong>Machine-readable file.</strong> Each report is an <code>acorn-report.yaml</code> file that follows a
<a href="downloads/acorn-report.schema.json">JSON Schema</a>, alongside the readable version for the paper.</li>
<li><strong>Fixed codes.</strong> Closed questions are answered with fixed codes (e.g. <code>agent_autonomous</code>), not free wording.
Counts and amounts are numbers.</li>
<li><strong>Typed missing values.</strong> Missing answers say why they are missing: <code>unknown</code>, <code>not_applicable</code>,
<code>not_disclosed</code> or <code>not_available</code>.</li>
<li><strong>Who answered.</strong> Every answer records who gave it (agent, human, agent checked by a human, or unknown).</li>
<li><strong>Versioned.</strong> Each report states its ACORN version, and every item records the version it was introduced in.
<a href="versions.html">All versions</a> stay available.</li>
</ul>

<h2>Turn many reports into tables</h2>
<p>Collect the <code>acorn-report.yaml</code> files in a folder and run the script from the
<a href="{self.repo_url}">repository</a>:</p>
<pre>pip install -r requirements.txt
python scripts/acorn_analyze.py reports/ --out acorn-data/</pre>
<p>It checks each report against the schema of its own version, then writes:</p>
<div class="table-wrap"><table>
<thead><tr><th>File</th><th>Contents</th><th>Use</th></tr></thead>
<tbody>
<tr><td><code>reports_wide.csv</code></td><td>One row per report, one column per variable, e.g. supervision level, permissions, number of decisions the agent made on its own</td><td>Quantitative analysis</td></tr>
<tr><td><code>table_rows.csv</code></td><td>One row per entry in the open-ended tables: models, ideas, decision log, verification, errors</td><td>Analysing decisions and ideas</td></tr>
<tr><td><code>texts.csv</code></td><td>Every free-text answer with its report and item</td><td>Qualitative coding</td></tr>
<tr><td><code>codebook.csv</code></td><td>Name, label, measure and allowed values of every variable</td><td>Documentation</td></tr>
<tr><td><code>validation.csv</code></td><td>Reports that do not match the schema, and why</td><td>Data cleaning</td></tr>
</tbody></table></div>
<p>Variable names follow the item IDs, for example <code>A3</code> (supervision level), <code>A4_skip_permissions</code>,
<code>C1_formal_analysis_level</code> and <code>D1_approved_by_agent_autonomous_n</code>.
See the <a href="downloads/codebook.csv">codebook</a> and the <a href="examples.html">example reports</a>.</p>
"""
        self.page("analyse.html", f"Analyse reports: {self.meta['name']}", body)

    EXAMPLES = [
        ("acorn-self-report", "acorn-self-report.yaml", "How ACORN itself was built",
         "A real report on how an AI coding agent helped create ACORN: the checklist, skill, formats and this website. "
         "It is a draft, so the items the authors still have to approve are marked with red TODOs."),
        ("fictional-example", "acorn-report-example.yaml", "Fictional online experiment",
         "A made-up, completed report for an online behavioural experiment, showing what a finished report looks like."),
    ]

    def build_examples(self):
        import markdown
        from render_report import render, render_disclosure
        cards = []
        for slug, name, title, desc in self.EXAMPLES:
            report = yaml.safe_load((ROOT / "examples" / name).read_text(encoding="utf-8"))
            body_md = render(report, self.data)
            body_html = markdown.markdown(body_md, extensions=["tables", "toc"])
            disclosure_md = render_disclosure(report, self.data)
            wording_link = (f' · <a href="{slug}-disclosure.html">Disclosure wording drafted from this report</a>'
                            if disclosure_md else "")
            body = f"""<p class="small"><a href="../examples.html">← All examples</a> · <a href="../downloads/{name}">Download the YAML file</a>{wording_link}</p>
<p class="notice small">{esc(desc)}</p>
<div class="report">{body_html}</div>"""
            self.page(f"examples/{slug}.html", f"Example: {title}: {self.meta['name']}", body, depth=1, description=desc)
            if disclosure_md:
                dbody = f"""<p class="small"><a href="{slug}.html">← Back to the report</a> · <a href="../disclose.html">Fill in the wording yourself</a></p>
<p class="notice small">This is the <code>acorn-disclosure.md</code> file that the ACORN skill writes next to the report. It was generated from the example report above.</p>
<div class="report">{markdown.markdown(disclosure_md, extensions=["tables"])}</div>"""
                self.page(f"examples/{slug}-disclosure.html", f"Disclosure wording: {title}: {self.meta['name']}", dbody, depth=1)
            cards.append(f'<div class="card"><strong><a href="examples/{slug}.html">{esc(title)}</a></strong><p class="muted small">{esc(desc)}</p></div>')
        body = f"""<h1>Example reports</h1>
<p class="lead">Completed ACORN reports, shown the way the agent skill writes them.</p>
<div class="cards">{''.join(cards)}</div>"""
        self.page("examples.html", f"Examples: {self.meta['name']}", body)

    def build_downloads(self):
        dl = self.out / "downloads"
        dl.mkdir(parents=True, exist_ok=True)
        for name in ("acorn-checklist.docx", "acorn-checklist.tex", "acorn-checklist.Rmd"):
            shutil.copy2(ROOT / "formats" / name, dl / name)
        for name in ("checklist.yaml", "codebook.csv", "acorn-report.schema.json"):
            shutil.copy2(ROOT / "checklist" / name, dl / name)
        for _, name, _, _ in self.EXAMPLES:
            shutil.copy2(ROOT / "examples" / name, dl / name)
        with zipfile.ZipFile(dl / "acorn-skill.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted((ROOT / "skill" / "acorn").iterdir()):
                z.write(f, f"acorn/{f.name}")
            z.write(ROOT / "skill" / "README.md", "acorn/README.md")

    def build(self):
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        shutil.copy2(SITE_SRC / "style.css", self.out / "style.css")
        (self.out / ".nojekyll").write_text("", encoding="utf-8")
        favicon = ICON.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ').replace("currentColor", "#8a5a2b")
        (self.out / "favicon.svg").write_text(favicon, encoding="utf-8")
        self.build_index()
        self.build_checklist()
        self.build_item_pages()
        self.build_use()
        self.build_disclose()
        self.build_policies()
        self.build_contribute()
        self.build_analyse()
        self.build_examples()
        self.build_versions()
        self.build_downloads()
        n = sum(1 for _ in self.out.rglob("*.html"))
        print(f"built {n} pages into {self.out}")


if __name__ == "__main__":
    Site(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_site").build()
