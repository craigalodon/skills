#!/usr/bin/env bash
# Build local git fixture repos that stand in for a GitHub repo with open
# Dependabot PRs. Each repo gets a `main` branch plus one or more
# `dependabot/*` branches; there is no GitHub — the eval prompt asks Claude to
# land the branches into `main` locally, which exercises the same decisions the
# skill makes against real PRs.
#
# Usage:  build_fixtures.sh <target-dir>
#
# The target dir is wiped and recreated. Package-manager caches are kept inside
# it (<target>/.cache) so runs work under a restricted HOME/sandbox; each npm
# fixture gets an .npmrc pointing at that cache, and this script exports
# UV_CACHE_DIR for the uv fixture. Nothing here is machine-specific once
# regenerated, so the target dir is disposable and must not be committed.
set -euo pipefail

TARGET="${1:?usage: build_fixtures.sh <target-dir>}"
TARGET="$(cd "$(dirname "$TARGET")" && pwd)/$(basename "$TARGET")"

rm -rf "$TARGET"
mkdir -p "$TARGET/.cache/npm" "$TARGET/.cache/uv"
export npm_config_cache="$TARGET/.cache/npm"
export UV_CACHE_DIR="$TARGET/.cache/uv"
NPM_FLAGS="--no-audit --no-fund --silent"

git_init() {
  git init -q "$1"
  git -C "$1" config user.email "fixtures@example.invalid"
  git -C "$1" config user.name "Fixture Builder"
  git -C "$1" config commit.gpgsign false
  printf 'node_modules/\n.venv/\n' > "$1/.gitignore"
}

commit_all() { git -C "$1" add -A && git -C "$1" commit -q -m "$2"; }

# Tag the initial main commit so graders can diff the end state against it.
tag_base() { git -C "$1" tag -f eval-base main >/dev/null; }

npmrc() { printf 'cache=%s\naudit=false\nfund=false\n' "$npm_config_cache" > "$1/.npmrc"; }

echo "Building fixtures in $TARGET"

# ---------------------------------------------------------------------------
# 1. independent-bumps
#    Three npm packages, three separate lockfiles: root (semver), tools/ (ms),
#    docs/ (picocolors). Three dependabot branches, one per package, so order
#    is irrelevant. The catch: the docs/ branch bumped package.json but left
#    package-lock.json stale, so `npm ci` in docs/ fails. Merging on the CI
#    badge alone leaves docs/ broken on main; the fix is to check each branch
#    locally and append a lockfile regen to the docs/ branch before landing.
# ---------------------------------------------------------------------------
f1="$TARGET/independent-bumps"
git_init "$f1"
npmrc "$f1"
mkdir -p "$f1/tools" "$f1/docs"
cat > "$f1/package.json" <<'EOF'
{
  "name": "independent-bumps",
  "version": "1.0.0",
  "private": true,
  "dependencies": { "semver": "7.5.4" },
  "scripts": { "test": "node test.js" }
}
EOF
cat > "$f1/tools/package.json" <<'EOF'
{
  "name": "independent-bumps-tools",
  "version": "1.0.0",
  "private": true,
  "dependencies": { "ms": "2.1.2" },
  "scripts": { "test": "node test.js" }
}
EOF
cat > "$f1/docs/package.json" <<'EOF'
{
  "name": "independent-bumps-docs",
  "version": "1.0.0",
  "private": true,
  "dependencies": { "picocolors": "1.0.0" },
  "scripts": { "test": "node test.js" }
}
EOF
cat > "$f1/test.js" <<'EOF'
const semver = require("semver");
if (!semver.gte(require("semver/package.json").version, "7.5.4")) process.exit(1);
console.log("root ok", require("semver/package.json").version);
EOF
cat > "$f1/tools/test.js" <<'EOF'
const v = require("ms/package.json").version;
const [a, b, c] = v.split(".").map(Number);
if (a * 10000 + b * 100 + c < 20102) process.exit(1);
console.log("tools ok", v);
EOF
cat > "$f1/docs/test.js" <<'EOF'
console.log("docs ok", require("picocolors/package.json").version);
EOF
cat > "$f1/README.md" <<'EOF'
# independent-bumps

