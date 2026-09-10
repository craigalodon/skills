# Evals for `merging-dependabot-prs`

Two independent test surfaces:

## Behavioral (`evals.json` + `fixtures/` + `check_result.py`)

Does Claude actually run the workflow correctly? Five scenarios, each a local git
repo built by [`fixtures/build_fixtures.sh`](fixtures/build_fixtures.sh) that
stands in for a repo with open Dependabot PRs. See
[`fixtures/README.md`](fixtures/README.md).

Run one iteration by hand:

```bash
# 1. build fresh fixtures (network needed: npm + PyPI)
bash fixtures/build_fixtures.sh /tmp/mdp-eval/fixtures

# 2. for each eval, give Claude the prompt from evals.json with {repo}
#    replaced by a fresh COPY of the fixture (runs mutate the repo):
cp -r /tmp/mdp-eval/fixtures/independent-bumps /tmp/mdp-eval/run-0
#    ...run Claude with the skill, then without it (baseline)...

# 3. grade the mechanical expectations
python evals/check_result.py independent-bumps /tmp/mdp-eval/run-0
```

`check_result.py` emits `{"expectations": [{text, passed, evidence}], ...}` —
the same shape `grading.json` uses, so it drops straight into skill-creator's
`aggregate_benchmark.py`. The transcript-only expectations in `evals.json`
(explaining an append, stopping to ask) are graded by a grader subagent, not the
script.

The full loop (with-skill vs. without-skill subagents, benchmark, HTML viewer)
is driven with the `skill-creator` skill.

## Triggering (`trigger-eval-set.json`)

Should the skill fire for a given user query, and not fire for near-misses? Fed
to skill-creator's description optimizer:

```bash
cd <skill-creator>/skills/skill-creator
python -m scripts.run_loop \
  --eval-set <this-dir>/trigger-eval-set.json \
  --skill-path <repo>/merging-dependabot-prs \
  --model <session-model-id> --max-iterations 5 --holdout 0.4 --verbose
```

The optimizer proposes description rewrites, scores each on a held-out split, and
returns the best. Any description that lands in `SKILL.md` must still pass
`scripts/validate_skills.py` (≤1024 chars, third person, no tags).
