# Releasing asxshorts

This document describes how we cut and publish releases of the `asxshorts` package
to TestPyPI and PyPI using GitHub Actions with PyPI Trusted Publishers (OIDC).
It’s written for maintainers and is safe to share publicly.

## Overview

- Source repository: https://github.com/ay-mich/asxshorts
- Distribution name (PyPI): `asxshorts`
- Import package: `asxshorts`
- CLI commands: `asxshorts`
- CI (tests/lint/build): `.github/workflows/ci.yml`
- Publish workflow: `.github/workflows/publish.yml`
- Docs workflow (API docs to Pages): `.github/workflows/docs.yml`
- Build tool: `uv build` (produces wheel + sdist in `dist/`)
- Publisher: PyPI/TestPyPI Trusted Publisher via GitHub OIDC (no API tokens)

## Versioning

- We follow semantic versioning (MAJOR.MINOR.PATCH), with optional pre-release tags (e.g., `-rc.1`).
- The version appears in two places and must be kept in sync:
  - `pyproject.toml` `[project].version`
  - `src/asxshorts/__init__.py` `__version__`

## One-time setup (per index)

Set up a Trusted Publisher for both TestPyPI and PyPI.

1. Create the project on TestPyPI and PyPI if not already present.
2. In TestPyPI: Project → Settings → Publishing → Add a Publisher → GitHub
   - Owner: your GitHub username/org
   - Repository: `ay-mich/asxshorts`
   - Workflow: `.github/workflows/publish.yml` (or “Any workflow”)
   - Environment: leave default (unless you use environments; see below)
   - Save
3. Repeat the same in PyPI.
4. In GitHub repo settings (optional but recommended):
   - Environments → create `pypi-release` and add “Required reviewers” to gate real PyPI publishes.

## CI behavior

### Continuous Integration (ci.yml)

- Trigger: push and pull_request to `main` (only when code/packaging files change).
- Jobs:
  - Lint: `ruff format --check` and `ruff check` over `src/` and `tests/`.
  - Tests: `pytest` with coverage.
  - Build: `uv build` to validate packaging.

### Publishing (publish.yml)

- Trigger: pushing a tag matching `v*` runs the workflow.
- Jobs:
  - `build`: checks out code, runs `uv build`, uploads `dist/*` as an artifact.
  - `publish-testpypi`: downloads artifact and publishes to TestPyPI using OIDC.
    - Uses `skip-existing: true` so re-running with the same version does not fail.
  - `publish-pypi`: downloads artifact and publishes to PyPI using OIDC.
    - Runs only for tags starting with `v` that do not contain `rc`.
    - Protected by the `pypi-release` environment (manual approval if configured).
- Concurrency: tags share a concurrency group, so we won’t double-publish the same ref.
- Attestations: enabled (PEP 740) for supply-chain provenance.

## Pre-release checklist

- [ ] Ensure the main branch is green: tests, ruff.
- [ ] Update docs as needed and ensure README is consistent with features.
- [ ] Update `CHANGELOG.md`: finalize the version section and today’s date.
- [ ] Bump version in both files:
  - `pyproject.toml`
  - `src/asxshorts/__init__.py`
- [ ] (Optional) Local sanity build and metadata validation:
  ```bash
  uv build
  python -m twine check dist/*
  ```

## Cutting a release candidate (RC)

Use RCs to test the pipeline without publishing to PyPI.

```bash
git switch main
git pull

# Bump version to e.g. 0.1.1-rc.1 in pyproject.toml and src/asxshorts/__init__.py
git commit -am "release: v0.1.1-rc.1"
git tag v0.1.1-rc.1

# CRITICAL: Push both commits AND tags to trigger CI
git push origin main --follow-tags
# OR push them separately:
# git push origin main
# git push origin v0.1.1-rc.1

# Verify the tag was pushed:
git ls-remote --tags origin | grep v0.1.1-rc.1
```

What happens:

- CI builds and publishes the artifact to TestPyPI.
- The PyPI job is skipped due to the `rc` condition.

Verify on TestPyPI:

```bash
uv pip install -i https://test.pypi.org/simple asxshorts==0.1.1rc1
python -c "import asxshorts; print(asxshorts.__version__)"
asxshorts --version
```

Note: pre-release normalization may omit the dash in the install spec (e.g., `0.1.1rc1`).

## Cutting a stable release

```bash
git switch main
git pull

# Bump version to e.g. 0.1.1 in pyproject.toml and src/asxshorts/__init__.py
git commit -am "release: v0.1.1"
git tag v0.1.1

# CRITICAL: Push both commits AND tags to trigger CI
git push origin main --follow-tags
# OR push them separately (more explicit):
# git push origin main
# git push origin v0.1.1
```