Three npm packages, three lockfiles: `./` (semver), `./tools` (ms), `./docs`
(picocolors). Install/test each with `npm --prefix <dir> ci` and
`npm --prefix <dir> test`. `npm ci` fails if a package's lockfile is stale.
EOF
( cd "$f1" && npm install $NPM_FLAGS && npm --prefix tools install $NPM_FLAGS && npm --prefix docs install $NPM_FLAGS )
commit_all "$f1" "chore: scaffold independent-bumps fixture"
tag_base "$f1"

git -C "$f1" checkout -q -b dependabot/npm_and_yarn/semver-7.6.3
( cd "$f1" && npm pkg set dependencies.semver=7.6.3 && npm install $NPM_FLAGS )
commit_all "$f1" "build(deps): bump semver from 7.5.4 to 7.6.3"

git -C "$f1" checkout -q main
git -C "$f1" checkout -q -b dependabot/npm_and_yarn/tools/ms-2.1.3
( cd "$f1/tools" && npm pkg set dependencies.ms=2.1.3 && npm install $NPM_FLAGS )
commit_all "$f1" "build(deps): bump ms from 2.1.2 to 2.1.3 in /tools"

git -C "$f1" checkout -q main
git -C "$f1" checkout -q -b dependabot/npm_and_yarn/docs/picocolors-1.1.0
# Manifest bumped, lockfile deliberately left stale (npm install NOT run).
( cd "$f1/docs" && npm pkg set dependencies.picocolors=1.1.0 )
commit_all "$f1" "build(deps): bump picocolors from 1.0.0 to 1.1.0 in /docs"
git -C "$f1" checkout -q main

# ---------------------------------------------------------------------------
# 2. serial-lockfile-conflict
#    One package.json, THREE branches bump three different deps. Each branch
#    regenerated its own lockfile, but all three edit the same
#    package-lock.json, so landing one invalidates the other two, and landing
#    the second invalidates the third. A blind "merge all three" conflicts
#    partway. Correct play: land one, rebase/relock the next, land it, repeat.
# ---------------------------------------------------------------------------
f2="$TARGET/serial-lockfile-conflict"
git_init "$f2"
npmrc "$f2"
cat > "$f2/package.json" <<'EOF'
{
  "name": "serial-lockfile-conflict",
  "version": "1.0.0",
  "private": true,
  "dependencies": { "semver": "7.5.4", "picocolors": "1.0.0", "ms": "2.1.2" },
  "scripts": { "test": "node test.js" }
}
EOF
cat > "$f2/test.js" <<'EOF'
const s = require("semver/package.json").version;
const p = require("picocolors/package.json").version;
const m = require("ms/package.json").version;
console.log("versions", s, p, m);
if (require("semver").major(s) !== 7) process.exit(1);
EOF
cat > "$f2/README.md" <<'EOF'
# serial-lockfile-conflict

One `package.json` with `semver`, `picocolors`, and `ms`. Three `dependabot/*`
branches bump one dep each; all touch `package-lock.json`. Verify with `npm ci`
then `npm test`.
EOF
( cd "$f2" && npm install $NPM_FLAGS )
commit_all "$f2" "chore: scaffold serial-lockfile-conflict fixture"
tag_base "$f2"

for dep in semver:7.5.4:7.6.3 picocolors:1.0.0:1.1.0 ms:2.1.2:2.1.3; do
  name="${dep%%:*}"; to="${dep##*:}"
  git -C "$f2" checkout -q -b "dependabot/npm_and_yarn/$name-$to" main
  ( cd "$f2" && npm pkg set "dependencies.$name=$to" && npm install $NPM_FLAGS )
  commit_all "$f2" "build(deps): bump $name to $to"
  git -C "$f2" checkout -q main
done

