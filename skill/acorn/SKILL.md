---
name: acorn
description: Fill in the ACORN reporting checklist (AI CO-scientist Reporting Norms) describing how an AI coding agent assisted a research project, draft the Methods and Acknowledgements wording that discloses it, check it against publisher and target-journal AI policies, or keep a running ACORN decision log during the project. Use when a researcher asks to report, disclose or document AI agent use for a paper, preprint, thesis, grant or replication package, or asks how to word an AI disclosure statement or whether it meets a journal's AI policy.
license: See LICENSE in the ACORN repository
---

# ACORN: AI CO-scientist Reporting Norms

ACORN is a reporting checklist that records which AI coding agent assisted a research project, what it did, who made each decision, and how the work can be reproduced. You, the agent, fill in as much as you can from evidence, and ask the human only for what you cannot know.

Files in this skill folder:
- `checklist.yaml`: the checklist. Each item has an `id`, a `question`, a `response` shape, `guidance`, and `agent_instructions` written for you. Read it fully before starting.
- `answers-template.yaml`: a blank report with one entry per item.
- `render_report.py`: turns `acorn-report.yaml` into the readable `acorn-report.md`, with TODO markers in red, and drafts the manuscript wording in `acorn-disclosure.md`.
- `publisher-policies.yaml`: what the AI policies of the major publishers (Elsevier, Springer Nature, Taylor & Francis, Wiley, SAGE, Science, PNAS) require, with their URLs, the date they were last checked, and which ACORN items meet each requirement.
- `acorn-report.schema.json`: the JSON Schema the finished `acorn-report.yaml` must follow. Reports from many papers are pooled and analysed by researchers, so the structure must be exact.

There are two modes. Use **report mode** unless the human asks for logging.

## Report mode: fill in the checklist

### 1. Gather evidence before asking anything
Collect what you can find yourself. Typical sources:
- **Your own session:** model ID, agent product and version, permission mode, loaded instruction files, skills, tools and servers, web access.
- **Session history:** earlier conversations or logs for this project if your product stores them, and an `ACORN_LOG.md` if one exists (see logging mode).
- **The repository:** `git log` (authors, dates, commit messages; commits co-authored by an agent), instruction files (`AGENTS.md`, `CLAUDE.md` and similar), README, pre-registration documents.
- **The environment:** language and package versions (e.g. `R -e 'sessionInfo()'`, `python -m pip freeze`, `julia -e 'using Pkg; Pkg.status()'`), lock files (`renv.lock`, `uv.lock`, `environment.yml`, `Manifest.toml`, `Dockerfile`).
- **Data files** the analysis reads, to describe the level of data access (item G1). Do not copy data contents into the report.

### 2. Draft every item
Copy `answers-template.yaml` to `acorn-report.yaml` in the project root (or where the human asks), and fill in each item following its `agent_instructions`. Also fill in the `report` block: title, authors, DOI if known, main discipline, today's date, and a `report_id` (the DOI if there is one).

