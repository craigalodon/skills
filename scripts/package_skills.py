# /// script
# requires-python = ">=3.11"
# ///
"""Package one or more skills into versioned tarballs for a GitHub Release.

Each skill directory (a `<name>/SKILL.md` pair, excluding `template/`) is
written as `<out>/<name>-<version>.tar.gz` whose sole top-level member is
`<name>/...`, so it extracts straight into a harness's skills directory:

    tar -xzf merging-dependabot-prs-1.0.0.tar.gz -C ~/.claude/skills/

Development-only content (eval harnesses, tool caches) is left out. A
`SHA256SUMS` file covering every built artifact is written alongside them.

Run directly (`uv run scripts/package_skills.py --version 1.0.0`) or from
.github/workflows/release.yml.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = "template"

# Paths that exist for development but shouldn't ship with a packaged skill:
# eval harnesses (see merging-dependabot-prs/evals/README.md) and tool caches.
EXCLUDE_NAMES = {"evals", "__pycache__", ".pytest_cache", ".ruff_cache", ".DS_Store"}


def skill_dirs(repo: Path, only: str | None = None) -> list[Path]:
    """Skill directories under *repo*: `<name>/SKILL.md`, minus the template.

    Duplicated from `validate_skills.skill_dirs` rather than imported — see
    CONTRIBUTING.md "Helper scripts" for when that stops being the right call.
    """
    dirs = sorted(
        p.parent for p in repo.glob("*/SKILL.md") if p.parent.name != TEMPLATE_DIR
    )
    if only is not None:
        dirs = [d for d in dirs if d.name == only]
    return dirs


def _skip_excluded(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
    if any(part in EXCLUDE_NAMES for part in Path(tarinfo.name).parts):
        return None
    return tarinfo


def package_skill(skill_dir: Path, version: str, out: Path) -> Path:
    """Write `<out>/<skill>-<version>.tar.gz` and return its path."""
    dest = out / f"{skill_dir.name}-{version}.tar.gz"
    with tarfile.open(dest, "w:gz") as tar:
        tar.add(skill_dir, arcname=skill_dir.name, filter=_skip_excluded)
    return dest


def write_checksums(paths: list[Path], out: Path) -> Path:
    """Write a `sha256sum`-compatible `SHA256SUMS` covering *paths*."""
    dest = out / "SHA256SUMS"
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in sorted(paths, key=lambda p: p.name)
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", help="package only this skill (default: all)")
    parser.add_argument("--version", required=True, help="version string, e.g. 1.0.0")
    parser.add_argument(
        "--out", default="dist", help="output directory (default: dist)"
    )
    parser.add_argument(
        "--repo", default=str(REPO), help="repo root (default: this repo)"
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    dirs = skill_dirs(repo, only=args.skill)
    if not dirs:
        target = args.skill or "any skill"
        print(f"✗ no matching skill found for {target!r} in {repo}", file=sys.stderr)
        return 1

    built = [package_skill(skill_dir, args.version, out) for skill_dir in dirs]
    checksums = write_checksums(built, out)

    manifest = {
        "version": args.version,
        "artifacts": [path.name for path in built] + [checksums.name],
    }
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
