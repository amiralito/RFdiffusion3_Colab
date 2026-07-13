#!/usr/bin/env python3
"""
extract_binder_fastas.py  —  pull the designed binder sequence out of each Foundry
LigandMPNN output structure and write them all to a single FASTA.

MPNN writes one designed structure (.cif) per sequence, containing the fixed target
chains plus the redesigned binder chain. This collects just the binder chain's sequence
from every design into one file, ready for ordering / clustering / analysis.

Identifying the binder:
  --target-chains A,B,C   -> binder = every other chain (unambiguous; use this)
  (omitted)               -> falls back to "the chain whose length is not the most
                             common" (works for e.g. 6 identical targets + 1 binder;
                             ambiguous for symmetric designs — pass --target-chains).

Usage
-----
    python3 extract_binder_fastas.py MPNN_OUT_DIR
    python3 extract_binder_fastas.py MPNN_OUT_DIR --target-chains B,C,D,E,F,G
    python3 extract_binder_fastas.py MPNN_OUT_DIR --out binders.fasta

Requires: biotite  (pip install biotite)
"""
import argparse
import glob
import os
import sys
from collections import Counter

import numpy as np

try:
    import biotite.structure as struc
    import biotite.structure.io as strucio
except ImportError:
    sys.exit("This script needs biotite:  pip install biotite")

THREE2ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLN": "Q", "GLU": "E",
    "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F",
    "PRO": "P", "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    "MSE": "M", "SEC": "U",
}


def chain_sequence(atoms, ch):
    m = (atoms.chain_id == ch) & (atoms.atom_name == "CA")
    order = np.argsort(atoms.res_id[m])
    return "".join(THREE2ONE.get(rn, "X") for rn in atoms.res_name[m][order])


def binder_chains(atoms, target_chains):
    chains = sorted(set(atoms.chain_id.tolist()))
    if target_chains:
        return [c for c in chains if c not in target_chains]
    # heuristic: binder = chain(s) not matching the most common residue count
    counts = {c: len(np.unique(atoms.res_id[atoms.chain_id == c])) for c in chains}
    freq = Counter(counts.values())
    mode_len, mode_n = freq.most_common(1)[0]
    if list(freq.values()).count(mode_n) > 1:
        print("  WARNING: ambiguous chain lengths; pass --target-chains for a reliable split")
    return [c for c, n in counts.items() if n != mode_len]


def main():
    ap = argparse.ArgumentParser(description="Extract designed binder sequences from MPNN CIFs into one FASTA.")
    ap.add_argument("path", help="folder of MPNN outputs (searched recursively) or a single .cif")
    ap.add_argument("--target-chains", default="", help="comma-separated target chains to exclude, e.g. B,C,D,E,F,G")
    ap.add_argument("--out", default="", help="output FASTA path (default: <path>/binder_sequences.fasta)")
    args = ap.parse_args()

    target = set(c.strip() for c in args.target_chains.split(",") if c.strip())

    p = args.path
    if os.path.isdir(p):
        cifs = sorted(f for f in glob.glob(os.path.join(p, "**", "*.cif"), recursive=True))
        default_out = os.path.join(p, "binder_sequences.fasta")
    elif os.path.isfile(p):
        cifs = [p]
        default_out = os.path.splitext(p)[0] + "_binder.fasta"
    else:
        sys.exit(f"Path not found: {p}")

    if not cifs:
        sys.exit("No .cif files found.")

    out_path = args.out or default_out
    records, n_files = [], 0
    for cif in cifs:
        try:
            a = strucio.load_structure(cif)
            a = a[struc.filter_amino_acids(a)]
        except Exception as e:
            print(f"  skip {os.path.basename(cif)}: {e}")
            continue
        n_files += 1
        stem = os.path.basename(cif)
        for ext in (".cif", ".pdb"):
            stem = stem.replace(ext, "")
        seen = set()
        for ch in binder_chains(a, target):
            seq = chain_sequence(a, ch)
            if not seq or seq in seen:
                continue
            seen.add(seq)
            records.append((f"{stem}|chain_{ch}|len_{len(seq)}", seq))

    with open(out_path, "w") as fh:
        for header, seq in records:
            fh.write(f">{header}\n{seq}\n")

    print(f"\nRead {n_files} structure(s); wrote {len(records)} binder sequence(s) -> {out_path}")


if __name__ == "__main__":
    main()
