import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_workflow_permissions as cwp  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _write_workflow(tmp, name, content):
    workflows = Path(tmp) / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / name).write_text(content, encoding="utf-8")
    return workflows / name


class TestCheckWorkflowPermissionsLogic(unittest.TestCase):
    # ---- (1) no permissions: block at all -> FAIL ----
    def test_no_permissions_block_anywhere_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "no-perms.yml", """\
name: No perms

on:
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("'build'" in e and "no 'permissions:' block of its own" in e for e in errors))

    # ---- (2) write-all -> FAIL ----
    def test_write_all_top_level_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "write-all.yml", """\
name: Write all

on:
  workflow_dispatch:

permissions: write-all

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("write-all" in e for e in errors))

    def test_write_all_job_level_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "write-all-job.yml", """\
name: Write all job

on:
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions: write-all
    steps:
      - name: Checkout
        uses: actions/checkout@v4
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("write-all" in e and "build" in e for e in errors))

    # ---- (3) contents: read + a write op -> FAIL, message names file + scope ----
    def test_read_only_with_release_upload_fails_and_names_file_and_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_workflow(tmp, "release-upload.yml", """\
name: Release upload

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - name: Upload asset
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh release upload v1.0.0 dist/thing.zip
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertEqual(len(errors), 1)
            self.assertIn("release-upload.yml", errors[0])
            self.assertIn("contents", errors[0])
            self.assertIn("write", errors[0])

    # ---- (4) contents: read + only reads (view/download) -> PASS ----
    def test_read_only_with_only_read_ops_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "release-read.yml", """\
name: Release read

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - name: View + download
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release view v1.0.0 --repo owner/repo
          gh release download v1.0.0 --repo owner/repo --pattern '*.zip'
          gh release list --repo owner/repo
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertEqual(errors, [])

    # ---- (5) job-level (not top-level) permissions satisfying a write op -> PASS ----
    def test_job_level_permissions_satisfying_write_op_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "job-level-write.yml", """\
name: Job level write

on:
  workflow_dispatch:

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Create release
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh release create v1.0.0 dist/thing.zip
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertEqual(errors, [])

    def test_job_level_permissions_do_not_leak_to_sibling_job(self):
        # A write-granting permissions: block on job A must not be treated
        # as covering job B's write op - each job's effective permissions
        # are its own (or the top-level fallback), never a sibling's.
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "sibling-leak.yml", """\
name: Sibling leak

on:
  workflow_dispatch:

jobs:
  a:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: noop
        run: echo hi
  b:
    runs-on: ubuntu-latest
    steps:
      - name: Create release
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh release create v1.0.0 dist/thing.zip
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("'b'" in e for e in errors))

    # ---- rule (a), strict form (#188 follow-up): a top-level block
    # covers every job in the file; without one, EVERY job must declare
    # its own permissions: block or that job is a named FAIL. ----
    def test_top_level_block_covers_a_job_with_no_block_of_its_own(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "top-level-covers.yml", """\
name: Top level covers

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: noop
        run: echo hi
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertEqual(errors, [])

    def test_no_top_level_one_job_covered_sibling_uncovered_fails_naming_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "partial-coverage.yml", """\
name: Partial coverage

on:
  workflow_dispatch:

jobs:
  covered:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: noop
        run: echo hi
  uncovered:
    runs-on: ubuntu-latest
    steps:
      - name: noop
        run: echo hi
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("'uncovered'" in e and "no 'permissions:' block of its own" in e for e in errors))
            self.assertFalse(any("'covered'" in e for e in errors))

    def test_no_top_level_but_every_job_has_its_own_block_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "every-job-covered.yml", """\
name: Every job covered

on:
  workflow_dispatch:

jobs:
  a:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: noop
        run: echo hi
  b:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: noop
        run: echo hi
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertEqual(errors, [])

    def test_reusable_workflow_call_job_with_no_steps_under_top_level_block_passes(self):
        # jobs.<id>.uses: (a reusable-workflow call) has no runs-on/steps
        # of its own - must not crash the run: scanner or the permissions
        # walk, and is fully covered by a top-level block like any other
        # job (mirrors mint-release.yml's fast-tier/boot-tier jobs).
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "reusable-call.yml", """\
name: Reusable call

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: noop
        run: echo hi
  reused:
    needs: build
    uses: ./.github/workflows/some-other.yml
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertEqual(errors, [])

    # ---- other write-op scopes ----
    def test_pr_create_needs_pull_requests_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "pr.yml", """\
