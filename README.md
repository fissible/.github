# fissible/.github

Org-wide standards, release tooling, and reusable GitHub Actions workflows for all fissible projects.

> **For Claude Code sessions:** When working in any fissible repo, read this file first.
> It documents what is automated, what is manual, and how releases work.
> The release procedure is in the [Release procedure](#release-procedure) section below.

---

## What this repo contains

| File | Purpose |
|---|---|
| `README.md` | This file — full reference for humans and Claude Code sessions |
| `RELEASE.md` | Canonical version strategy and semver rules |
| `CONTRIBUTING.md` | Commit message format (Conventional Commits), TDD standard, branching |
| `release.sh` | Interactive release script — copy to any fissible repo root |
| `.cliff.toml` | git-cliff config for CHANGELOG generation — copy to any fissible repo root |
| `PULL_REQUEST_TEMPLATE.md` | Default PR body for all repos in the org |
| `ISSUE_TEMPLATE/bug_report.md` | Default bug report template |
| `ISSUE_TEMPLATE/feature_request.md` | Default feature request template |
| `profile/README.md` | Org landing page shown at github.com/fissible |
| `.github/workflows/test-bash.yml` | Reusable CI workflow — bash matrix (3.2 + 5.x) |
| `.github/workflows/release.yml` | Reusable release workflow — creates GitHub Release on tag push |

---

## What is automated

Once a fissible repo has `.github/workflows/ci.yml` and `.github/workflows/release.yml`, the following happens automatically with no manual steps:

### On every push or PR to `main`
- **CI runs** (`test-bash.yml`): executes `bash run.sh` on two runners in parallel:
  - macOS latest — bash 3.2 (system bash, tests 3.2 compatibility)
  - Ubuntu latest — bash 5.x (tests modern bash)
- PRs cannot be merged if CI fails

### On every tag push matching `v*`
- **Release workflow** (`release.yml`): creates a GitHub Release automatically
  - Verifies the tag is on a commit reachable from `main` — aborts if not
  - Extracts the matching section from `CHANGELOG.md`
  - Creates the GitHub Release with those notes

Everything else is **manual** — see the release procedure below.

---

## What is NOT automated

These steps are intentionally manual to keep the release process explicit and reviewed:

- Deciding the version bump type (patch / minor / major)
- Updating `VERSION` and `CHANGELOG.md`
- Creating the git commit and tag
- Updating the Homebrew formula in `fissible/homebrew-tap` after a release
- Bumping version references in dependent projects after a breaking change

---

## Release procedure

This is the complete, step-by-step procedure to cut a release. `release.sh` handles steps 1–7.

### Using release.sh (recommended)

```bash
# From the repo root on main, with a clean working tree:
bash release.sh           # script suggests bump type automatically
bash release.sh minor     # or specify: patch | minor | major
```

The script will:
1. Verify you are on `main` with a clean working tree
2. Show all commits since the last tag
3. Suggest a bump type based on conventional commit types (`feat` → minor, `fix` → patch, `feat!` → major)
4. Confirm the new version with you
5. Update `VERSION`
6. Regenerate `CHANGELOG.md` via git-cliff
7. Commit `chore: release vX.Y.Z`
8. Create annotated tag `vX.Y.Z`
9. Ask before pushing — pushes branch and tags

After `release.sh` completes:
- GitHub Actions picks up the tag push and creates the GitHub Release automatically (step 10)
- If the project is in homebrew-tap, update the formula manually (step 11)

### Manual procedure (if not using release.sh)

```bash
# 1. Ensure you are on main, working tree clean
git checkout main && git pull
git diff --quiet && git diff --cached --quiet

# 2. Review commits since last tag
git log $(git describe --tags --abbrev=0)..HEAD --oneline --no-merges

# 3. Update VERSION
echo "1.2.0" > VERSION

# 4. Regenerate CHANGELOG
git-cliff --config .cliff.toml --tag v1.2.0 --output CHANGELOG.md

# 5. Commit and tag
git add VERSION CHANGELOG.md
git commit -m "chore: release v1.2.0"
git tag -a v1.2.0 -m "v1.2.0"

# 6. Push (triggers GitHub Release automatically)
git push && git push --tags
```

---

## Wiring up a new fissible repo

Every new bash project should have these files. Copy them from this repo:

**1. Required files (copy to repo root):**
```bash
cp path/to/.github/release.sh ./release.sh
cp path/to/.github/.cliff.toml ./.cliff.toml
chmod +x release.sh
```

**2. Create `VERSION`:**
```bash
echo "0.1.0" > VERSION
```

**3. Generate initial `CHANGELOG.md`:**
```bash
git-cliff --config .cliff.toml --output CHANGELOG.md
```

**4. Add CI workflow** (`.github/workflows/ci.yml`):
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    uses: fissible/.github/.github/workflows/test-bash.yml@main
```

**5. Add release workflow** (`.github/workflows/release.yml`):
```yaml
name: Release
on:
  push:
    tags: ['v*']
jobs:
  release:
    uses: fissible/.github/.github/workflows/release.yml@main
```

**6. Add to `PROJECT.md`** — include a "Current version" line and link to this README.

---

## Version strategy summary

Full details in [RELEASE.md](./RELEASE.md). Short version:

- **Semver** everywhere: `MAJOR.MINOR.PATCH`
- **Conventional Commits** drive bump decisions
- **`VERSION` file** = single source of truth (one line, no `v` prefix)
- **`CHANGELOG.md`** = generated by git-cliff from commit history
- **Annotated git tags** = `vX.Y.Z` matching `VERSION`
- Releases only from `main` — enforced by both `release.sh` and the release workflow

---

## Dependencies

| Tool | Install | Used by |
|---|---|---|
| `git-cliff` | `brew install git-cliff` | `release.sh`, manual CHANGELOG generation |
| `git` | system | everything |
| `bash` | system (3.2+) | test suite, release.sh |