**⚠️ IMPORTANT**: The GitHub Actions workflow is triggered by pushing the tag to the remote repository. If you forget to push the tag, the CI workflow will NOT run and your package will NOT be published to PyPI.

**Immediate verification** (run this right after pushing):

```bash
# Verify the tag was pushed to GitHub
git ls-remote --tags origin | grep v0.1.1
```

You should see output like:

```
48b87c4a7eb06a4af6ea20f885f462078a65e1bf        refs/tags/v0.1.1
```

If you don't see your tag, the CI won't trigger. Push it manually:

```bash
git push origin v0.1.1
```

What happens after successful tag push:

- CI builds and publishes to TestPyPI automatically
- CI publishes to PyPI after `pypi-release` environment approval (if configured)
- Check the Actions tab on GitHub to monitor progress

## API documentation (docs.yml)

- Trigger: push to `main` when code changes (or the workflow file itself changes).
- The workflow builds API docs with `pdoc` into the `site/` directory and deploys to GitHub Pages.
- `site/` is ignored by git and should not be committed; the workflow uploads and deploys it.
- You can preview locally with:
  ```bash
  uv sync --extra pandas
  uv add --dev pdoc
  uv run pdoc asxshorts -o site
  python -m http.server --directory site 8000
  ```

## Branch protection (optional)

- If you use branch protection, set the required status check to the CI job name: `CI / test`.
- Configure this in GitHub repo settings → Branches → Branch protection rules.

## Dependabot noise reduction

- Dependabot is configured to run weekly.
- GitHub Actions bumps are grouped (minor/patch) and major updates are ignored by default to reduce PR noise.
- Security updates for Actions may still appear; you can handle those manually when relevant.

Post-release verification (after CI completes):

```bash
pip install -U asxshorts==0.1.1
python -c "import asxshorts; print(asxshorts.__version__)"
asxshorts --version
```

## Local/manual publishing (rare)

Normally we publish via CI. For emergencies or testing only:

```bash
uv build
python -m twine check dist/*

# TestPyPI
uv publish --repository testpypi

# PyPI (ensure you understand the implications)
uv publish
```

## Troubleshooting

- **CI workflow doesn't trigger / No GitHub Actions run appears**:

  - **MOST COMMON ISSUE**: You forgot to push the tag to GitHub.
  - Check if your tag exists on the remote: `git ls-remote --tags origin | grep vX.Y.Z`
  - If missing, push it: `git push origin vX.Y.Z`
  - The workflow is triggered by tag pushes, not commits.
  - Verify in GitHub: go to Actions tab and look for a workflow run with your tag name.

- **CI fails with "403: Forbidden" during publish**:

  - Ensure Trusted Publisher is configured on the target index (TestPyPI/PyPI) for this repo.
  - The workflow file path and environment must match what PyPI/TestPyPI trusts.

- **CI fails with "File already exists"**:

  - Version already published. Bump the version before tagging.

- **CI waits for approval / "Required reviewers"**:

  - Approve the `pypi-release` environment in the Actions UI.

- **Can't install from TestPyPI**:

  - Use the TestPyPI index: `uv pip install -i https://test.pypi.org/simple asxshorts==X.Y.Z`
  - Or `pip install --extra-index-url https://test.pypi.org/simple asxshorts==X.Y.Z`

- **CLI/import mismatch**:

  - Distribution is `asxshorts`, import is `asxshorts`, CLI is `asxshorts`.

- **Metadata check fails**:

  - Run `python -m twine check dist/*` locally and correct errors (e.g., invalid URLs).

- **Tag exists locally but not on GitHub**:
  - This happens if you created a tag but didn't push it.
  - Check local tags: `git tag -l`
  - Check remote tags: `git ls-remote --tags origin`
  - Push missing tag: `git push origin <tag-name>`

## Notes on provenance and security

- We avoid long‑lived API tokens by using PyPI Trusted Publishers (OIDC).
- The workflow enables build attestations (PEP 740). PyPI may surface a “Verified” badge for provenance.

## Yank or rollback

- PyPI supports yanking a release (soft removal) via the web UI.
- To fix a broken release, cut a new patch version and publish (preferred over deleting files).

## Summary (quick start)

1. Update CHANGELOG and bump version in `pyproject.toml` and `src/asxshorts/__init__.py`.
2. Commit: `release: vX.Y.Z`.
3. Tag and push: `git tag vX.Y.Z && git push origin main --follow-tags`.
4. **VERIFY TAG WAS PUSHED**: `git ls-remote --tags origin | grep vX.Y.Z`
5. Check GitHub Actions tab for the workflow run.
6. Approve the `pypi-release` environment when prompted (stable only).
7. Verify install, import, and CLI version from PyPI.