Format rules, so that reports can be analysed across papers:
- **Use codes, not labels.** Where an item or field has options, write the option's `value` from `checklist.yaml` (e.g. `agent_autonomous`, `read_line_by_line`), never its label or your own wording. Multiple-choice answers are lists of codes.
- **Numbers as numbers.** Fields with `value_type: integer` or `number` take a plain number (e.g. `6`, not "about six").
- **Missing values with a reason.** Instead of leaving an answer empty or writing "N/A", use one of the codes under `missing_values`: `unknown`, `not_applicable`, `not_disclosed`, `not_available`.
- **Free text stays in text fields and notes.** Put explanations in `note` or in text fields, not inside coded fields.
- **Write a note only when a reader needs it.** Use `note` for facts the answer cannot hold: exceptions, scope limits (e.g. sessions not covered) and caveats about the data. Do not use notes to ask for confirmation (that is what `todo` is for), to describe how you found the answer, to repeat the answer, or to give advice. Most items need no note. Every note is something a human has to review.
- **Keep the structure.** Do not add, rename or remove keys. If you can run code, check the file against `acorn-report.schema.json` (e.g. with Python's `jsonschema` package) and fix any errors.

Every answer has a `source`:
- `agent`: you found it in your own records, settings or the project files.
- `human`: the human told you.
- `agent_verified`: you drafted it and the human confirmed it.
- `unknown`: nobody could determine it. Use a missing-value code as the answer and explain in `note`.

Rules:
- **Never guess.** If you have no evidence, mark the item `unknown` and add it to your questions for the human. A wrong answer is worse than a gap.
- **Be candid about your own role.** In C2 (origin of ideas) and D1 (decision log), list decisions you made without asking, even if they seem minor. Use `approved_by: agent_autonomous` for them.
- **Cover sessions you cannot see.** You usually only see your current session. Say so in the note on A1, C1, C2 and D1, and ask the human about earlier sessions and other agents.
- **Optional items** (`tier: optional`): fill them when you have evidence, otherwise write `not_applicable` or leave them for the human.
- **No personal data.** Do not put participant data, names or contact details of anyone other than the authors, credentials or API keys into the report.

**Mark everything that needs human approval with a TODO.** Set the answer's `todo` field to a short, specific request whenever:
- the answer's `source` is `agent` and a human has not confirmed it yet, for items whose answer is a judgement or covers work you may not have seen (always A1, A3, A7, B1, B3, C1, C2, D1, E1, G2, G3),
- the answer is `unknown`, or you left it empty for the human,
- you inferred or estimated the answer rather than read it from a record.

Write the request so it can be answered in a line, e.g. `Confirm level 2: approvals happened only when merging pull requests.` In the readable report, every TODO appears as a red marker (🔴 **TODO (needs human approval):** …), and all TODOs are listed at the top as a numbered list. A report is final only when no `todo` is left.

### 3. Ask the human once, in a batch
After drafting, ask the human all remaining questions in **one message**, as a **numbered list** (1., 2., 3., ...) with the item ID in each question, each phrased so it can be answered in a line. Numbering lets the human answer by number (e.g. "3. no"). Typical ones you cannot answer yourself:
- ideas and decisions from meetings or earlier sessions (C2, D1),
- how they verified your outputs (E1),
- pre-registration details (E2),
- provider data terms and ethics approval (G2, G3),
- where code will be deposited (F1), and whether transcripts will be deposited too (B3, optional),
- other AI tools they or coauthors used, e.g. for editing, translation or figures (A7),
- which journal(s) or publisher(s) they plan to submit to (for step 6).

Ask about every item that has a `todo`. When the human confirms or answers an item, update the answer, set `source` to `agent_verified` (or `human`), and clear its `todo`. Keep any `todo` they have not resolved.

**Clean up after every round of answers.** Re-read the `note` of every item, not only the ones the human answered, and delete or shorten any note that is now outdated or redundant: notes that asked for confirmation, explained an uncertainty the human has resolved, or repeat what the answer now says. Use the human's own wording where they gave it. Then re-render the outputs, so that `acorn-report.md` and `acorn-disclosure.md` match.

### 4. Produce the outputs
1. `acorn-report.yaml`: the filled report (machine-readable, valid against the schema). Tell the human to deposit it with the replication package, so that it can be found and analysed.
2. `acorn-report.md`: a readable version for the paper's supplementary material. If you can run Python, create it with `python render_report.py acorn-report.yaml checklist.yaml` (from this skill folder's files). Otherwise write it yourself: one heading per section; for each item the ID, title, answer, source and note, with tables as Markdown tables. Start it with `Reported using ACORN v<version from checklist.yaml> (AI CO-scientist Reporting Norms).`
   Show every `todo` directly under its item in red, exactly like this, so it stands out in any viewer (the colour shows in HTML, R Markdown and most previews; the red circle and the word TODO show everywhere):
   `<span style="color:#d00000">🔴 <strong>TODO (needs human approval):</strong> …</span>`
   If any TODOs remain, list them all at the top of the report as a numbered list (1., 2., 3., ...), never as bullet points, so the human can refer to them by number.
