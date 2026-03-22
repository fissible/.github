"""Tests for fissible versioning MCP server.

Uses real temp git repos to avoid mocking git internals.
"""
import sys
import os
import json
import shutil
import subprocess
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def make_repo(path, version=None, tag=None, commits=None, changelog=None, composer_version=None):
    """Create a minimal git repo for testing."""
    os.makedirs(path, exist_ok=True)
    subprocess.run(['git', 'init', '-b', 'main'], cwd=path, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=path, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=path, capture_output=True)

    if version:
        with open(os.path.join(path, 'VERSION'), 'w') as f:
            f.write(version + '\n')

    if changelog:
        with open(os.path.join(path, 'CHANGELOG.md'), 'w') as f:
            f.write(changelog)

    if composer_version is not None:
        with open(os.path.join(path, 'composer.json'), 'w') as f:
            json.dump({'name': 'test/pkg', 'version': composer_version}, f)

    # Initial commit
    subprocess.run(['git', 'add', '-A'], cwd=path, capture_output=True)
    subprocess.run(['git', 'commit', '--allow-empty', '-m', 'feat: initial commit'],
                   cwd=path, capture_output=True)

    if tag:
        subprocess.run(['git', 'tag', '-a', tag, '-m', tag], cwd=path, capture_output=True)

    if commits:
        for msg in commits:
            subprocess.run(['git', 'commit', '--allow-empty', '-m', msg],
                           cwd=path, capture_output=True)

    return path


