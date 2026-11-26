"""Validate checklist/checklist.yaml: unique IDs, required fields, allowed values."""
import sys
from pathlib import Path

import yaml

REQUIRED_ITEM_KEYS = {"id", "tier", "introduced_in", "title", "question", "response", "guidance", "agent_instructions", "origin"}
TIERS = {"core", "optional"}


def main(path: Path) -> int:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    types = set(data["response_types"])
    errors, ids = [], set()
    for section in data["sections"]:
        for item in section["items"]:
            iid = item.get("id", "?")
            missing = REQUIRED_ITEM_KEYS - item.keys()
            if missing:
                errors.append(f"{iid}: missing {sorted(missing)}")
            if iid in ids:
                errors.append(f"{iid}: duplicate id")
            ids.add(iid)
            if not iid.startswith(section["id"]):
                errors.append(f"{iid}: id does not match section {section['id']}")
            if item.get("tier") not in TIERS:
                errors.append(f"{iid}: tier must be one of {sorted(TIERS)}")
            if item.get("response", {}).get("type") not in types:
                errors.append(f"{iid}: unknown response type")
            r = item.get("response", {})
            for part in r.get("fields", []) + r.get("columns", []):
                if part.get("value_type", "text") not in data.get("value_types", ["text"]):
                    errors.append(f"{iid}: unknown value_type in '{part['name']}'")
                if part.get("value_type") and part.get("options"):
                    errors.append(f"{iid}: '{part['name']}' has both options and value_type")
                for opt in part.get("options", []):
                    if not isinstance(opt, str):
                        errors.append(f"{iid}: option {opt!r} in '{part['name']}' is not text (quote yes/no in YAML)")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from acorn_data import variables
    names = [v["variable"] for v in variables(data)]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        errors.append(f"duplicate analysis variable names: {sorted(dupes)}")
    # Archived releases must never change.
    import hashlib
    archive = Path(__file__).resolve().parent.parent / "checklist" / "versions"
    index = yaml.safe_load((archive / "index.yaml").read_text(encoding="utf-8")) or {}
    for rel in index.get("releases") or []:
        for name, digest in rel["sha256"].items():
            f = archive / rel["version"] / name
            if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != digest:
                errors.append(f"archived release {rel['version']}: {name} is missing or was modified")
    # Publisher policy table: every requirement has a cell for every publisher.
    pol_path = path.parent / "publisher-policies.yaml"
    if pol_path.exists():
        pol = yaml.safe_load(pol_path.read_text(encoding="utf-8"))
        pubs = [x["id"] for x in pol["publishers"]]
        kinds = {"required", "recommended", "not_allowed", "exempt", "not_exempt", "not_mentioned"}
        for r in pol["requirements"]:
            if set(r["cells"]) != set(pubs):
                errors.append(f"publisher-policies {r['id']}: cells must cover exactly {pubs}")
            for pub, cell in r["cells"].items():
                if str(cell).split(":")[0].strip() not in kinds:
                    errors.append(f"publisher-policies {r['id']}/{pub}: unknown value {cell!r}")
    for e in errors:
        print("ERROR", e)
    n_core = sum(i["tier"] == "core" for s in data["sections"] for i in s["items"])
    print(f"{len(ids)} items ({n_core} core, {len(ids) - n_core} optional) in {len(data['sections'])} sections")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "checklist/checklist.yaml")))
