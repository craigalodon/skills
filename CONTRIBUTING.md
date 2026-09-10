# Contributing

Notes to myself (and anyone reusing these) for keeping the collection consistent
and portable.

## Layout

- One skill per top-level directory, flat — no category folders. The catalog
  table in [README.md](README.md) does the grouping.
- Each skill folder is self-contained:

  ```text
  verbing-the-noun/
  ├── SKILL.md            # required
  ├── references/         # optional — docs loaded on demand
  ├── scripts/            # optional — executed, not read into context
  └── assets/             # optional — templates/files used in output
  ```

- Start from [template/SKILL.md](template/SKILL.md).

## Naming

- Gerund form: `merging-dependabot-prs`, `analyzing-spreadsheets`.
- Lowercase letters, numbers, hyphens only. Max 64 chars.
- Never the words `claude` or `anthropic` (reserved).

## Frontmatter

Only two fields, and they must be the portable ones:

- `name` — matches the directory name.
- `description` — third person, ≤1024 chars, says **what** it does **and when**
  to use it, with concrete trigger phrases and artifact names. No first/second
  person.

Optional but still portable: `license`, `metadata`. Do **not** add
harness-specific keys — `allowed-tools`, `context`, `when_to_use`, model hints
(Claude Code), or an `agents/openai.yaml` (Codex). They don't travel and can be
silently ignored or rejected elsewhere.

## Body

- Keep `SKILL.md` under ~500 lines. Push detail into `references/`, linked one
  level deep from `SKILL.md` (nested references get partially read).
- Reference files over ~100 lines get a table of contents.
- Forward-slash paths only, even in examples.
- Explain the *why* behind instructions instead of stacking MUST/NEVER.
- No time-sensitive phrasing ("as of 2026…", "the new API"); use a "legacy"
  subsection if history matters.
- Name external tools explicitly and give a fallback rather than assuming a
  specific CLI or harness is present.

## Before committing

```bash
uvx pre-commit install          # once
uv run scripts/validate_skills.py
rumdl check .                    # or: rumdl fmt
```

CI runs the same checks. The skill validator enforces the checklist below
mechanically, so a green run means the conventions hold.

## Helper scripts

`scripts/` holds CI helpers as single-file scripts with
[PEP 723](https://peps.python.org/pep-0723/) inline dependencies — `uv run`
resolves them, so there is no `pyproject.toml` or lockfile. Keep it that way
until something forces the issue: a second script that shares code with the
first, a dependency beyond the standard library plus PyYAML, or
`validate_skills.py` outgrowing ~250 lines. At that point, promote `scripts/`
to a proper package with `pyproject.toml`.

Lint and test them with `ruff` and `pytest` (both via `uvx` / `uv run --with`,
no install step). Tests live in `tests/` and cover `validate_skills.py`.

## Portability checklist

- [ ] Folder name is gerund, lowercase-hyphen, matches `name`
- [ ] `description` is third person, ≤1024 chars, what + when + triggers
- [ ] No harness-specific frontmatter keys
- [ ] `SKILL.md` under ~500 lines; references one level deep
- [ ] Forward-slash paths throughout
- [ ] External tools have a stated fallback
- [ ] Added a row to the README catalog

## Repo-level agent instructions

If this repo ever needs instructions for an agent working *in* it, put them in
[AGENTS.md](AGENTS.md) (the cross-tool convention), not a harness-specific file.
