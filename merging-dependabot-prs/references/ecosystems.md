# Ecosystem reference: build, test, and lockfile sync

For each ecosystem: how to install/build/test a checked-out branch, and how to
regenerate the lockfile when Dependabot changed a manifest but left the lockfile
stale. Always prefer commands documented in the repo (README, CONTRIBUTING,
`.github/workflows/*`, Makefile, `mise`/`asdf` config) over these defaults.

A lockfile is stale when the manifest lists a version range or dependency that
the lockfile's pinned graph no longer satisfies. Symptoms: CI step named
"check lockfile", "frozen", "--locked", "--frozen-lockfile", or
"verify up to date" fails; or the install step itself refuses in CI mode.

After regenerating, commit only the lockfile (and manifest if the tool
reformatted it) to the PR branch:

```bash
git add <lockfile> && git commit -m "chore(deps): sync <lockfile> after <pkg> bump" && git push
```

Pushing to a Dependabot branch stops Dependabot from further auto-updating it —
expected and fine here.

---

## Python — uv

- Install/test: `uv sync --frozen && uv run pytest` (or the project's test cmd).
  If `--frozen` fails, the lock is stale.
- Regenerate lock: `uv lock` (updates only what the manifest now requires).
  Then `uv sync`.
- Dependabot frequently updates `pyproject.toml` without updating `uv.lock` —
  this is the single most common append this skill performs.

## Python — Poetry

- Install/test: `poetry install --sync && poetry run pytest`
- Regenerate lock without bumping unrelated deps: `poetry lock --no-update`

## Python — pip-tools / requirements

- Regenerate: `pip-compile` (per `requirements*.in`). Some repos use
  `pip-compile --upgrade-package <pkg>`.

## Python — pipenv

- `pipenv lock` then `pipenv sync --dev`

## JavaScript / TypeScript — npm

- Install/test: `npm ci && npm test` (`npm ci` fails if `package-lock.json` is
  out of sync with `package.json`).
- Regenerate lock only: `npm install --package-lock-only`

## JavaScript — yarn

- Classic: `yarn install --frozen-lockfile` to check; `yarn install` to fix.
- Berry: `yarn install --immutable` to check; `yarn install` to fix.

## JavaScript — pnpm

- Check: `pnpm install --frozen-lockfile`
- Regenerate lock only: `pnpm install --lockfile-only`

## Rust — Cargo

- Build/test: `cargo build --locked && cargo test --locked` (`--locked` fails on
  a stale `Cargo.lock`).
- Regenerate for one crate: `cargo update -p <crate> --precise <version>`

## Go modules

- Build/test: `go build ./... && go test ./...`
- Sync: `go mod tidy` (updates `go.mod` and `go.sum`). Verify: `go mod verify`.

## Ruby — Bundler

- Check: `bundle install --frozen` or `bundle check`
- Update one gem: `bundle lock --update <gem>` (keeps others pinned)

## PHP — Composer

- Check: `composer install --dry-run` / CI uses `--no-dev` etc.
- Update one package: `composer update <vendor/pkg> --with-dependencies`

## GitHub Actions

- No lockfile. Changes are to `.github/workflows/*.yml` /
  `.github/actions/*` version pins. Verify by reading the diff and letting CI
  run; nothing to regenerate.

## Docker

- Changes a base image tag/digest in a `Dockerfile`. Verify with a local
  `docker build` if feasible; otherwise rely on CI.

## Gradle / Maven (Java)

- Gradle with version catalog + lockfile: `./gradlew dependencies --write-locks`
- Maven generally has no lockfile; `mvn -o verify` to test.
