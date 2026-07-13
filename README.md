# dsz

Show disk usage of a directory's immediate children, sorted by size.

## Installation

```
uv tool install dsz
```

## Usage

```
dsz [PATH] [--min-percent N]
```

- `PATH` — directory to scan (default: current directory)
- `--min-percent N` — collapse entries below N% of the total into a single `<other>` line (default: 1.0; N must be between 0 and 100)

## Example

```
$ dsz ~
/home/user    24.2 GB
   18.2 GB  75% Videos               ###############
    4.1 GB  17% Documents            ###
    1.6 GB   7% Downloads            #
  312.4 MB   1% <other 5>
```

Hidden entries (dot files and directories) and symlinks are excluded from all counts. Drill into a subdirectory by passing it as `PATH`.
