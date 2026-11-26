# Contributing to ACORN

ACORN is a living standard. Anyone can propose a change, and every proposal and decision is public.

## How to propose a change

- **Change an item or suggest a new one:** open an issue with the [change proposal form](../../issues/new?template=change-proposal.yml). The website's *Propose a change* button on each item opens this form with the item filled in.
- **Discuss:** comment on an item's page on the website, or use [Discussions](../../discussions) for general questions.
- **Edit directly:** open a pull request that changes `checklist/checklist.yaml`. Then run `python scripts/build_skill.py` and `python scripts/build_formats.py` so that the other formats match. The checks on the pull request fail if you forget.

## How decisions are made

ACORN is maintained by its research team.

| Type of change | Examples | How it is decided | Version |
|---|---|---|---|
| Minor | Clarified wording, examples, typo fixes | Reviewed by the research team on a rolling basis | patch |
| Major | Adding, removing or redefining items | Decided by the research team at a scheduled review, with the reasons published on the proposal | minor |
| Conceptual | Restructuring the checklist | A new consultation round with the community | major |

Each proposal receives a public answer: accepted, accepted with changes, deferred to the next review, or declined, with reasons.

## Releasing a version (maintainers)

1. Run `python scripts/release.py <version>` (e.g. `1.0.0`). It stamps the version and date, rebuilds every format, and archives a frozen copy in `checklist/versions/`.
2. Add the release notes to `CHANGELOG.md`, commit, and create a GitHub release with the same version tag. With Zenodo connected, each release gets its own DOI.
3. After a release, set `meta.version` in `checklist/checklist.yaml` to the next draft (e.g. `1.1.0-draft`) before making further changes. New items get `introduced_in` set to the version they will be released in.

Archived versions are never edited. The checks fail if an archived file changes.

## Credit

Contributors whose proposals are accepted are listed in [CONTRIBUTORS.md](CONTRIBUTORS.md) and acknowledged in the release notes. Add your ORCID iD to your proposal if you would like it included.
