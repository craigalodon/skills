"""Tests for scripts/package_skills.py.

Run with: uv run --with pytest pytest
"""

from __future__ import annotations

import tarfile
from pathlib import Path

import package_skills as pk  # on sys.path via tests/conftest.py


def make_repo(tmp_path: Path) -> Path:
    skill = tmp_path / "doing-things"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: doing-things\n---\nbody\n", encoding="utf-8"
    )
    refs = skill / "references"
    refs.mkdir()
    (refs / "notes.md").write_text("notes", encoding="utf-8")

    # Development-only content that should never ship.
    evals = skill / "evals"
    evals.mkdir()
    (evals / "check_result.py").write_text("pass", encoding="utf-8")
    cache = skill / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"\x00")

    template = tmp_path / "template"
    template.mkdir()
    (template / "SKILL.md").write_text(
        "---\nname: verbing-the-noun\n---\n", encoding="utf-8"
    )

    return tmp_path


def test_skill_dirs_excludes_template(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert [d.name for d in pk.skill_dirs(repo)] == ["doing-things"]


def test_skill_dirs_only_filters_to_one(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    assert [d.name for d in pk.skill_dirs(repo, only="doing-things")] == [
        "doing-things"
    ]
    assert pk.skill_dirs(repo, only="nonexistent") == []


def test_package_skill_excludes_dev_content(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    out = tmp_path / "dist"
    out.mkdir()
    dest = pk.package_skill(repo / "doing-things", "1.0.0", out)

    assert dest.name == "doing-things-1.0.0.tar.gz"
    with tarfile.open(dest) as tar:
        names = tar.getnames()

    assert "doing-things/SKILL.md" in names
    assert "doing-things/references/notes.md" in names
    assert not any("evals" in n for n in names)
    assert not any("__pycache__" in n for n in names)
    # The tarball's sole top-level member is the skill name, so it extracts
    # straight into a harness's skills directory.
    assert {Path(n).parts[0] for n in names} == {"doing-things"}


def test_write_checksums(tmp_path: Path) -> None:
    out = tmp_path / "dist"
    out.mkdir()
    f1 = out / "a.tar.gz"
    f1.write_bytes(b"one")
    f2 = out / "b.tar.gz"
    f2.write_bytes(b"two")

    dest = pk.write_checksums([f1, f2], out)
    lines = dest.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    for line in lines:
        digest, name = line.split("  ")
        assert len(digest) == 64
        assert name in {"a.tar.gz", "b.tar.gz"}


def test_main_builds_manifest_and_checksums(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    out = tmp_path / "dist"
    rc = pk.main(["--repo", str(repo), "--version", "2.3.4", "--out", str(out)])

    assert rc == 0
    assert (out / "doing-things-2.3.4.tar.gz").exists()
    assert (out / "SHA256SUMS").exists()


def test_main_reports_unknown_skill(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    rc = pk.main(
        [
            "--repo",
            str(repo),
            "--skill",
            "nonexistent",
            "--version",
            "1.0.0",
            "--out",
            str(tmp_path / "dist"),
        ]
    )
    assert rc == 1
