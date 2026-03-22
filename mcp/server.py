#!/usr/bin/env python3
"""fissible versioning MCP server.

Tools:
  fissible_version(repo)       — fast VERSION vs git tag alignment check
  fissible_audit(repo)         — full audit: VERSION, tag, CHANGELOG, composer.json, package.json
  fissible_audit_all()         — audit every ~/lib/fissible/* repo with a VERSION file
  fissible_repos()             — list all fissible repos with descriptions for issue routing
  fissible_new_issue(repo, title, body, labels) — create a GitHub issue via gh CLI
  fissible_release_advice(repo)— analyze commits since last tag, suggest bump + new version
"""
import subprocess
import os
import re
import json
from pathlib import Path
from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp import FastMCP

mcp = FastMCP("fissible")

FISSIBLE_ROOT = os.path.expanduser("~/lib/fissible")

REPO_DESCRIPTIONS = {
    ".github":          "org-wide standards, CI workflows, release tooling, MCP server",
    "guit":             "terminal git client (proprietary)",
    "homebrew-tap":     "Homebrew formula repository",
    "macbin":           "personal macOS toolbox (gflow, gitag, gdiff)",
    "projects":         "suite planning and project management",
    "ptyunit":          "standalone PTY test framework",
    "seed":             "bash fake data generator (31 generators, MCP server)",
    "shellframe":       "TUI framework (~10K lines, 714 tests)",
    "shellql":          "terminal SQLite workbench (shellframe-based)",
    "sigil-workspace":  "Rust credential broker (sigil CLI + sanctum daemon)",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve(repo: str) -> Path:
    """Resolve a repo name, 'fissible/name', or absolute path to a Path."""
    if os.path.isabs(repo):
        return Path(repo)
    name = repo.removeprefix("fissible/")
    return Path(FISSIBLE_ROOT) / name


def _git(args: list, cwd: Path) -> tuple:
    """Run a git command. Returns (returncode, stdout, stderr)."""
    r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def _read_version(path: Path) -> Optional[str]:
    f = path / "VERSION"
    return f.read_text().strip() if f.exists() else None


def _latest_tag(path: Path) -> Optional[str]:
    rc, out, _ = _git(["describe", "--tags", "--abbrev=0"], path)
    return out if rc == 0 else None


def _commits_since(path: Path, tag: Optional[str]) -> list:
    args = ["log", "--oneline", "--no-merges"]
    if tag:
        args.append(f"{tag}..HEAD")
    rc, out, _ = _git(args, path)
    if rc != 0 or not out:
        return []
    return [l for l in out.splitlines() if l]


def _suggest_bump(commits: list) -> str:
    if any("!:" in c or "BREAKING CHANGE" in c for c in commits):
        return "major"
    if any(re.search(r'[a-f0-9]+ feat', c) for c in commits):
        return "minor"
    if commits:
        return "patch"
    return "none"


def _bump(version: str, bump: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if bump == "major": return f"{major + 1}.0.0"
    if bump == "minor": return f"{major}.{minor + 1}.0"
    if bump == "patch": return f"{major}.{minor}.{patch + 1}"
    return version


def _changelog_has_version(path: Path, version: str) -> bool:
    f = path / "CHANGELOG.md"
    return f.exists() and f"## [{version}]" in f.read_text()


def _json_version(path: Path, filename: str) -> Optional[str]:
    f = path / filename
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text()).get("version")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@mcp.tool()
def fissible_version(repo: str) -> str:
    """Fast version check for a fissible repo — VERSION file vs latest git tag.

    repo = name (e.g. 'seed'), 'fissible/seed', or absolute path.
    """
    path = _resolve(repo)
    if not path.exists():
        return f"ERROR: repo not found at {path}"

    version = _read_version(path)
    tag = _latest_tag(path)
    tag_ver = tag.lstrip("v") if tag else None
    aligned = version is not None and version == tag_ver

    lines = [
        f"repo:    {path.name}",
        f"VERSION: {version or '(missing)'}",
        f"tag:     {tag or '(none)'}",
        f"status:  {'✓ aligned' if aligned else '✗ misaligned'}",
    ]
    if not aligned and version and tag_ver:
        lines.append(f"         VERSION={version} but tag={tag_ver}")
    return "\n".join(lines)


@mcp.tool()
def fissible_audit(repo: str) -> str:
    """Full version audit for a fissible repo.

    Checks VERSION, git tag, CHANGELOG.md, composer.json, and package.json for alignment.
    repo = name (e.g. 'seed'), 'fissible/seed', or absolute path.
    """
    path = _resolve(repo)
    if not path.exists():
        return f"ERROR: repo not found at {path}"

    issues = []
    version = _read_version(path)
    tag = _latest_tag(path)
    tag_ver = tag.lstrip("v") if tag else None

    if not version:
        issues.append("VERSION file missing")
    if not tag:
        issues.append("no git tags found")
    if version and tag_ver and version != tag_ver:
        issues.append(f"VERSION ({version}) != latest tag ({tag_ver})")
    if version and not _changelog_has_version(path, version):
        issues.append(f"CHANGELOG.md missing section for [{version}]")

    composer_ver = _json_version(path, "composer.json")
    if composer_ver is not None and version and composer_ver != version:
        issues.append(f"composer.json version ({composer_ver}) != VERSION ({version})")

    pkg_ver = _json_version(path, "package.json")
    if pkg_ver is not None and version and pkg_ver != version:
        issues.append(f"package.json version ({pkg_ver}) != VERSION ({version})")

    lines = [f"=== {path.name} version audit ===",
             f"VERSION:    {version or '(missing)'}",
             f"latest tag: {tag or '(none)'}"]
    if composer_ver is not None:
        lines.append(f"composer:   {composer_ver}")
    if pkg_ver is not None:
        lines.append(f"package:    {pkg_ver}")
    lines.append("")
    if issues:
        lines.append(f"ISSUES ({len(issues)}):")
        for issue in issues:
            lines.append(f"  ✗ {issue}")
    else:
        lines.append("✓ all version sources aligned")
    return "\n".join(lines)


@mcp.tool()
def fissible_audit_all() -> str:
    """Audit version alignment across all fissible repos under ~/lib/fissible/."""
    root = Path(FISSIBLE_ROOT)
    if not root.exists():
        return f"ERROR: {root} not found"

    results = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not (d / ".git").exists() or not (d / "VERSION").exists():
            continue
        version = _read_version(d)
        tag = _latest_tag(d)
        tag_ver = tag.lstrip("v") if tag else None
        ok = version is not None and version == tag_ver
        results.append({"repo": d.name, "version": version or "?", "tag": tag or "(none)", "ok": ok})

    if not results:
        return "No fissible repos with VERSION files found."

    lines = ["fissible repo version audit", ""]
    for r in results:
        mark = "✓" if r["ok"] else "✗"
        lines.append(f"  {mark}  {r['repo']:<20} VERSION={r['version']:<10} tag={r['tag']}")
    ok_count = sum(1 for r in results if r["ok"])
    lines += ["", f"{ok_count}/{len(results)} repos aligned"]
    return "\n".join(lines)


@mcp.tool()
def fissible_repos() -> str:
    """List all fissible repos with one-line descriptions for issue routing.

    Returns a formatted table of every git repo under ~/lib/fissible/.
    Repos not in the static descriptions dict show '(no description)'.
    """
    root = Path(FISSIBLE_ROOT)
    if not root.exists():
        return f"ERROR: {root} not found"

    lines = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not (d / ".git").exists():
            continue
        desc = REPO_DESCRIPTIONS.get(d.name, "(no description)")
        lines.append(f"{d.name:<20} — {desc}")

    if not lines:
        return "No fissible repos found."
    return "\n".join(lines)


@mcp.tool()
def fissible_new_issue(repo: str, title: str, body: str, labels: list) -> str:
    """Create a GitHub issue in a fissible repo via gh CLI.

    repo   = bare name ('seed'), 'fissible/seed', or absolute path.
    labels = list of label strings e.g. ['bug']; may be empty.

    Returns a formatted string with issue number, URL, and a ready-to-copy
    claude worker command.
    """
    if os.path.isabs(repo):
        name = Path(repo).name
    else:
        name = repo.removeprefix("fissible/")

    cmd = ["gh", "issue", "create",
           "--repo", f"fissible/{name}",
           "--title", title,
           "--body", body]
    for label in labels:
        cmd += ["--label", label]
    cmd += ["--json", "number,url"]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return f"ERROR: gh issue create failed: {r.stderr.strip()}"

    try:
        data = json.loads(r.stdout)
        number = data["number"]
        url = data["url"]
    except (json.JSONDecodeError, KeyError) as e:
        return f"ERROR: unexpected gh output: {e}: {r.stdout[:200]}"
    worker = f'claude --cwd ~/lib/fissible/{name} "Work on issue #{number}: {title}"'

    return "\n".join([
        f"issue:   #{number}",
        f"url:     {url}",
        f"worker:  {worker}",
    ])


@mcp.tool()
def fissible_release_advice(repo: str) -> str:
    """Analyze commits since the last tag and suggest the next version.

    Returns bump type (patch/minor/major), suggested new version, and a
    categorized summary of what has changed.
    repo = name (e.g. 'seed'), 'fissible/seed', or absolute path.
    """
    path = _resolve(repo)
    if not path.exists():
        return f"ERROR: repo not found at {path}"

    version = _read_version(path)
    tag = _latest_tag(path)
    commits = _commits_since(path, tag)

    if not commits:
        return f"{path.name}: no commits since {tag or 'beginning'} — nothing to release."

    bump = _suggest_bump(commits)
    new_ver = _bump(version, bump) if version else "?"

    added = [c for c in commits if re.search(r'[a-f0-9]+ feat', c)]
    fixed = [c for c in commits if re.search(r'[a-f0-9]+ fix', c)]
    other = [c for c in commits if c not in added and c not in fixed]

    def _fmt(items, limit=5):
        lines = [f"  {c}" for c in items[:limit]]
        if len(items) > limit:
            lines.append(f"  ... and {len(items) - limit} more")
        return lines

    lines = [
        f"=== {path.name} release advice ===",
        f"current: {version or '(no VERSION)'} ({tag or 'no tag'})",
        f"commits: {len(commits)} since last tag",
        f"bump:    {bump}",
        f"suggest: v{new_ver}",
        "",
    ]
    if added:
        lines += [f"Added ({len(added)}):"] + _fmt(added) + [""]
    if fixed:
        lines += [f"Fixed ({len(fixed)}):"] + _fmt(fixed) + [""]
    if other:
        lines += [f"Other ({len(other)}) — not releasable on their own:"] + _fmt(other, 3) + [""]
    lines.append(f"To release: bash release.sh {bump}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