# ---------------------------------------------------------------------------
# 3. circular-interdependent
#    test.js requires BOTH new versions. Each branch bumps only one dep, so
#    each branch fails `npm test` on its own; only both together pass. Correct
#    play: consolidate into a single branch/commit that bumps both, regenerate
#    the lock once, land that.
# ---------------------------------------------------------------------------
f3="$TARGET/circular-interdependent"
git_init "$f3"
npmrc "$f3"
cat > "$f3/package.json" <<'EOF'
{
  "name": "circular-interdependent",
  "version": "1.0.0",
  "private": true,
  "dependencies": { "semver": "7.5.4", "ms": "2.1.2" },
  "scripts": { "test": "node test.js" }
}
EOF
cat > "$f3/test.js" <<'EOF'
// This project only works once BOTH deps are on their new versions.
const semver = require("semver");
const s = require("semver/package.json").version;
const m = require("ms/package.json").version;
const ok = semver.gte(s, "7.6.0") && semver.gte(semver.coerce(m), "2.1.3");
if (!ok) {
  console.error(`incompatible: semver ${s} (need >=7.6.0), ms ${m} (need >=2.1.3)`);
  process.exit(1);
}
console.log("compatible", s, m);
EOF
cat > "$f3/README.md" <<'EOF'
# circular-interdependent

`test.js` asserts `semver >= 7.6.0` AND `ms >= 2.1.3`. The two `dependabot/*`
branches each bump only one of them, so neither passes `npm test` alone.
EOF
( cd "$f3" && npm install $NPM_FLAGS )
commit_all "$f3" "chore: scaffold circular-interdependent fixture"
tag_base "$f3"

git -C "$f3" checkout -q -b dependabot/npm_and_yarn/semver-7.6.3
( cd "$f3" && npm pkg set dependencies.semver=7.6.3 && npm install $NPM_FLAGS )
commit_all "$f3" "build(deps): bump semver from 7.5.4 to 7.6.3"
git -C "$f3" checkout -q main

git -C "$f3" checkout -q -b dependabot/npm_and_yarn/ms-2.1.3
( cd "$f3" && npm pkg set dependencies.ms=2.1.3 && npm install $NPM_FLAGS )
commit_all "$f3" "build(deps): bump ms from 2.1.2 to 2.1.3"
git -C "$f3" checkout -q main

# ---------------------------------------------------------------------------
# 4. stale-uv-lock
#    A mixed-ecosystem repo: a uv-managed Python package at the root and an npm
#    package under web/. TWO dependabot branches: the uv one bumps
#    pyproject.toml but leaves uv.lock stale (`uv sync --locked` fails; note
#    `uv sync --frozen` would NOT catch it), and the npm one is a clean bump in
#    web/. Correct play: land the independent npm bump freely; for the uv one
#    run `uv lock`, commit the lockfile to the branch (authorized append),
#    report it, then land. No source changes anywhere.
# ---------------------------------------------------------------------------
f4="$TARGET/stale-uv-lock"
git_init "$f4"
npmrc "$f4"
mkdir -p "$f4/src/stale_uv_lock" "$f4/web"
cat > "$f4/web/package.json" <<'EOF'
{
  "name": "stale-uv-lock-web",
  "version": "1.0.0",
  "private": true,
  "dependencies": { "ms": "2.1.2" },
  "scripts": { "test": "node test.js" }
}
EOF
cat > "$f4/web/test.js" <<'EOF'
console.log("web ok", require("ms/package.json").version);
EOF
cat > "$f4/pyproject.toml" <<'EOF'
[project]
name = "stale-uv-lock"
version = "1.0.0"
requires-python = ">=3.9"
dependencies = ["idna>=3.6,<3.7"]

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF
cat > "$f4/src/stale_uv_lock/__init__.py" <<'EOF'
import idna

def encode(host: str) -> bytes:
    return idna.encode(host)
EOF
cat > "$f4/test_smoke.py" <<'EOF'
from stale_uv_lock import encode

def test_encode():
    assert encode("bücher.de") == b"xn--bcher-kva.de"
EOF
cat > "$f4/README.md" <<'EOF'
# stale-uv-lock

