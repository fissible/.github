# Contributing to fissible projects

## Commit messages — Conventional Commits

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

```
<type>: <short description>

[optional body]

[optional footer: BREAKING CHANGE: ...]
```

### Types

| Type | When to use | Version bump |
|---|---|---|
| `feat` | New feature or capability | minor |
| `fix` | Bug fix | patch |
| `refactor` | Code change that isn't a fix or feature | none |
| `test` | Adding or updating tests | none |
| `docs` | Documentation only | none |
| `chore` | Tooling, deps, release commits | none |
| `perf` | Performance improvement | none |
| `style` | Formatting, whitespace | none |
| `feat!` / `BREAKING CHANGE:` | Incompatible API change | major |

### Examples

```
feat: add seed_custom engine with .seed schema file support
fix: correct MCP server path from placeholder to absolute path
refactor: hoist locals and split array declarations in wizard
chore: release v1.1.0
```

---

## Branching

- `main` is always releasable
- Work on feature branches: `feat/<name>`, `fix/<name>`, `chore/<name>`
- Open a PR to merge into `main`; don't push directly

---

## Test-driven development

Write the test before the implementation. No exceptions.

1. Write a failing test that describes the desired behaviour
2. Confirm it fails for the right reason
3. Write the minimal code to pass it
4. Confirm all tests pass
5. Refactor if needed — keep tests green

**Bash projects:** tests live in `tests/unit/` and `tests/integration/`. Run the full suite with `bash run.sh`.

A PR without tests for new behaviour will not be merged.

---

## Releasing

See [RELEASE.md](./RELEASE.md) for the full release process.
Use `release.sh` at the root of any fissible repo to cut a release.
