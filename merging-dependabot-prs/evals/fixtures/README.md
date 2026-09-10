# Fixture repos

`build_fixtures.sh <target-dir>` builds five throwaway git repos that stand in
for a GitHub repo with open Dependabot PRs. There is no GitHub in the loop — each
repo has a `main` branch and one or more `dependabot/*` branches, and the eval
prompt asks Claude to land those branches into `main` locally. The decisions the
skill has to make (merge order, lockfile appends, consolidation, when to stop)
are the same either way.

The target dir is wiped on each run and must not be committed. Package-manager
caches live inside it (`<target>/.cache`) and each npm fixture gets an `.npmrc`
pointing at that cache, so runs work under a restricted `HOME`/sandbox. The
initial `main` commit of every fixture is tagged `eval-base` so the grader can
diff the end state against the starting point.

Requires network (npm registry + PyPI), `node`/`npm`, and `uv`.

| fixture | what's wrong | correct outcome |
| --- | --- | --- |
| `independent-bumps` | three bumps, three separate lockfiles (root, `tools/`, `docs/`) — the `docs/` branch also left its lockfile stale | land all three, any order; catch and append a lockfile regen to the `docs/` branch before landing it; delete local branches |
| `serial-lockfile-conflict` | three bumps share one `package-lock.json`; landing one conflicts the rest | land one, rebase/relock the next, land it, repeat |
| `circular-interdependent` | the test needs BOTH new versions, so each branch is red alone | consolidate both bumps into one commit, relock once, land it |
| `stale-uv-lock` | mixed ecosystems: a clean npm bump in `web/`, and `pyproject.toml` bumped with `uv.lock` left stale (`uv sync --locked` fails) | land the npm bump freely; for the uv one, `uv lock`, commit the lockfile to the branch (authorized append), report it, land |
| `needs-source-change` | `uuid` 3→9 drops the `uuid/v4` subpath that `index.js` imports | STOP: don't edit source, don't merge, report what's needed |

`check_result.py <fixture> <repo>` grades the mechanical expectations against a
repo after a run. Transcript expectations (did it explain the append? did it stop
and ask?) are graded separately by a grader subagent.
