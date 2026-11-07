"""Check that each SkillType discriminant occurs in the legacy skill data.

Run from any directory: python tools/check_skill_enum.py
Extra effect types in the data are intentionally ignored.
"""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main():
    source = (ROOT / "src/race_solver.rs").read_text(encoding="utf-8")
    match = re.search(r"\bpub\s+enum\s+SkillType\s*\{([^}]*)\}", source, re.DOTALL)
    if not match:
        raise ValueError("Could not find the SkillType enum")
    body = re.sub(r"//[^\n]*|/\*.*?\*/", "", match.group(1), flags=re.DOTALL)
    variants = {}
    for entry in body.split(","):
        if not entry.strip():
            continue
        variant = re.fullmatch(r"\s*(\w+)\s*=\s*(\d+)\s*", entry)
        if not variant:
            raise ValueError(f"Cannot parse SkillType variant: {entry.strip()!r}")
        variants[variant.group(1)] = int(variant.group(2))
    if not variants:
        raise ValueError("SkillType has no variants")

    data = json.loads((ROOT / "data/skill_data.json").read_text(encoding="utf-8"))
    occurrences = {}
    for skill_id, skill in data.items():
        for alternative in skill["alternatives"]:
            for effect in alternative["effects"]:
                occurrences.setdefault(effect["type"], set()).add(skill_id)

    missing = []
    for name, value in variants.items():
        ids = occurrences.get(value, set())
        if ids:
            print(f"{name} ({value}): {len(ids)} skill(s); example {min(ids)}")
        else:
            missing.append(f"{name} ({value})")
    if missing:
        print("No skill data for: " + ", ".join(missing), file=sys.stderr)
        return 1
    print(f"All {len(variants)} SkillType values occur in skill data.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Skill enum check failed: {error}", file=sys.stderr)
        sys.exit(2)