class TestFissibleVersion(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        import server as s
        s.FISSIBLE_ROOT = self.tmpdir
        self.server = s

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_version_aligned(self):
        """fissible_version reports aligned when VERSION matches git tag."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.2.3', tag='v1.2.3')
        result = self.server.fissible_version('myrepo')
        self.assertIn('1.2.3', result)
        self.assertIn('aligned', result)

    def test_version_misaligned(self):
        """fissible_version reports misalignment when VERSION != tag."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.2.3', tag='v1.0.0')
        result = self.server.fissible_version('myrepo')
        self.assertIn('misaligned', result)
        self.assertIn('1.2.3', result)
        self.assertIn('v1.0.0', result)

    def test_version_no_tag(self):
        """fissible_version reports no tag when repo has no tags."""
        make_repo(f'{self.tmpdir}/myrepo', version='0.1.0')
        result = self.server.fissible_version('myrepo')
        self.assertIn('none', result)

    def test_version_missing_version_file(self):
        """fissible_version reports missing VERSION file."""
        make_repo(f'{self.tmpdir}/myrepo', tag='v1.0.0')
        result = self.server.fissible_version('myrepo')
        self.assertIn('missing', result)

    def test_version_repo_not_found(self):
        """fissible_version returns error for unknown repo."""
        result = self.server.fissible_version('doesnotexist')
        self.assertIn('ERROR', result)

    def test_version_strips_fissible_prefix(self):
        """fissible_version accepts 'fissible/repo' as well as 'repo'."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.0.0', tag='v1.0.0')
        result = self.server.fissible_version('fissible/myrepo')
        self.assertIn('aligned', result)


class TestFissibleAudit(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        import server as s
        s.FISSIBLE_ROOT = self.tmpdir
        self.server = s

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_audit_all_aligned(self):
        """fissible_audit reports clean when VERSION, tag, and CHANGELOG all match."""
        changelog = '# Changelog\n\n## [1.0.0] - 2026-01-01\n\n### Added\n- init\n'
        make_repo(f'{self.tmpdir}/myrepo', version='1.0.0', tag='v1.0.0', changelog=changelog)
        result = self.server.fissible_audit('myrepo')
        self.assertIn('all version sources aligned', result)

    def test_audit_missing_version_file(self):
        """fissible_audit flags missing VERSION file."""
        make_repo(f'{self.tmpdir}/myrepo', tag='v1.0.0')
        result = self.server.fissible_audit('myrepo')
        self.assertIn('VERSION file missing', result)

    def test_audit_tag_version_mismatch(self):
        """fissible_audit flags VERSION != tag."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.1.0', tag='v1.0.0')
        result = self.server.fissible_audit('myrepo')
        self.assertIn('1.1.0', result)
        self.assertIn('v1.0.0', result)

    def test_audit_missing_changelog_section(self):
        """fissible_audit flags CHANGELOG missing section for current version."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.0.0', tag='v1.0.0',
                  changelog='# Changelog\n\n## [0.9.0]\n- old\n')
        result = self.server.fissible_audit('myrepo')
        self.assertIn('CHANGELOG', result)
        self.assertIn('1.0.0', result)

    def test_audit_composer_mismatch(self):
        """fissible_audit flags composer.json version mismatch."""
        changelog = '# Changelog\n\n## [1.0.0]\n- init\n'
        make_repo(f'{self.tmpdir}/myrepo', version='1.0.0', tag='v1.0.0',
                  changelog=changelog, composer_version='0.9.0')
        result = self.server.fissible_audit('myrepo')
        self.assertIn('composer.json', result)
        self.assertIn('0.9.0', result)


class TestFissibleAuditAll(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        import server as s
        s.FISSIBLE_ROOT = self.tmpdir
        self.server = s

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_audit_all_lists_repos_with_version_files(self):
        """fissible_audit_all includes repos that have VERSION files."""
        make_repo(f'{self.tmpdir}/alpha', version='1.0.0', tag='v1.0.0')
        make_repo(f'{self.tmpdir}/beta', version='2.0.0', tag='v2.0.0')
        result = self.server.fissible_audit_all()
        self.assertIn('alpha', result)
        self.assertIn('beta', result)

    def test_audit_all_skips_repos_without_version(self):
        """fissible_audit_all skips repos that have no VERSION file."""
        make_repo(f'{self.tmpdir}/noversionrepo')
        make_repo(f'{self.tmpdir}/withversion', version='1.0.0', tag='v1.0.0')
        result = self.server.fissible_audit_all()
        self.assertNotIn('noversionrepo', result)
        self.assertIn('withversion', result)

    def test_audit_all_shows_alignment_status(self):
        """fissible_audit_all shows ✓ for aligned and ✗ for misaligned."""
        make_repo(f'{self.tmpdir}/good', version='1.0.0', tag='v1.0.0')
        make_repo(f'{self.tmpdir}/bad', version='1.1.0', tag='v1.0.0')
        result = self.server.fissible_audit_all()
        self.assertIn('✓', result)
        self.assertIn('✗', result)

    def test_audit_all_summary_line(self):
        """fissible_audit_all includes a N/total summary line."""
        make_repo(f'{self.tmpdir}/a', version='1.0.0', tag='v1.0.0')
        make_repo(f'{self.tmpdir}/b', version='1.0.0', tag='v1.0.0')
        result = self.server.fissible_audit_all()
        self.assertIn('2/2', result)


class TestFissibleReleaseAdvice(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        import server as s
        s.FISSIBLE_ROOT = self.tmpdir
        self.server = s

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_suggests_minor_for_feat_commits(self):
        """fissible_release_advice suggests minor bump when feat: commits present."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.0.0', tag='v1.0.0',
                  commits=['feat: add new thing', 'fix: small correction'])
        result = self.server.fissible_release_advice('myrepo')
        self.assertIn('minor', result)
        self.assertIn('1.1.0', result)

    def test_suggests_patch_for_fix_only_commits(self):
        """fissible_release_advice suggests patch bump when only fix: commits."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.0.0', tag='v1.0.0',
                  commits=['fix: correct a bug', 'fix: another fix'])
        result = self.server.fissible_release_advice('myrepo')
        self.assertIn('patch', result)
        self.assertIn('1.0.1', result)

    def test_suggests_major_for_breaking_commits(self):
        """fissible_release_advice suggests major bump for breaking changes."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.0.0', tag='v1.0.0',
                  commits=['feat!: redesign API'])
        result = self.server.fissible_release_advice('myrepo')
        self.assertIn('major', result)
        self.assertIn('2.0.0', result)

    def test_nothing_to_release(self):
        """fissible_release_advice reports nothing to release when no commits since tag."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.0.0', tag='v1.0.0')
        result = self.server.fissible_release_advice('myrepo')
        self.assertIn('nothing to release', result)

    def test_lists_feat_and_fix_commits(self):
        """fissible_release_advice lists added and fixed sections."""
        make_repo(f'{self.tmpdir}/myrepo', version='1.0.0', tag='v1.0.0',
                  commits=['feat: cool feature', 'fix: broken thing'])
        result = self.server.fissible_release_advice('myrepo')
        self.assertIn('cool feature', result)
        self.assertIn('broken thing', result)

    def test_advice_with_no_prior_tag(self):
        """fissible_release_advice handles repo with no tags yet."""
        make_repo(f'{self.tmpdir}/myrepo', version='0.1.0',
                  commits=['feat: first feature'])
        result = self.server.fissible_release_advice('myrepo')
        self.assertIn('minor', result)


if __name__ == '__main__':
    unittest.main()
