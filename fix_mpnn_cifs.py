#!/usr/bin/env python3
"""
fix_mpnn_cifs.py  —  make Foundry LigandMPNN output CIFs openable in ChimeraX/PyMOL.

MPNN writes a provenance block whose empty-list values are bare `[]`, e.g.
    _mpnn_input.remove_ccds          []
Strict mmCIF parsers (ChimeraX, PyMOL) reject an unquoted `[` and refuse the file.
This script quotes those values ( []  ->  '[]' ) in place so the files open.
The atom coordinates are untouched.

Usage
-----
    python3 fix_mpnn_cifs.py                 # fix every *.cif under the current folder
    python3 fix_mpnn_cifs.py PATH            # PATH = a file or a folder (recursive)
    python3 fix_mpnn_cifs.py PATH --backup   # keep a .cif.bak copy of each changed file
    python3 fix_mpnn_cifs.py PATH --dry-run  # report what would change, write nothing
"""
import argparse
import re
import sys
from pathlib import Path

# a data-name line whose entire value is a bare []   ->   quote it as '[]'
PATTERN = re.compile(r"^(\s*_\S+\s+)\[\]\s*$")


def fix_text(text: str):
    """Return (new_text, n_lines_changed)."""
    out, changed = [], 0
    for line in text.splitlines(keepends=True):
        m = PATTERN.match(line)
        if m:
            eol = "\n" if line.endswith("\n") else ""
            out.append(f"{m.group(1).rstrip()} '[]'{eol}")
            changed += 1
        else:
            out.append(line)
    return "".join(out), changed


def iter_cifs(path: Path):
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from sorted(path.rglob("*.cif"))
    else:
        sys.exit(f"Path not found: {path}")


def main():
    ap = argparse.ArgumentParser(description="Quote bare [] values in MPNN CIFs so ChimeraX/PyMOL can open them.")
    ap.add_argument("path", nargs="?", default=".", help="CIF file or folder to search (default: current folder)")
    ap.add_argument("--backup", action="store_true", help="write a .bak copy before changing each file")
    ap.add_argument("--dry-run", action="store_true", help="show what would change without writing")
    args = ap.parse_args()

    files = list(iter_cifs(Path(args.path)))
    if not files:
        print("No .cif files found.")
        return

    n_files_changed = 0
    for f in files:
        try:
            text = f.read_text()
        except Exception as e:
            print(f"skip {f}: {e}")
            continue
        new_text, n = fix_text(text)
        if n == 0:
            continue
        n_files_changed += 1
        if args.dry_run:
            print(f"[dry-run] would fix {n} line(s): {f}")
            continue
        if args.backup:
            f.with_suffix(f.suffix + ".bak").write_text(text)
        f.write_text(new_text)
        print(f"fixed {n} line(s): {f}")

    verb = "would be" if args.dry_run else "were"
    print(f"\n{n_files_changed} of {len(files)} CIF file(s) {verb} fixed.")


if __name__ == "__main__":
    main()
