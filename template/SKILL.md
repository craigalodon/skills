---
name: verbing-the-noun
description: >-
  Third-person summary of what the skill does, followed by the situations that
  should trigger it. Name concrete artifacts, file types, error messages, and
  phrases a user would actually say ("merge the dependabot PRs", "the uv.lock is
  out of sync"). Keep under 1024 characters. Do not write in first or second
  person ("I can…", "you can…") and do not use the words claude or anthropic.
---

# Verbing the noun

## What this skill is for

One or two paragraphs: the problem, why the naive approach fails, and what doing
it well looks like. Assume the model is already capable — add only the context it
doesn't have.

## Tooling assumptions

State any external tools the workflow leans on and give a fallback, so the skill
stays usable across harnesses and platforms. Use forward-slash paths only.

## Guardrail: autonomous vs. sign-off

Spell out what may be done without asking and what must stop for approval. Explain
the reasoning rather than relying on bare MUST/NEVER.

## Steps

Number the workflow. Each step: the command or action, then how to tell whether
it worked and what to do when it doesn't.

## References

Link one level deep from this file. Put long or domain-specific material in
`references/<topic>.md` with a table of contents if it exceeds ~100 lines.
