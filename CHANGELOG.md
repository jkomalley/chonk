# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-09-02

### Changed

- Release tags migrated from unprefixed (`0.1.0`, `0.2.0`) to `v`-prefixed
  (`v0.1.0`, `v0.2.0`), matching the rest of the project family. This also
  makes the CI version-guard functional, which previously matched no tags and
  silently skipped its check.
- Build requirement floor raised to `uv_build>=0.12.0,<0.13.0`.

### Internal

- Automated release pipeline: publishing now runs after CI succeeds on `main`,
  extracting release notes from this file, then tagging and creating the
  GitHub release. Replaces the manual `workflow_dispatch` + `gh release create`
  flow.
- CI `ty` gate pinned to Python 3.14; `fail-fast` disabled so every matrix leg
  reports; `version-guard` job added.
- Test coverage gated at 100%.
- Dependency updates grouped by ecosystem, with a new `pre-commit` ecosystem,
  and minor/patch updates merged automatically.

No behavioural change to the library or CLI. The only `src/` edit is a
`# pragma: no branch` comment on an unreachable loop-exhaustion arc.

## [0.2.0] - 2026-07-13

### Fixed
- A file or directory deleted (or made unreadable) while `dsz` was scanning
  it could crash the whole run with an unhandled exception; such entries are
  now tolerated and treated as 0 bytes.
- A permission error partway through a scan could silently drop every entry
  listed after it from the report.
- Sizes near a 1024-byte unit boundary could render as e.g. `1024.0 KB`
  instead of rolling over to the next unit.
- A directory containing only zero-byte files was reported as if it were
  empty.
- `--min-percent` silently accepted invalid values like `nan`, collapsing
  the entire report into a single `<other>` line with no indication why.

### Added
- TB and PB size units (previously capped at GB).
- FIFOs, sockets, and other non-regular-file entries are now listed
  (at 0 bytes) instead of being silently excluded from the report.

### Changed
- `--min-percent` now validates its input; values outside `[0, 100]` (or
  non-numeric/NaN) are rejected with a usage error instead of silently
  accepted.
- Minimum supported Python version lowered from 3.14 to 3.11.
- Directory scanning is now parallelized for better performance on large
  trees.

## [0.1.0] - 2026-05-23

### Added
- Initial release.
