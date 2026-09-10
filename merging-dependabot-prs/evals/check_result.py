#!/usr/bin/env python3
"""Mechanical grader for merging-dependabot-prs eval fixtures.

Given a scenario id and the path to a fixture repo *after* an eval run has
operated on it, emit the objectively-checkable expectations as JSON in the
shape grading.json expects:

    {"expectations": [{"text": ..., "passed": bool, "evidence": ...}], ...}

Transcript-based checks (did the model explain the append? did it stop and
ask?) are left to the grader subagent — this script only inspects the repo.

Usage:
    python check_result.py <scenario> <repo-path> [--json]

Scenarios: independent-bumps serial-lockfile-conflict circular-interdependent
           stale-uv-lock needs-source-change
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCENARIOS = {
    "independent-bumps",
    "serial-lockfile-conflict",
    "circular-interdependent",
    "stale-uv-lock",
    "needs-source-change",
}


def sh(repo: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=repo, capture_output=True, text=True, check=check)


def git(repo: Path, *args: str) -> str:
    return sh(repo, "git", *args).stdout.strip()


def npm_env(repo: Path) -> dict:
    """Environment with a writable npm/uv cache, discovered next to the fixtures."""
    env = dict(os.environ)
    for parent in [repo, *repo.parents]:
        cache = parent / ".cache"
        if (cache / "npm").is_dir():
            env.setdefault("npm_config_cache", str(cache / "npm"))
            env.setdefault("UV_CACHE_DIR", str(cache / "uv"))
            break
    return env


def file_at(repo: Path, ref: str, path: str) -> str | None:
    r = sh(repo, "git", "show", f"{ref}:{path}")
    return r.stdout if r.returncode == 0 else None


def dep_version(repo: Path, ref: str, manifest: str, name: str) -> str | None:
    raw = file_at(repo, ref, manifest)
    if raw is None:
        return None
    if manifest.endswith(".json"):
        data = json.loads(raw)
        for key in ("dependencies", "devDependencies", "optionalDependencies"):
            if name in data.get(key, {}):
                return str(data[key][name])
        return None
    # pyproject.toml: find the dependency spec string
    m = re.search(rf'["\']{re.escape(name)}\s*([^"\']*)["\']', raw)
    return m.group(1).strip() if m else None


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    out = git(repo, "diff", "--name-only", f"{base}..{head}")
    return [line for line in out.splitlines() if line]


def run_cmd(repo: Path, *cmd: str, cwd: Path | None = None) -> tuple[bool, str]:
    r = subprocess.run(
        cmd,
        cwd=cwd or repo,
        capture_output=True,
        text=True,
        env=npm_env(repo),
        check=False,
    )
    tail = (r.stdout + r.stderr).strip().splitlines()
    return r.returncode == 0, " / ".join(tail[-3:])[:400]


# --------------------------------------------------------------------------


def check_independent_bumps(repo: Path) -> list[dict]:
    exp: list[dict] = []
    want = {
        ("package.json", "semver"): "7.6.3",
        ("tools/package.json", "ms"): "2.1.3",
        ("docs/package.json", "picocolors"): "1.1.0",
    }
    got = {k: dep_version(repo, "main", *k) for k in want}
    exp.append(
        {
            "text": "all three bumps landed on main (semver 7.6.3, tools/ ms 2.1.3, docs/ picocolors 1.1.0)",
            "passed": all(got[k] == v for k, v in want.items()),
            "evidence": "; ".join(
                f"{mf}:{name}={got[(mf, name)]!r}" for mf, name in want
            ),
        }
    )
    changed = changed_files(repo, "eval-base", "main")
    allowed = {
        f"{d}{f}"
        for d in ("", "tools/", "docs/")
        for f in ("package.json", "package-lock.json")
    }
    stray = sorted(set(changed) - allowed)
    exp.append(
        {
            "text": "only manifests and lockfiles changed between eval-base and main",
            "passed": not stray and bool(changed),
            "evidence": f"changed: {changed or 'nothing'}; unexpected: {stray or 'none'}",
        }
    )
    git(repo, "checkout", "-qf", "main")
    for pkg in ("", "tools", "docs"):
        cwd = repo / pkg if pkg else repo
        ok_ci, ev = run_cmd(repo, "npm", "ci", "--no-audit", "--no-fund", cwd=cwd)
        ok_t, _ = run_cmd(repo, "node", "test.js", cwd=cwd)
        label = pkg or "root"
        exp.append(
            {
                "text": f"{label} package installs cleanly (npm ci) and its test passes on main",
                "passed": ok_ci and ok_t,
                "evidence": f"{label}: npm ci ok={ok_ci}; test ok={ok_t} ({ev})",
            }
        )
    return exp


def check_serial(repo: Path) -> list[dict]:
    exp: list[dict] = []
    want = {"semver": "7.6.3", "picocolors": "1.1.0", "ms": "2.1.3"}
    got = {n: dep_version(repo, "main", "package.json", n) for n in want}
    exp.append(
        {
            "text": "all three bumps landed on main (semver 7.6.3, picocolors 1.1.0, ms 2.1.3)",
            "passed": got == want,
            "evidence": f"got {got}",
        }
    )
    git(repo, "checkout", "-qf", "main")
    ok_ci, ev = run_cmd(repo, "npm", "ci", "--no-audit", "--no-fund")
    exp.append(
        {
            "text": "npm ci succeeds on main (package-lock.json consistent with package.json)",
            "passed": ok_ci,
            "evidence": ev,
        }
    )
    ok_t, ev_t = run_cmd(repo, "node", "test.js")
    exp.append(
        {
            "text": "the test passes on main",
            "passed": ok_t,
            "evidence": ev_t,
        }
    )
    changed = changed_files(repo, "eval-base", "main")
    stray = sorted(set(changed) - {"package.json", "package-lock.json"})
    exp.append(
        {
            "text": "only package.json and package-lock.json changed",
            "passed": not stray and bool(changed),
            "evidence": f"changed: {changed or 'nothing'}; unexpected: {stray or 'none'}",
        }
    )
    return exp


def check_circular(repo: Path) -> list[dict]:
    exp: list[dict] = []
    sv = dep_version(repo, "main", "package.json", "semver")
    ms = dep_version(repo, "main", "package.json", "ms")
    exp.append(
        {
            "text": "both semver (7.6.3) and ms (2.1.3) are bumped on main",
            "passed": sv == "7.6.3" and ms == "2.1.3",
            "evidence": f"semver={sv!r} ms={ms!r}",
        }
    )
    git(repo, "checkout", "-qf", "main")
    ok_ci, _ = run_cmd(repo, "npm", "ci", "--no-audit", "--no-fund")
    ok_t, ev_t = run_cmd(repo, "node", "test.js")
    exp.append(
        {
            "text": "the combined result passes the test on main",
            "passed": ok_ci and ok_t,
            "evidence": f"npm ci ok={ok_ci}; node test.js ok={ok_t} ({ev_t})",
        }
    )
    # No broken intermediate landed: every commit from eval-base..main must
    # pass the test. This is what distinguishes consolidation from "merged a
    # red branch, then fixed it".
    revs = git(repo, "rev-list", "--reverse", "eval-base..main").splitlines()
    broken = []
    for rev in revs:
        git(repo, "checkout", "-qf", rev)
        run_cmd(
            repo,
            "npm",
            "install",
            "--no-audit",
            "--no-fund",
            "--package-lock-only",
            "--ignore-scripts",
        )
        run_cmd(repo, "npm", "ci", "--no-audit", "--no-fund")
        ok, _ = run_cmd(repo, "node", "test.js")
        if not ok:
            broken.append(rev[:9])
    git(repo, "checkout", "-qf", "main")
    exp.append(
        {
            "text": "no broken intermediate commit was landed on main (deps bumped together, not one at a time)",
            "passed": not broken,
            "evidence": f"{len(revs)} commit(s) after eval-base; failing: {broken or 'none'}",
        }
    )
    changed = changed_files(repo, "eval-base", "main")
    stray = sorted(set(changed) - {"package.json", "package-lock.json"})
    exp.append(
        {
            "text": "only package.json and package-lock.json changed",
            "passed": not stray and bool(changed),
            "evidence": f"changed: {changed or 'nothing'}; unexpected: {stray or 'none'}",
        }
    )
    return exp


def check_stale_uv(repo: Path) -> list[dict]:
    exp: list[dict] = []
    # The skill may land to main or leave a fixed branch; check whichever ref
    # carries the bump.
    ref = "main"
    spec = dep_version(repo, "main", "pyproject.toml", "idna")
    if not spec or "3.7" not in spec:
        for b in git(repo, "branch", "--format=%(refname:short)").splitlines():
            s = dep_version(repo, b.strip(), "pyproject.toml", "idna")
            if s and "3.7" in s:
                ref, spec = b.strip(), s
                break
    exp.append(
        {
            "text": "idna requirement is raised to 3.7 in pyproject.toml",
            "passed": bool(spec) and "3.7" in spec,
            "evidence": f"{ref}:pyproject.toml idna spec = {spec!r}",
        }
    )
    git(repo, "checkout", "-qf", ref)
    ok_lock, ev = run_cmd(repo, "uv", "sync", "--locked")
    exp.append(
        {
            "text": "uv.lock is back in sync with pyproject.toml (uv sync --locked succeeds)",
            "passed": ok_lock,
            "evidence": ev,
        }
    )
    lock_raw = file_at(repo, ref, "uv.lock") or ""
    exp.append(
        {
            "text": "uv.lock was regenerated and committed (pins idna 3.7)",
            "passed": 'name = "idna"' in lock_raw and 'version = "3.7"' in lock_raw,
            "evidence": "uv.lock idna pin: "
            + ("3.7" if 'version = "3.7"' in lock_raw else "not 3.7 / not committed"),
        }
    )
    ok_t, ev_t = run_cmd(repo, "uv", "run", "--locked", "pytest", "-q")
    exp.append(
        {
            "text": "the test suite passes after the lockfile sync",
            "passed": ok_t,
            "evidence": ev_t,
        }
    )
    changed = changed_files(repo, "eval-base", ref)
    allowed = {"pyproject.toml", "uv.lock", "web/package.json", "web/package-lock.json"}
    stray = sorted(set(changed) - allowed)
    exp.append(
        {
            "text": "only manifests and lockfiles changed (no source edits)",
            "passed": not stray,
            "evidence": f"changed: {changed or 'nothing'}; unexpected: {stray or 'none'}",
        }
    )
    # The independent npm bump in web/ must also have landed and still build.
    web_ms = dep_version(repo, ref, "web/package.json", "ms")
    git(repo, "checkout", "-qf", ref)
    ok_web, ev_web = run_cmd(
        repo, "npm", "ci", "--no-audit", "--no-fund", cwd=repo / "web"
    )
    exp.append(
        {
            "text": "the independent npm bump in web/ also landed (ms 2.1.3) and web/ installs cleanly",
            "passed": web_ms == "2.1.3" and ok_web,
            "evidence": f"web/package.json ms = {web_ms!r}; npm ci ok={ok_web} ({ev_web})",
        }
    )
    return exp


def check_needs_source_change(repo: Path) -> list[dict]:
    exp: list[dict] = []
    uuid_main = dep_version(repo, "main", "package.json", "uuid")
    exp.append(
        {
            "text": "the uuid bump was NOT merged to main (still 3.4.0)",
            "passed": uuid_main == "3.4.0",
            "evidence": f"main:package.json uuid = {uuid_main!r}",
        }
    )
    # index.js must be untouched on every ref and in the worktree.
    base_index = file_at(repo, "eval-base", "index.js")
    edited_refs = []
    for ref in [
        "main",
        *[
            b.strip()
            for b in git(repo, "branch", "--format=%(refname:short)").splitlines()
        ],
    ]:
        if file_at(repo, ref, "index.js") != base_index:
            edited_refs.append(ref)
    worktree_index = (
        (repo / "index.js").read_text() if (repo / "index.js").exists() else None
    )
    exp.append(
        {
            "text": "index.js was never modified (no source change attempted)",
            "passed": not edited_refs and worktree_index == base_index,
            "evidence": f"refs with edited index.js: {edited_refs or 'none'}; "
            f"worktree matches base: {worktree_index == base_index}",
        }
    )
    changed = changed_files(repo, "eval-base", "main")
    exp.append(
        {
            "text": "main is unchanged from eval-base (nothing was force-landed)",
            "passed": not changed,
            "evidence": f"changed: {changed or 'nothing'}",
        }
    )
    return exp


CHECKS = {
    "independent-bumps": check_independent_bumps,
    "serial-lockfile-conflict": check_serial,
    "circular-interdependent": check_circular,
    "stale-uv-lock": check_stale_uv,
    "needs-source-change": check_needs_source_change,
}


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--json"]
    if len(args) != 2 or args[0] not in SCENARIOS:
        print(__doc__, file=sys.stderr)
        return 2
    scenario, repo = args[0], Path(args[1]).resolve()
    if not (repo / ".git").exists():
        print(f"not a git repo: {repo}", file=sys.stderr)
        return 2

    starting_branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    try:
        expectations = CHECKS[scenario](repo)
    finally:
        sh(repo, "git", "checkout", "-qf", starting_branch or "main")

    passed = sum(1 for e in expectations if e["passed"])
    total = len(expectations)
    result = {
        "scenario": scenario,
        "expectations": expectations,
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "pass_rate": round(passed / total, 3) if total else 0.0,
        },
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
