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

### From a release

Each skill is tagged and released on its own: `<skill>/v<version>`
(e.g. `merging-dependabot-prs/v1.0.0`). A tag's
[Release](https://github.com/craigalodon/skills/releases) carries a
`<skill>-<version>.tar.gz` whose sole top-level entry is the skill folder, plus
a `SHA256SUMS` — download it and extract straight into a harness's skills
directory:

```bash
curl -LO https://github.com/craigalodon/skills/releases/download/merging-dependabot-prs/v1.0.0/merging-dependabot-prs-1.0.0.tar.gz
tar -xzf merging-dependabot-prs-1.0.0.tar.gz -C ~/.claude/skills/
```

This gives an immutable, checksummed snapshot instead of whatever `main`
happens to hold — useful when pinning a version or scripting an install.

### Claude Code plugin

Claude Code users can install a skill as a plugin instead, with updates gated
to explicit version bumps rather than every commit to `main`:

```text
/plugin marketplace add craigalodon/skills
/plugin install merging-dependabot-prs@craig-skills
```

The marketplace is [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json)
— every skill is also a single-skill plugin, sourced from its own folder.

## Adding a skill

Copy [template/SKILL.md](template/SKILL.md) into a new gerund-named folder
(`verbing-the-noun/`) and fill it in. Keep `SKILL.md` under ~500 lines; move
detail into `references/`. Add a row to the catalog above and a matching entry
in [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json). Read
[CONTRIBUTING.md](CONTRIBUTING.md) first.

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
  level deep with no broken or escaping links, a catalog entry in this README,
  and a matching plugin entry in `.claude-plugin/marketplace.json`. Run it
  directly with `uv run scripts/validate_skills.py`; its own tests (and
  [scripts/package_skills.py](scripts/package_skills.py)'s) are
  `uv run --with pytest --with pyyaml>=6 pytest -q`.
- **Script hygiene** — `ruff` check + format on `scripts/` and `tests/`.

## Releasing a skill

Each skill is versioned and released independently. See
[.github/workflows/release.yml](.github/workflows/release.yml):

1. In a PR, bump that skill's `version` in
   [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json) (plus any
   skill changes) and merge it to `main`.
2. Tag the merged commit `<skill>/v<version>` and push the tag:

   ```bash
   git tag merging-dependabot-prs/v1.0.0
   git push origin merging-dependabot-prs/v1.0.0
   ```

The workflow re-validates the skill, packages `<skill>-<version>.tar.gz` +
`SHA256SUMS`, refuses to publish if the tag's version doesn't match the
`marketplace.json` entry, and publishes a GitHub Release with notes scoped to
that skill's history. `workflow_dispatch` (with `skill` and `version` inputs)
runs the same packaging as a dry run — it uploads the tarball as a workflow
artifact instead of publishing a release.

## License

[MIT](LICENSE).
