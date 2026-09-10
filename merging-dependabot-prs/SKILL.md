---
name: merging-dependabot-prs
description: >-
  Reviews and merges a repository's open Dependabot pull requests as one
  coordinated batch: reads the whole set first, works out a safe merge order,
  resolves interdependent version bumps, verifies each change builds and tests
  locally, appends a lockfile-sync commit when Dependabot left a lockfile stale,
  then merges and cleans up local branches. Use when several Dependabot PRs are
  open and need to land, when dependency-update PRs are failing CI because of
  interdependent bumps or an out-of-sync lockfile (uv.lock, poetry.lock,
  package-lock.json, yarn.lock, pnpm-lock.yaml, Cargo.lock, go.sum,
  Gemfile.lock), or when asked to "merge the Dependabot PRs", "clear the
  dependency backlog", "get the bot PRs in", or "handle the dependabot updates".
  Also applies to a single Dependabot PR that needs local verification or a
  lockfile fix before it can merge.
---

# Merging Dependabot PRs

## What this skill is for

Dependabot opens one PR per dependency (or per configured group). Merged one at a
time without looking at the whole set, they fight each other: two PRs that touch
the same lockfile conflict the moment the first lands, and a pair of bumps that
only pass CI *together* (package A's new version needs package B's new version)
each fail forever on their own. The job is to read the whole batch first, land it
in an order that works, and fix the small mechanical gaps Dependabot leaves
behind — without quietly turning a dependency bump into a code change.

## Tooling assumptions

This skill is written to be harness- and platform-neutral. The examples use
GitHub's `gh` CLI because GitHub + Dependabot is the common case; if `gh` is
unavailable or the repo is on another platform, use the equivalent PR API,
`glab`, or the web UI — the workflow and the decisions are identical. Everything
else is plain `git` plus the project's own build/test commands.

## Guardrail: what to do autonomously vs. what needs sign-off

Invoking this skill authorizes these actions on the Dependabot PRs in question:

- checking out branches, building, and running tests locally;
- appending a commit to a Dependabot PR branch **only** to regenerate a lockfile
  or otherwise re-sync generated files to the manifest change Dependabot already
  made;
- replacing a set of circularly-dependent PRs with one new PR that performs all
  their manifest updates in a single commit;
- merging the PRs and deleting the merged branches.

Report every append and every consolidation, with the reason.

**Stop and ask first** if landing the updates appears to need anything beyond
editing dependency manifests and their generated lockfiles — source-code changes
for a breaking API, a config-file migration, a build-script change, test edits.
Summarize what's needed and wait for approval.

Also surface, before merging, any major-version bump where a breaking change is
plausible even though CI is green — name it and let the user decide.

## Step 1 — Inventory the open Dependabot PRs

```bash
gh pr list --state open --author "app/dependabot" \
  --json number,title,headRefName,labels,createdAt,mergeStateStatus,statusCheckRollup \
  --limit 100
```

Read `.github/dependabot.yml` if present — it shows which ecosystems and
directories are in play and whether updates are grouped.

## Step 2 — Review the whole set before touching anything

For each PR:

```bash
gh pr view <n> --json title,body,files,additions,deletions,mergeStateStatus,statusCheckRollup
gh pr diff <n>
```

Capture, per PR: ecosystem, package(s), from → to version, bump size
(patch / minor / major), whether it's a security update (label `security`), which
files it touches, and current CI state. A short written table helps once there
are more than a few.

## Step 3 — Plan the merge order

Classify the batch:

- **Independent** — different manifests / ecosystems, no shared lockfile. Order
  doesn't matter; merge them and the rest only need a rebase.
- **Serially conflicting** — several PRs edit the same manifest or lockfile, so
  each merge invalidates the others. Merge one, then for each remaining PR either
  comment `@dependabot rebase` and wait, or rebase locally (the branch is already
  checked out in Step 4: `git rebase origin/<default-branch>`, regenerate the
  lockfile to resolve it, push).
- **Interdependent / circular** — bump A only passes CI with bump B and vice
  versa, so neither PR is green alone. Consolidate: branch off the default
  branch, apply every manifest change from the group, regenerate the lockfile
  once, open a single PR whose body lists `Closes #<n>` for each replaced PR.
  Verify locally (Step 4) before merging; the superseded PRs close automatically.

Security updates go first within whatever order you choose.

## Step 4 — Check out, build, and test locally before merging

Don't merge on the strength of the CI badge alone. Check out the branch and run
the project's real build and test locally.

```bash
gh pr checkout <n>
```

Detect the project type and run its install / build / test commands. See
[references/ecosystems.md](references/ecosystems.md) for per-ecosystem commands
and for how to recognize and regenerate a stale lockfile. Prefer commands
documented in the repo (README, CONTRIBUTING, CI config) over guessing.

If the build or tests fail:

- **Stale lockfile** — manifest changed, lockfile not regenerated (common with
  `uv.lock`, and with grouped updates). Regenerate per
  `references/ecosystems.md`, commit to the PR branch, push. Authorized append.
- **Anything needing a source / config / build change** — stop, per the
  guardrail.

## Step 5 — Merge

Match the repo's configured merge method and history style:

```bash
gh repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed
```

Wait for required checks to pass on the final commit, then:

```bash
gh pr merge <n> --squash --delete-branch   # or --merge / --rebase to match the repo
```

If branch protection needs a review approval you can't provide, or a merge queue
is in play, hand back: list the PRs that are ready and ask the user to approve or
merge. After each merge, update the next branch (rebase comment or local rebase)
before continuing.

## Step 6 — Clean up local state

Once every PR is merged (unless the user asked to stop short of this):

```bash
git checkout <default-branch>
git pull --ff-only
git fetch --prune
# delete local branches already merged into the default branch;
# -d refuses to delete anything not yet merged, so this is safe
git for-each-ref --format='%(refname:short)' refs/heads/ \
  | grep -E '^dependabot/' \
  | xargs -r -n1 git branch -d
```

Report what merged, anything appended or consolidated, and anything still open
and why.
