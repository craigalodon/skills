# AGENTS.md

Guidance for an AI agent working in this repository.

## What this repo is

A collection of portable Agent Skills. Each top-level directory is one skill
(`SKILL.md` + optional `references/`, `scripts/`, `assets/`). It is a source
repository, not an installed skills directory — nothing here runs until a skill
folder is copied or symlinked into a harness's own skills path.

## When editing or adding a skill

Follow [CONTRIBUTING.md](CONTRIBUTING.md). The load-bearing rules:

- Keep skills portable: only `name` + `description` (and optionally `license` /
  `metadata`) in frontmatter; no harness-specific keys.
- `description` is third person, ≤1024 chars, and states what the skill does and
  when it should trigger.
- `SKILL.md` under ~500 lines; detail goes in `references/`, linked one level
  deep.
- Update the catalog table in [README.md](README.md) when adding or renaming a
  skill.

## Validate before committing

- `SKILL.md` frontmatter parses as YAML and has `name` + `description`.
- `name` equals the directory name.
- All intra-skill links resolve and are one level deep.
- No `\` in any path.