3. `acorn-disclosure.md`: ready-to-paste wording for the manuscript (see step 5), followed by the policy check (step 6). `render_report.py` writes a first draft of it next to `acorn-report.md`.
4. A short summary to the human: how many items were answered by the agent, by the human, verified, and unknown, and how many TODOs remain. List the TODOs as a numbered list. Then show the suggested Methods and Acknowledgements wording (step 5) directly in your message, so the human can paste it without opening a file, and the result of the policy check (step 6).

### 5. Suggest the Methods and Acknowledgements wording
Researchers must disclose AI use in the manuscript itself, and most journals want it in the Methods, the Acknowledgements, or both. Write this wording for them, so that disclosing takes no effort.

1. **Start from the templates.** The `disclosure` block in `checklist.yaml` has templates for the Methods, the Acknowledgements (full and short), a separate AI declaration for writing help, figure legends, the cover letter, and the availability statement. Each says where it goes; templates with `requires` are only needed when that value exists (e.g. a figure legend only when a figure was AI-generated or AI-edited). Each has `{placeholders}`, described under `disclosure.placeholders`. `render_report.py` fills them from the report into `acorn-disclosure.md`. If you cannot run Python, fill them yourself from the same items:
   - `{agents}`: the agent product (A2) and every model with its exact version ID and provider (A1).
   - `{tasks}`: the research roles in C1 where the agent `led` or `assisted`, in plain words; `{research_tasks}` is the same without the writing and reference roles.
   - `{writing_tools}` and `{writing_tasks}`: the agent (if C1 shows writing roles) and any A7 tools used for language editing, drafting or translation, with what they did and where.
   - `{figure_tools}`: A7 tools used for figures or images, with versions and which figures.
   - `{supervision}`: one sentence describing the A3 level.
   - `{verification}`: one sentence on how outputs were checked (E1). Say plainly which outputs were not verified, if any.
   - `{location}`: the persistent link to the deposited report, preferably a DOI.
   - `{version}`: the ACORN version from `meta.version`. Always cite it.
2. **Tailor the draft.** Make the generated sentences read naturally for this project: name the specific outputs (e.g. "the data cleaning script and the mixed-effects models" rather than "statistical analysis"), mention notable exceptions recorded in notes (e.g. a stage that ran at a different supervision level), and match the paper's voice ("we" or "the authors"). Keep the structure of the template and its key claims: which agent and model, which tasks, how humans supervised and verified, that the authors take responsibility, and where the ACORN report is with its version.
3. **Claim nothing the report does not support.** Every statement must match an answer in `acorn-report.yaml`. Never write that the authors reviewed or verified everything unless E1 says so; if they did not, say what was checked. Do not soften the agent's role.
4. **Leave gaps visible.** Anything you cannot fill stays in `[square brackets]`, and is listed at the top of `acorn-disclosure.md` as a red TODO. If the report still has TODOs, say the wording may change once they are resolved.
5. **Point to a persistent DOI.** If `{location}` is not a DOI, add a TODO advising the human to deposit the report on Zenodo or OSF and use that DOI. Remind them to cite ACORN itself in the references (citation in the ACORN repository's `CITATION.cff` or on the website's Cite & disclose page).
6. **Never list an agent as an author** or suggest doing so.

If the human only asks for the disclosure wording, or for a journal policy check, and an `acorn-report.yaml` already exists, skip steps 1 to 3 and do steps 5 and 6 from the existing report.

### 6. Check publisher and journal AI policies
Journal AI policies differ and change often. Check them every time you produce the disclosure wording, and tell the human what you found. Skip only the parts you cannot do (e.g. you have no web access) and say so.

