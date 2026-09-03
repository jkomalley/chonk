# Contributing to dsz

Thanks for your interest in improving `dsz`. This guide covers everything you
need to get set up and land a change. For tool *usage*, see the
[README](README.md).

## Ways to contribute

- **Report a bug** or **request a feature** by [opening an issue](https://github.com/jkomalley/dsz/issues).
- **Submit a pull request** for a fix or improvement.

For anything large or behavior-changing, please open an issue to discuss the
approach before investing time in a PR.

## Development setup

**Prerequisites:** Python 3.11+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/jkomalley/dsz.git
cd dsz
just install               # uv sync + pre-commit install
```

Or, without [`just`](https://github.com/casey/just):

```bash
uv sync                    # create the venv and install all dependencies
uv run pre-commit install  # enable the git hooks
```

## Project layout

The package uses a `src/` layout:

| Module | Responsibility |
| --- | --- |
| `core.py` | All scanning and formatting logic: size formatting, per-entry and per-directory sizing, and report generation. |
| `cli.py` | The `dsz` command-line entry point (`argparse`) and `--min-percent` validation. |
| `__main__.py` | `python -m dsz` alias for the CLI. |
| `__init__.py` | Package docstring. `dsz` is a CLI tool, not a library, so nothing is re-exported. |

## Running checks

The repo uses [`just`](https://github.com/casey/just) as a task runner. Run
everything before pushing:

```bash
just check      # format-check + lint-check + typecheck + test-cov
```

Or run individual tasks:

```bash
just format        # ruff format
just format-check  # ruff format --check
just lint          # ruff check --fix
just lint-check    # ruff check
just typecheck     # ty check
just test          # pytest
just test-cov      # pytest with coverage
```

Each task maps to a plain `uv run …` command, so you can run them directly if
you'd rather not install `just`.

## Coding standards

- **Style & linting:** [`ruff`](https://docs.astral.sh/ruff/) with nearly all
  rules enabled (see `pyproject.toml` for the pragmatic exceptions). Run
  `just format` and `just lint` before committing.
- **Type checking:** the codebase is fully typed; `just typecheck` must pass.
- **Docstrings:** Google-style, on every public function and class.
- **Comments:** explain *why*, not *what*. Lean toward documenting non-obvious
  decisions; skip comments that merely restate the code.
- **Line length:** 88 characters.

### Testing

- Every new code path needs a test; check coverage with `just test-cov`.
- Tests use real filesystem operations via pytest's `tmp_path` rather than
  mocks wherever practical — this is a filesystem tool, and the real syscalls
  are what need to behave correctly.
- **Race tolerance is the single most important invariant.** An entry deleted
  or made unreadable between being listed and being examined must contribute
  0 bytes and still be listed — never dropped, never raised. Test that
  deterministically: create the entry, list it via `os.scandir`, delete it,
  *then* call the sizing function. No timing or threading needed.

## Pull requests

- Branch off `main`; one logical change per PR.
- Keep commits atomic — a single coherent change each, not a bundle of
  unrelated edits.
- Include tests for any new or changed behavior.
- Make sure `just check` passes cleanly before you open the PR.

CI runs the full check suite against Python 3.11–3.14 on every pull request.

## Releasing

A release starts with a version bump merged to `main`, opened as its own PR.

Choose the bump from the changes since the **last release tag**, not just your
latest work:

```bash
git log "$(git describe --tags --abbrev=0)"..HEAD --oneline
```

Map the conventional-commit types in that range to a [semver](https://semver.org/)
bump and apply it:

| Changes since last release | Bump | Command |
| --- | --- | --- |
| Any `feat:` | minor | `just bump-version minor` |
| Only `fix:` / `docs:` / `chore:` | patch | `just bump-version patch` |
| A breaking change (`feat!:`, `BREAKING CHANGE`) | major¹ | `just bump-version major` |

¹ While the project is pre-1.0, breaking changes are released as a **minor**
bump per semver's 0.x convention.

Add the matching `## [x.y.z]` entry to `CHANGELOG.md` in the same PR, in
[Keep a Changelog](https://keepachangelog.com/) format.

The `version-guard` CI job fails any release PR whose bump is too small for the
commits since the last release (for example, shipping a `feat:` as a patch).
Features merged to `main` without a release accumulate, so the bump must account
for all of them, not just the most recent change.

Once the bump is on `main`, the rest is automatic. `cd.yml` runs after CI
succeeds, compares the version against PyPI, and no-ops if it is already
published. Otherwise it extracts the `## [x.y.z]` section of `CHANGELOG.md`
for the release notes, builds, publishes via PyPI trusted publishing, then
tags `vX.Y.Z` and creates the GitHub release. Tagging and release creation
are the last steps, downstream of a successful publish -- never the trigger.

A missing changelog entry fails the release **before** anything is published,
rather than shipping empty notes.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
