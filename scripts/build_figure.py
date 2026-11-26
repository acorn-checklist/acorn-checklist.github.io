"""Build the overview figure of the ACORN checklist for papers and talks.

Reads checklist/checklist.yaml, so the figure always matches the current items.
Writes figures/acorn-overview.pdf (vector) and figures/acorn-overview.png (300 dpi).

Usage: python scripts/build_figure.py [out_dir]
Needs Node.js with Playwright and Chromium.
"""
import html
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# One short line per section, so the figure stays light. Edit here if section purposes change.
SHORT = {
    "A": "Which agents, how supervised",
    "B": "What humans asked for",
    "C": "What the agent contributed",
    "D": "Who decided what, and why",
    "E": "How outputs were checked",
    "F": "How others can reproduce it",
    "G": "What data the agent saw",
}

SITE = "acorn-checklist.github.io"  # shown in the figure; change here if the address changes
WIDTH_MM = 180  # full page width in most journals; the height follows the content


def build_html(data):
    meta = data["meta"]
    cards = []
    for s in data["sections"]:
        items = "".join(
            f'<li class="{i["tier"]}"><span class="iid">{i["id"]}</span>{html.escape(i["title"])}</li>'
            for i in s["items"])
        cards.append(f"""<div class="card">
<div class="head"><span class="letter">{s['id']}</span><span class="title">{html.escape(s['title'])}</span></div>
<p class="purpose">{html.escape(SHORT.get(s['id'], ''))}</p>
<ul>{items}</ul></div>""")
    # Break a long address only after a slash, never at a hyphen.
    site_html = "/<wbr>".join(f'<span class="nw">{html.escape(part)}</span>' for part in SITE.split("/"))
    n = sum(len(s["items"]) for s in data["sections"])
    n_core = sum(i["tier"] == "core" for s in data["sections"] for i in s["items"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {WIDTH_MM}mm; }}
body {{ font-family: Inter, "Helvetica Neue", Arial, sans-serif; color: #1f2a24; background: #fff;
  padding: 5mm 5mm 4mm; display: flex; flex-direction: column; gap: 3.2mm; }}
.top h1 {{ font-size: 13pt; font-weight: 700; letter-spacing: -0.01em; }}
.top h1 span {{ color: #2f6b4f; }}
.top p {{ font-size: 8pt; line-height: 1.4; color: #4a5650; margin-top: 1.2mm; max-width: 150mm; }}
.grid {{ display: grid; grid-template-columns: repeat(4, 1fr); grid-auto-rows: auto; column-gap: 2.6mm; }}
/* Each card spans three shared rows (title, purpose, items), so the dividers line up across a row. */
.card {{ grid-row: span 3; display: grid; grid-template-rows: subgrid; row-gap: 0; margin-bottom: 2.6mm; }}
.card {{ border: 0.3mm solid #d5ddd8; border-radius: 1.6mm; padding: 2.4mm 2.6mm; background: #fbfcfb; }}
.head {{ display: flex; align-items: center; gap: 1.8mm; }}
.letter {{ flex: none; width: 5.2mm; height: 5.2mm; border-radius: 50%; background: #2f6b4f; color: #fff;
  font-size: 7.5pt; font-weight: 700; display: flex; align-items: center; justify-content: center; }}
.title {{ font-size: 7.6pt; font-weight: 650; line-height: 1.2; }}
.purpose {{ font-size: 6.4pt; line-height: 1.35; color: #5b6761; padding: 1.4mm 0 1.6mm; }}
ul {{ list-style: none; align-self: start; border-top: 0.25mm solid #e1e7e3; padding-top: 1.4mm; }}
li {{ font-size: 6.6pt; line-height: 1.3; margin-bottom: 0.7mm; display: flex; gap: 1.4mm; }}
.iid {{ flex: none; width: 4.2mm; font-weight: 600; color: #2f6b4f; }}
li.optional {{ color: #7d8883; font-style: italic; }}
li.optional .iid {{ color: #8fa89b; font-style: normal; }}
.legend {{ grid-column: 4; grid-row: span 3; margin-bottom: 2.6mm; display: flex; flex-direction: column; justify-content: flex-end; gap: 1.2mm;
  font-size: 6.4pt; color: #5b6761; line-height: 1.4; padding: 0 1mm 0.6mm; }}
.legend b {{ color: #1f2a24; font-weight: 600; }}
.legend .site {{ margin-top: 2mm; padding-top: 1.6mm; border-top: 0.25mm solid #e1e7e3; }}
.legend .site b {{ color: #2f6b4f; font-size: 7.4pt; }}
.nw {{ white-space: nowrap; }}
.legend .opt {{ font-style: italic; color: #7d8883; }}
</style></head><body>
<div class="top">
<h1><span>{html.escape(meta['name'])}</span>: {html.escape(meta['full_name'])}</h1>
<p>A reporting checklist for research that used AI coding agents. It records which agent was used, what it did,
who made each decision, and how others can reproduce the work. The coding agent fills in most of it; the authors confirm and complete it.</p>
</div>
<div class="grid">{''.join(cards)}
<div class="legend"><span><b>{n} items</b> in {len(data['sections'])} sections</span>
<span>{n_core} core items, always reported</span><span class="opt">{n - n_core} optional items, reported when relevant</span>
<span class="site">Checklist, agent skill and disclosure wording:<br><b>{site_html}</b></span></div>
</div></body></html>"""


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "figures"
    out.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load((ROOT / "checklist" / "checklist.yaml").read_text(encoding="utf-8"))
    page_html = build_html(data)
    (out / "acorn-overview.html").write_text(page_html, encoding="utf-8")
    # Render with Node Playwright (the same browser the site screenshots use).
    js = f"""
const {{chromium}} = require('playwright');
(async () => {{
  const b = await chromium.launch();
  const p = await b.newPage({{viewport: {{width: {round(WIDTH_MM * 96 / 25.4)}, height: 400}}, deviceScaleFactor: {300 / 96}}});
  await p.goto({json.dumps((out / "acorn-overview.html").resolve().as_uri())});
  const h = await p.evaluate(() => Math.ceil(document.body.getBoundingClientRect().height));
  await p.setViewportSize({{width: {round(WIDTH_MM * 96 / 25.4)}, height: h}});
  await p.pdf({{path: {json.dumps(str(out / "acorn-overview.pdf"))}, width: "{WIDTH_MM}mm", height: (h + 1) + "px", printBackground: true, pageRanges: "1"}});
  await p.screenshot({{path: {json.dumps(str(out / "acorn-overview.png"))}}});
  await b.close();
}})();"""
    subprocess.run(["node", "-e", js], check=True)
    print(f"wrote {out}/acorn-overview.pdf and .png")


if __name__ == "__main__":
    main()
