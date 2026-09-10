"""Tests for scripts/validate_skills.py.

Run with: uv run --with pytest --with 'pyyaml>=6' pytest
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import validate_skills as vs  # on sys.path via tests/conftest.py

GOOD_DESC = "Does a well-scoped thing. Use when the user asks to do that thing."


def make_repo(tmp_path: Path, catalog: str) -> Path:
    (tmp_path / "README.md").write_text(f"# skills\n\n{catalog}\n", encoding="utf-8")
    return tmp_path


def write_skill(repo: Path, name: str, *, fm: str, body: str = "# Title\n") -> Path:
    d = repo / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(f"---\n{fm}\n---\n\n{body}", encoding="utf-8")
    return d


def write_marketplace(
    repo: Path, plugins: list[dict], *, raw: str | None = None
) -> Path:
    d = repo / ".claude-plugin"
    d.mkdir(parents=True, exist_ok=True)
    text = raw if raw is not None else json.dumps({"name": "test", "plugins": plugins})
    (d / "marketplace.json").write_text(text, encoding="utf-8")
    return d / "marketplace.json"


def test_valid_skill_passes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    write_skill(
        repo, "doing-things", fm=f"name: doing-things\ndescription: {GOOD_DESC}"
    )
    write_marketplace(repo, [{"name": "doing-things", "source": "./doing-things"}])
    assert vs.validate_repo(repo) == []


def test_empty_repo_reports(tmp_path: Path) -> None:
    problems = vs.validate_repo(make_repo(tmp_path, "nothing here"))
    assert problems and "no skills found" in problems[0]


def test_template_is_exempt_from_name_match_but_needs_keys(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    write_skill(
        repo, "doing-things", fm=f"name: doing-things\ndescription: {GOOD_DESC}"
    )
    write_skill(
        repo,
        "template",
        fm="name: verbing-the-noun\ndescription: placeholder text here",
    )
    write_marketplace(repo, [{"name": "doing-things", "source": "./doing-things"}])
    assert vs.validate_repo(repo) == []

    write_skill(repo, "template", fm="name: verbing-the-noun")
    assert any(
        "must keep 'name' and 'description'" in p for p in vs.validate_repo(repo)
    )


@pytest.mark.parametrize(
    ("fm", "needle"),
    [
        pytest.param(
            f"name: wrong\ndescription: {GOOD_DESC}",
            "does not match directory name",
            id="name-mismatch",
        ),
        pytest.param(
            f"name: doing-things\ndescription: {GOOD_DESC}\ncontext: fork",
            "non-portable frontmatter",
            id="extra-key",
        ),
        pytest.param(
            f"name: doing-things\ndescription: {GOOD_DESC}\nallowed-tools: Bash",
            "non-portable frontmatter",
            id="allowed-tools",
        ),
        pytest.param(
            "name: doing-things\ndescription: I can help you do things here.",
            "third person",
            id="first-person",
        ),
        pytest.param(
            f"name: Doing_Things\ndescription: {GOOD_DESC}",
            "must match",
            id="bad-name-chars",
        ),
        pytest.param(
            f"name: claude-helper\ndescription: {GOOD_DESC}",
            "reserved word",
            id="reserved-word",
        ),
        pytest.param(
            "name: doing-things\ndescription: ''",
            "non-empty 'description'",
            id="empty-desc",
        ),
        pytest.param(
            f"name: doing-things\ndescription: {'padding ' * 200}",
            "max 1024",
            id="overlong-desc",
        ),
        pytest.param(
            "name: doing-things\ndescription: Wraps <b>text</b> in tags.",
            "XML/HTML tags",
            id="html-in-desc",
        ),
    ],
)
def test_frontmatter_problems(tmp_path: Path, fm: str, needle: str) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    write_skill(repo, "doing-things", fm=fm)
    assert any(needle in p for p in vs.validate_repo(repo))


def test_missing_frontmatter(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    d = repo / "doing-things"
    d.mkdir()
    (d / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
    assert any("missing YAML frontmatter" in p for p in vs.validate_repo(repo))


def test_missing_from_catalog(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "catalog with no entry")
    write_skill(
        repo, "doing-things", fm=f"name: doing-things\ndescription: {GOOD_DESC}"
    )
    assert any("missing from the catalog" in p for p in vs.validate_repo(repo))


def test_body_line_limit(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    write_skill(
        repo,
        "doing-things",
        fm=f"name: doing-things\ndescription: {GOOD_DESC}",
        body="# Title\n" + "\n".join(f"line {i}" for i in range(600)),
    )
    assert any("move detail to references/" in p for p in vs.validate_repo(repo))


def test_link_checks(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    d = write_skill(
        repo,
        "doing-things",
        fm=f"name: doing-things\ndescription: {GOOD_DESC}",
        body="See [x](references/deep/x.md), [y](missing.md), [z](../escape.md), [ok](references/e.md)\n",
    )
    (d / "references" / "deep").mkdir(parents=True)
    (d / "references" / "deep" / "x.md").write_text("x", encoding="utf-8")
    (d / "references" / "e.md").write_text("e", encoding="utf-8")

    problems = "\n".join(vs.validate_repo(repo))
    assert "more than one level deep" in problems
    assert "broken link: missing.md" in problems
    assert "escapes the skill directory: ../escape.md" in problems
    assert "references/e.md" not in problems  # the valid one is not flagged


def test_marketplace_missing_file_reports(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    write_skill(
        repo, "doing-things", fm=f"name: doing-things\ndescription: {GOOD_DESC}"
    )
    assert any("marketplace.json: not found" in p for p in vs.validate_repo(repo))


def test_marketplace_invalid_json_reports(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    write_skill(
        repo, "doing-things", fm=f"name: doing-things\ndescription: {GOOD_DESC}"
    )
    write_marketplace(repo, [], raw="{not json")
    assert any("invalid JSON" in p for p in vs.validate_repo(repo))


def test_marketplace_missing_entry_reports(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    write_skill(
        repo, "doing-things", fm=f"name: doing-things\ndescription: {GOOD_DESC}"
    )
    write_marketplace(repo, [{"name": "someone-else", "source": "./someone-else"}])
    assert any("no matching plugin entry" in p for p in vs.validate_repo(repo))


def test_marketplace_wrong_source_reports(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "| [doing-things](doing-things/SKILL.md) | x |")
    write_skill(
        repo, "doing-things", fm=f"name: doing-things\ndescription: {GOOD_DESC}"
    )
    write_marketplace(repo, [{"name": "doing-things", "source": "./wrong-path"}])
    problems = "\n".join(vs.validate_repo(repo))
    assert "entry has source './wrong-path'" in problems
    assert "expected './doing-things'" in problems


def test_frontmatter_parses_block_scalar() -> None:
    fm, body = vs.frontmatter(
        "---\nname: x\ndescription: >-\n  multi\n  line\n---\nbody\n"
    )
    assert fm == {"name": "x", "description": "multi line"}
    assert body.strip() == "body"
