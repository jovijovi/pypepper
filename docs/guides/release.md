# Release

Publish PyPepper to [PyPI](https://pypi.org/project/pypepper/) by pushing a Git tag. The package version in [`pyproject.toml`](https://github.com/jovijovi/pypepper/blob/main/pyproject.toml) is authoritative; the tag must match it.

## One-time setup

Do this once before the first tag-triggered release.

### GitHub

1. Open the repository **Settings → Environments**.
2. Create an environment named `pypi` (optional: restrict who can deploy).

### PyPI Trusted Publisher

1. Sign in to [PyPI](https://pypi.org/) as a project owner/maintainer of `pypepper`.
2. Open **Publishing** for the project (or pending publisher if the next version is new).
3. Add a **Trusted Publisher** (GitHub):
   - Owner: `jovijovi`
   - Repository: `pypepper`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

No long-lived API token is stored in the repository. A local `.pypirc` (gitignored and listed in `.dockerignore`) is only for manual uploads. If that file is exposed or you suspect a leak, revoke the token on PyPI / TestPyPI, create a new project-scoped token, and update your local `.pypirc`.

## Release checklist

1. Bump `version` in `pyproject.toml` (keep runtime pins in `requirements.txt` / `requirements-dev.txt` in sync when you change dependencies).
2. Update [`CHANGELOG.md`](https://github.com/jovijovi/pypepper/blob/main/CHANGELOG.md) and merge to `main`.
3. On the release commit (usually `main` tip):

```shell
git tag vX.Y.Z
git push origin vX.Y.Z
```

Example: if `pyproject.toml` has `version = "0.6.4"`, the tag must be `v0.6.4`.

4. Watch **Actions → Publish to PyPI**. The workflow runs lint/docs on Python 3.13, then pretest on **Python 3.10 and 3.14** (sample ends of the supported range); build/upload stays on 3.13. A failing pretest or a tag/`pyproject.toml` version mismatch blocks upload.
5. Confirm the version on [https://pypi.org/project/pypepper/](https://pypi.org/project/pypepper/).

## Manual fallback

Local publish (uses your machine credentials / `.pypirc`; prefer Trusted Publisher for tagged releases):

```shell
make publish-test   # TestPyPI
make publish        # PyPI
```

Automated TestPyPI publishing from tags is not configured; use `make publish-test` when needed.