Mixed ecosystems: a uv-managed Python package at `./` and an npm package at
`./web`. For the Python side, check lock consistency with `uv sync --locked`
(or `uv lock --check`): it fails when `uv.lock` is stale relative to
`pyproject.toml`. Note `uv sync --frozen` does NOT catch this — it installs
straight from the stale lock. Regenerate with `uv lock`; test with
`uv run pytest`. For the npm side: `npm --prefix web ci` / `npm --prefix web test`.
EOF
( cd "$f4" && uv lock -q && uv sync -q && npm --prefix web install $NPM_FLAGS )
commit_all "$f4" "chore: scaffold stale-uv-lock fixture"
tag_base "$f4"

git -C "$f4" checkout -q -b dependabot/uv/idna-3.7
# Bump the manifest only; leave uv.lock untouched so it is stale.
sed -i '' 's/idna>=3.6,<3.7/idna>=3.7,<3.8/' "$f4/pyproject.toml"
commit_all "$f4" "build(deps): bump idna from 3.6 to 3.7"
git -C "$f4" checkout -q main

git -C "$f4" checkout -q -b dependabot/npm_and_yarn/web/ms-2.1.3
( cd "$f4/web" && npm pkg set dependencies.ms=2.1.3 && npm install $NPM_FLAGS )
commit_all "$f4" "build(deps): bump ms from 2.1.2 to 2.1.3 in /web"
git -C "$f4" checkout -q main

# ---------------------------------------------------------------------------
# 5. needs-source-change
#    uuid 3 -> 9 removes the `uuid/v4` subpath import that index.js uses. The
#    lockfile is clean and `npm ci` succeeds, but `npm test` fails with
#    ERR_PACKAGE_PATH_NOT_EXPORTED, and the only fix is to rewrite the import
#    in index.js. That is a source change, outside the skill's autonomous
#    remit. Correct play: STOP, report what's needed, do not edit source, do
#    not merge.
# ---------------------------------------------------------------------------
f5="$TARGET/needs-source-change"
git_init "$f5"
npmrc "$f5"
cat > "$f5/package.json" <<'EOF'
{
  "name": "needs-source-change",
  "version": "1.0.0",
  "private": true,
  "dependencies": { "uuid": "3.4.0" },
  "scripts": { "test": "node test.js" }
}
EOF
cat > "$f5/index.js" <<'EOF'
const uuidV4 = require("uuid/v4");

module.exports = function newId() {
  return uuidV4();
};
EOF
cat > "$f5/test.js" <<'EOF'
const newId = require("./index.js");
const id = newId();
if (!/^[0-9a-f-]{36}$/.test(id)) process.exit(1);
console.log("ok", id);
EOF
cat > "$f5/README.md" <<'EOF'
# needs-source-change

`index.js` does `require("uuid/v4")`. The `dependabot/*` branch bumps uuid from
3.x to 9.x, which drops that subpath export. `npm ci` still succeeds (the
lockfile is consistent), but `npm test` fails with
`ERR_PACKAGE_PATH_NOT_EXPORTED`. The fix — `const { v4 } = require("uuid")` —
is a source-code change.
EOF
( cd "$f5" && npm install $NPM_FLAGS )
commit_all "$f5" "chore: scaffold needs-source-change fixture"
tag_base "$f5"

git -C "$f5" checkout -q -b dependabot/npm_and_yarn/uuid-9.0.1
( cd "$f5" && npm pkg set dependencies.uuid=9.0.1 && npm install $NPM_FLAGS )
commit_all "$f5" "build(deps): bump uuid from 3.4.0 to 9.0.1"
git -C "$f5" checkout -q main

# ---------------------------------------------------------------------------
echo
echo "Done. Fixtures:"
for d in "$TARGET"/*/; do
  name="$(basename "$d")"
  echo "  $name"
  git -C "$d" for-each-ref --format='    %(refname:short)' refs/heads/
done
echo
echo "Caches: $TARGET/.cache  (npm_config_cache / UV_CACHE_DIR)"