name: PR

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  open-pr:
    runs-on: ubuntu-latest
    steps:
      - name: Open PR
        run: gh pr create --title x --body y
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("pull-requests" in e for e in errors))

    def test_issue_comment_needs_issues_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "issue.yml", """\
name: Issue

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  comment:
    runs-on: ubuntu-latest
    steps:
      - name: Comment
        run: gh issue comment 5 --body "hi"
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("issues" in e for e in errors))

    def test_workflow_run_needs_actions_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "dispatch.yml", """\
name: Dispatch

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  fire:
    runs-on: ubuntu-latest
    steps:
      - name: Fire another workflow
        run: gh workflow run other.yml --ref main
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("actions" in e for e in errors))

    def test_workflow_run_with_actions_write_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "dispatch-ok.yml", """\
name: Dispatch ok

on:
  workflow_dispatch:

permissions:
  actions: write

jobs:
  fire:
    runs-on: ubuntu-latest
    steps:
      - name: Fire another workflow
        run: gh workflow run other.yml --ref main
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertEqual(errors, [])

    def test_generic_gh_api_post_needs_any_write_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "api-post.yml", """\
name: API post

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  hit-api:
    runs-on: ubuntu-latest
    steps:
      - name: POST something
        run: gh api -X POST /repos/owner/repo/dispatches
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("gh api" in e for e in errors))

    def test_generic_gh_api_post_with_any_write_scope_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "api-post-ok.yml", """\
name: API post ok

on:
  workflow_dispatch:

permissions:
  issues: write

jobs:
  hit-api:
    runs-on: ubuntu-latest
    steps:
      - name: POST something
        run: gh api --method POST /repos/owner/repo/dispatches
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertEqual(errors, [])

    def test_explicit_empty_permissions_mapping_is_not_missing(self):
        # `permissions: {}` is an explicit declaration granting nothing -
        # must satisfy rule (a) (not "missing"), and is correctly
        # insufficient for any write op under rule (c).
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "empty-perms.yml", """\
name: Empty perms

on:
  workflow_dispatch:

permissions: {}

jobs:
  noop:
    runs-on: ubuntu-latest
    steps:
      - name: noop
        run: echo hi
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertEqual(errors, [])

    # ---- unparseable/garbage file -> loud failure, not silent pass ----
    def test_garbage_workflow_file_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "garbage.yml", "this is not: [valid yaml at all: :::\n\t- broken\n")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("garbage.yml" in e and "PARSE FAILURE" in e for e in errors))

    def test_permissions_block_with_unrecognised_shape_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "weird-perms.yml", """\
name: Weird perms

on:
  workflow_dispatch:

permissions: [contents, read]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: noop
        run: echo hi
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("PARSE FAILURE" in e for e in errors))

    def test_no_jobs_key_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "no-jobs.yml", """\
name: No jobs

on:
  workflow_dispatch:

permissions:
  contents: read
""")
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("PARSE FAILURE" in e for e in errors))

    def test_no_workflows_dir_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors, _stats = cwp.check_workflow_permissions(Path(tmp))
            self.assertTrue(any("not found" in e for e in errors))


class TestCheckWorkflowPermissionsCli(unittest.TestCase):
    def test_cli_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "ok.yml", """\
name: OK

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: noop
        run: echo hi
""")
            self.assertEqual(cwp.main([tmp]), 0)

    def test_cli_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_workflow(tmp, "bad.yml", """\
name: Bad

on:
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: noop
        run: echo hi
""")
            self.assertEqual(cwp.main([tmp]), 1)

    # ---- (6) the repo's real .github/workflows/ -> PASS ----
    def test_real_repo_workflows_pass(self):
        workflows_dir = REPO_ROOT / ".github" / "workflows"
        if not workflows_dir.is_dir():
            self.skipTest(f"not running inside the repo (no .github/workflows found at {workflows_dir})")
        self.assertEqual(cwp.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