1. **Check the major publishers for updates.** Read every URL in `publisher-policies.yaml`. Compare what each page says now with the publisher's `summary` and its column in `requirements`. If a policy changed since `last_checked` (a new requirement, a new disclosure location, a new prohibition, or a new policy date), flag it to the human: name the publisher, quote the changed passage briefly, and say whether the report or wording needs to change. If nothing changed, say "checked on <date>, no changes" in one line. If a page cannot be read, say which one, and do not guess its content.
2. **Check the target journal(s) or publisher(s).** If the human names where they will submit (ask in step 3 if you do not know), find that journal's own AI policy (the journal's author guidelines, then its publisher's policy) and read it. Then, item by item:
   - **Confirm what is met:** for each thing the policy asks authors to disclose, name the ACORN item or disclosure template that covers it.
   - **Flag gaps:** anything the policy requires that the report or wording does not yet contain (e.g. a required section title, a cover-letter statement, a prompt log, a figure-legend note, the reason for using AI). Add the missing piece to `acorn-disclosure.md` where you can, and a TODO where you cannot.
   - **Flag conflicts:** any AI use in the report that the policy restricts or forbids (e.g. AI-generated images, synthetic data or participants, AI-written results or discussion, sensitive data sent to a public tool). Say exactly which report answer conflicts with which policy passage. Never hide or reword a conflict to make it disappear; the human must decide what to do.
   - **Map each A7 row by its purpose code.** A7 purposes follow the STM classification of AI use in manuscript preparation (`stm_classification` in `publisher-policies.yaml`). Many policies are written in these terms (Science's `a7_rules` give its rule for each code), so match each row to the policy's rule for that activity: declare it where the policy says, drop declarations the policy does not need, and flag uses the policy forbids. Anything that looks like AI content presented as real research data or results (STM 9) is a conflict under every policy.
   - **Remind about the tool's terms:** if the policy asks authors to check the AI tool's terms (Elsevier, Wiley and Taylor & Francis do), remind the human to confirm that the tools in A1 and A7 do not train on their inputs (record this in G2) and do not claim ownership of, or restrict publication of, the outputs.
   - **Adapt the wording:** use the policy's required section title, location or template wording (e.g. Elsevier's declaration title), and drop pieces it does not want.
3. **Write it down.** Add a `## Publisher policy check` section at the end of `acorn-disclosure.md` with the date, the URLs you read, and a table with one row per requirement: requirement, where ACORN covers it, status (met, gap, conflict). List gaps and conflicts as red TODOs in the numbered list at the top.
4. If a major publisher's policy changed, suggest that the human report it to the ACORN maintainers (the website's "Tell us" link), so the shared table can be updated.

### 7. Do not publish anything yourself
Do not deposit transcripts, push to public repositories or upload anything to archives as part of this task. Tell the human what to deposit and where. Point out any personal data in transcripts they plan to share.

## Logging mode: keep a decision log as you work
If the human asks you to keep an ACORN log (recommended at the start of a project), keep `ACORN_LOG.md` in the project root and append to it during the work. This makes the final report far more complete, because it records decisions before they are forgotten.

Append an entry whenever any of these happens:
- a decision that could change results or their interpretation (exclusion rules, model specification, outlier handling, variable coding, deviations from a plan),
- you propose an idea, hypothesis or approach,
- you run an alternative analysis or specification,
- an error is found and fixed,
- the model, agent product or permission mode changes.

Entry format:

```markdown
### YYYY-MM-DD: <short title>
- Type: decision | idea | alternative analysis | error | setup change
- What: <one or two sentences>
- Proposed by: human | agent
- Approved by: human | agent (autonomous)
- Why: <rationale>
- Where: <file, commit or script>
```

Keep entries short and factual. Ask the human before logging anything personal or sensitive. In report mode, use the log as the main source for items C2, D1, E2 and E3.
