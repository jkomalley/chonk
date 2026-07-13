# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
