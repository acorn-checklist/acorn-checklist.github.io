# Changelog

ACORN uses version numbers of the form MAJOR.MINOR.PATCH:

- **Patch** (0.1.0 → 0.1.1): clarified wording, guidance or examples.
- **Minor** (0.1 → 0.2): items added, removed or redefined.
- **Major** (1.x → 2.0): conceptual restructuring after a community consultation.

Item IDs are never reused.

## 0.1.0 (2026-11-26)

First release. Completed reports are machine-readable: fixed answer codes, typed missing values, numeric fields, a JSON Schema, an analysis codebook and a script that pools reports into tables.

22 items (17 core, 5 optional) in 7 sections: agent, interface and supervision; human goals and instructions; agent contributions; decision log; verification and research integrity; reproducibility; data protection and ethics.

Changes since the first draft (2026-11-16):

- Ready-to-paste disclosure wording (Methods, Acknowledgements full and short, availability statement) in `checklist.yaml`, added to the Word, LaTeX and R Markdown forms.
- New website page, Cite & disclose, that fills in the wording from a few fields and copies it with one click.
- The agent skill now drafts tailored Methods and Acknowledgements wording from the completed report (`acorn-disclosure.md`), and shows it in its summary.
- Checked against the AI policies of Elsevier, Springer Nature, Taylor & Francis, Wiley, SAGE, Science and PNAS (`checklist/publisher-policies.yaml`, website page Publisher AI policies). Gaps found and fixed:
  - New core item A7 (Other AI tools): publishers require every AI tool to be disclosed, including chatbots for editing or translation and image generators. Its purpose codes follow the STM classification of AI use in manuscript preparation (2025), plus codes for research uses that STM does not cover.
  - New disclosure templates: a separate AI declaration for writing help (Elsevier), a figure legend note (Elsevier, Wiley, PNAS, Springer Nature) and a cover letter statement (Science). The Methods template now lists research tasks only, since writing help goes in the Acknowledgements or declaration.
- C2 (Origin of ideas) and B3 (Transcripts) are now optional rather than core.
- C1 (Contributions by role): the two writing roles now cover only the text of the paper itself. Other text the agent wrote goes under the role it served, or under Other.
- The skill re-checks those policies for changes each time it runs, and checks the researcher's target journal(s), flagging gaps and conflicts.
