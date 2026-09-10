# skills

A personal collection of [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) —
reusable, model-invoked workflows packaged as plain folders. Each skill is a
directory with a `SKILL.md` and optional `references/`, `scripts/`, and
`assets/`.

These skills stick to the portable subset of the format (`name` + `description`
frontmatter, markdown body, forward-slash paths, no harness-specific fields), so
the same folder works across Claude Code, Codex CLI, OpenCode, Cursor, Gemini
CLI, and other SKILL.md-compatible runtimes. See [CONTRIBUTING.md](CONTRIBUTING.md)
for the portability rules.

## Catalog

| Skill | What it does |
| --- | --- |
| [merging-dependabot-prs](merging-dependabot-prs/SKILL.md) | Review, verify locally, and merge a repo's open Dependabot PRs as one batch — merge order, interdependent bumps, stale lockfiles, and cleanup. |

## Installing a skill

Skills are discovered per-harness from that tool's skills directory. Copy (or
symlink) the skill folder into the right place:

| Harness | Personal (all projects) | Project-scoped |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/<skill>/` | `.claude/skills/<skill>/` |
| Codex CLI | `~/.codex/skills/<skill>/` | `.codex/skills/<skill>/` |
| OpenCode | `~/.config/opencode/skills/<skill>/` | `.opencode/skills/<skill>/` |

```bash
# example: install one skill for Claude Code
cp -R merging-dependabot-prs ~/.claude/skills/

# or symlink so it tracks this repo
ln -s "$PWD/merging-dependabot-prs" ~/.claude/skills/merging-dependabot-prs
```

Restart or reload the harness so it picks up the new skill, then give it a task
matching the skill's description and confirm it loads.

## Adding a skill

Copy [template/SKILL.md](template/SKILL.md) into a new gerund-named folder
(`verbing-the-noun/`) and fill it in. Keep `SKILL.md` under ~500 lines; move
detail into `references/`. Read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## Development

```bash
uvx pre-commit install
```

Pre-commit and [CI](.github/workflows/ci.yml) run the same checks on every push
to `main` and every pull request:

- **Repository hygiene** — large files, merge-conflict markers, TOML/YAML
  validity, trailing whitespace, end-of-file newlines
  ([pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks)).
- **Markdown linting** — [rumdl](https://github.com/rvben/rumdl), configured in
  [.rumdl.toml](.rumdl.toml). Autofix with `rumdl fmt`.
- **Skill validation** — [scripts/validate_skills.py](scripts/validate_skills.py)
  checks every `SKILL.md` against the portability rules in
  [CONTRIBUTING.md](CONTRIBUTING.md): portable frontmatter only, `name` matches
  the folder, third-person `description` within the length limit, references one
  level deep with no broken or escaping links, and a catalog entry in this
  README. Run it directly with `uv run scripts/validate_skills.py`; its own
  tests are `uv run --with pytest --with pyyaml>=6 pytest -q`.
- **Script hygiene** — `ruff` check + format on `scripts/` and `tests/`.

## License

[MIT](LICENSE).
