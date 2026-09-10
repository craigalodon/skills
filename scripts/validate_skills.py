# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""Validate that every skill in this repo stays within the portable SKILL.md
subset and matches the conventions in CONTRIBUTING.md.

Run directly (`uv run scripts/validate_skills.py`) or via pre-commit / CI.
Exits non-zero and prints one line per problem if anything is wrong.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = "template"
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
RESERVED = ("anthropic", "claude")
PORTABLE_KEYS = {"name", "description", "license", "metadata"}
MAX_DESCRIPTION = 1024
MAX_BODY_LINES = 500
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def frontmatter(text: str) -> tuple[dict, str] | tuple[None, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def check_skill(skill_dir: Path, readme: str, problems: list[str]) -> None:
    rel = skill_dir.name
    md = skill_dir / "SKILL.md"
    fm, body = frontmatter(md.read_text(encoding="utf-8"))

    def err(msg: str) -> None:
        problems.append(f"{rel}/SKILL.md: {msg}")

    if fm is None:
        err("missing YAML frontmatter delimited by ---")
        return

    extra = set(fm) - PORTABLE_KEYS
    if extra:
        err(
            f"non-portable frontmatter key(s): {', '.join(sorted(extra))} "
            f"(allowed: {', '.join(sorted(PORTABLE_KEYS))})"
        )

    name = fm.get("name")
    if not name:
        err("frontmatter missing 'name'")
    else:
        if not NAME_RE.match(str(name)):
            err(f"name {name!r} must match [a-z0-9-], max 64 chars")
        if name != rel:
            err(f"name {name!r} does not match directory name {rel!r}")
        if any(w in str(name) for w in RESERVED):
            err(f"name {name!r} contains a reserved word ({'/'.join(RESERVED)})")

    desc = fm.get("description")
    if not desc or not str(desc).strip():
        err("frontmatter missing non-empty 'description'")
    else:
        desc = str(desc).strip()
        if len(desc) > MAX_DESCRIPTION:
            err(f"description is {len(desc)} chars (max {MAX_DESCRIPTION})")
        if "<" in desc and ">" in desc:
            err("description must not contain XML/HTML tags")
        low = desc.lower()
        if low.startswith(("i ", "i'll", "i can", "you ", "you can", "use this to")):
            err("description should be third person (not 'I'/'you')")

    body_lines = body.count("\n") + 1
    if body_lines > MAX_BODY_LINES:
        err(
            f"body is {body_lines} lines (keep under {MAX_BODY_LINES}; move detail to references/)"
        )

    # Local links: must resolve, stay inside the skill, and be one level deep.
    for target in MD_LINK_RE.findall(body):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        if "\\" in path_part:
            err(f"link uses backslashes: {target}")
        if path_part.startswith("/") or ".." in Path(path_part).parts:
            err(f"link escapes the skill directory: {target}")
            continue
        if not (skill_dir / path_part).exists():
            err(f"broken link: {target}")
        elif path_part.count("/") > 1:
            err(f"link is more than one level deep: {target} (flatten references/)")

    if rel not in readme:
        problems.append(f"README.md: skill {rel!r} is missing from the catalog table")


def skill_dirs(repo: Path) -> list[Path]:
    return sorted(
        p.parent for p in repo.glob("*/SKILL.md") if p.parent.name != TEMPLATE_DIR
    )


def validate_repo(repo: Path) -> list[str]:
    """Return a list of problem strings for the skills repo rooted at *repo*.

    An empty list means everything is valid. This is the testable core; `main`
    only adds argument handling and reporting.
    """
    problems: list[str] = []
    dirs = skill_dirs(repo)
    if not dirs:
        return ["no skills found (expected <name>/SKILL.md directories)"]

    readme = (repo / "README.md").read_text(encoding="utf-8")
    for skill_dir in dirs:
        check_skill(skill_dir, readme, problems)

    # The template should still parse and carry both required keys.
    tmpl = repo / TEMPLATE_DIR / "SKILL.md"
    if tmpl.exists():
        fm, _ = frontmatter(tmpl.read_text(encoding="utf-8"))
        if not fm or "name" not in fm or "description" not in fm:
            problems.append(
                f"{TEMPLATE_DIR}/SKILL.md: must keep 'name' and 'description'"
            )

    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    repo = Path(argv[0]).resolve() if argv else REPO

    problems = validate_repo(repo)
    if problems:
        print(f"✗ {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1

    print(f"✓ {len(skill_dirs(repo))} skill(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
