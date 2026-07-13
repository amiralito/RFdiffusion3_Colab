# RFdiffusion3 Design Pipeline (Colab)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amiralito/RFdiffusion3_Colab/blob/main/RFdiffusion3_design_pipeline.ipynb)

End-to-end protein design on Google Colab using the
[RosettaCommons Foundry](https://github.com/RosettaCommons/foundry) stack:
**RFD3 → LigandMPNN → RF3**. Generate backbones with all-atom diffusion, design sequences
with LigandMPNN, and validate by refolding with RF3 — from a single notebook driven by
form fields, with a raw-YAML escape hatch for full control.

Supports unconditional generation, motif scaffolding, protein–protein **binder design**, and
**Cn/Dn symmetric** design (e.g. symmetric caps against oligomeric targets).

## Features

- **Two ways to configure a run** — a form-field builder for common cases, or paste raw RFD3
  YAML for full control (atom-level hotspots, explicit `ori_token`, per-assembly `length`,
  multiple jobs in one pass, and any other RFD3 field).
- **Google Drive integration** — persist a whole run to Drive, and cache the model weights so
  they download **once** and are reused by every future session.
- **Timestamped, named runs** — each run writes to its own `runs/<date-time>_<name>/` folder, so
  runs never overwrite each other.
- **Code-free UI** — every step is a form; code is hidden by default (toggle "Show code" if needed).
- **Symmetric design** — axis alignment + idealisation with a built-in fold-preservation check,
  and symmetric sequence tying in LigandMPNN.
- **Clean outputs** — MPNN structures are auto-repaired for ChimeraX/PyMOL, and designed binder
  sequences are auto-exported to a single FASTA.
- **Utility scripts** for fixing and extracting outputs after download (see below).

## Pipeline

```
RFD3            →   LigandMPNN          →   RF3
(all-atom           (sequence design /      (AF3-class structure
 backbone            inverse folding)        prediction, validation)
 diffusion)
```

## Requirements

- Google Colab with a **GPU runtime** (`Runtime → Change runtime type → GPU`).
- **A100 / L4 / RTX 6000-class recommended.** T4 (16 GB) works for small/trimmed targets with
  `LOW_MEMORY` enabled.
- ~10 GB for model weights (downloaded once, or cached on Google Drive across sessions).

## Quick start

1. Open the notebook in Colab and select a GPU runtime.
2. Run **Step 1** (GPU check) and **Setup** (name the run, mount Drive).
3. Run **Step 2** (install) and **Step 3** (download weights — skipped automatically if cached).
4. Provide and prepare a target (**Steps 4–6**), or supply your own prepared PDB and skip to config.
5. Configure the design — the **form (Step 7)** or the **advanced YAML cell (Step 7 · advanced)**.
6. Run **RFD3 → MPNN → RF3** (**Steps 8–10**), collect metrics (**Step 11**), download (**Step 12**).

## Notebook structure

| Step  | Purpose |
|-------|---------|
| 1     | Check the allocated GPU |
| Setup | Name the run, mount Google Drive, set the per-run `WORK` directory, point at cached weights |
| 2     | Install `rc-foundry[all]` |
| 3     | Download RFD3 / LigandMPNN / RF3 weights (skips if already cached) |
| 4     | Upload or fetch the target structure |
| 5     | *(Symmetric only)* align the symmetry axis to z and idealise, with a fold-preservation guard |
| 6     | Strip ligands / trim residues (keeps the model within GPU memory) |
| 7     | Build the RFD3 `input.json` from form fields |
| 7 · advanced | Paste raw RFD3 YAML to override the form (full field control) |
| 8     | Run RFD3 backbone generation |
| 9     | LigandMPNN sequence design → auto CIF repair + binder FASTA export |
| 10    | RF3 refold / validation |
| 11    | Collect confidence metrics and rank designs |
| 12    | Download / persist results |

## Configuring a design

### Form (Step 7)

A design is specified by a **contig** plus optional **hotspots**.

**Contig** — a left-to-right recipe for the output structure:
- Chain-labelled ranges (`A210-260`) are **kept from the input** as fixed motif.
- Unlabelled ranges (`100-150`) are **designed** (length sampled uniformly in the range).
- `/0` is a **chain break** (separates target from binder, or one designed segment from the next).

**Hotspots** — interface residues the binder should contact, e.g. `A230-240,B230-240`.

**Symmetric** — set `USE_SYMMETRY=True` + `SYM_ID` (e.g. `C6`); the contig describes one
asymmetric unit and RFD3 replicates it n-fold.

| Mode | `INPUT_PDB` | `CONTIG` | Symmetry |
|------|-------------|----------|----------|
| Unconditional / monomer | *(empty)* | *(empty)*; set `BINDER_LENGTH` | off |
| Binder vs one chain | target | `A<range>,/0,<len>` | off |
| Binder bridging chains | target | `A<range>,/0,B<range>,/0,<len>` | off |
| Symmetric cap | symmetric target | `A<range>,/0,<len>` (one asymmetric unit) | on (`C6`, …) |

### Advanced YAML (Step 7 · advanced)

For anything the form can't express, paste raw RFD3 YAML. This exposes every RFD3 field —
atom-level `select_hotspots` (e.g. `A233: OD1,ND2`), an explicit `ori_token` (a fixed 3-D
center-of-mass for the designed region), whole-assembly `length`, `select_fixed_atoms`,
`dialect`, and more. Multiple top-level entries run as separate jobs in one pass. Running this
cell overrides the form.

> If a run relies on an explicit `ori_token`, the input must keep its original coordinate frame —
> **skip Step 5** (idealisation moves coordinates and would invalidate the token) and prepare the
> target with Step 6 only (which just masks atoms).

## Sequence design (Step 9)

- `FIXED_CHAINS` — keep the target chains fixed so **only the binder is designed** (otherwise
  MPNN redesigns the target sequence too).
- `TIE_CHAINS` — *(symmetric only)* tie binder subunit chains to one shared sequence
  (`--homo_oligomer_chains`), required so a symmetric cap keeps its symmetry.
- `DIFFUSION_BATCH_SIZE` *(Step 8)* — designs per forward pass; lower it if a large target OOMs.
- The cell auto-locates the LigandMPNN checkpoint and passes the required
  `--checkpoint_path` / `--is_legacy_weights` (unlike `rfd3`/`rf3`, MPNN does not auto-discover weights).
- After the run it **repairs the output CIFs** so they open in ChimeraX/PyMOL and **writes
  `binder_sequences.fasta`** — the designed binder sequence from every structure, in one file.

## Outputs

Everything lands under your run's `WORK` directory (local or Drive):

- `rfd3_out/` — generated backbones (`.cif.gz`)
- `mpnn_out/` — designed structures (`.cif`), raw MPNN FASTAs (`.fa`), and `binder_sequences.fasta`
- `rf3_out/` — refolded structures + confidence
- `design_metrics.csv` — ranked metrics table

## Utility scripts

Standalone, dependency-light helpers for outputs after you download them:

- **`fix_mpnn_cifs.py`** — makes MPNN CIFs strict-mmCIF compliant so ChimeraX/PyMOL can open them
  (MPNN writes bare `[]` metadata values that strict parsers reject). Recursive, idempotent,
  optional backup. The notebook already does this in-line; this is for files fixed after the fact.
- **`extract_binder_fastas.py`** — pulls the designed binder sequence from a folder of MPNN
  structures into one FASTA. Identify the binder with `--target-chains A,B,...` (recommended) or
  let it fall back to the odd-length chain.

```bash
python3 fix_mpnn_cifs.py       /path/to/mpnn_out
python3 extract_binder_fastas.py /path/to/mpnn_out --target-chains B,C,D,E,F,G
```

## Notes & gotchas

- **Memory** — RFD3 cost scales as O(N²) in tokens. Trim the input (Step 6) and strip ligands.
  `LOW_MEMORY=True`, a smaller `DIFFUSION_BATCH_SIZE`, and `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`
  all help; the biggest lever is a tighter residue window.
- **Chain relabelling** — RFD3 relabels output chains, and the labels can differ between jobs and
  even between models. Always re-inspect chain IDs before setting `FIXED_CHAINS` — the reliable
  rule is "the designed chain is the one whose length matches the binder range."
- **Symmetric axis alignment** — Step 5 aligns the symmetry axis to z with a numerically robust
  rotation and verifies the fold is preserved (helix content before vs after). It aborts rather
  than silently corrupting the target.
- **Validation is in-family** — RF3 shares lineage with RFD3, so cross-check top designs with an
  independent predictor (AlphaFold3, Boltz-2) before committing.
- **Scale** — very large campaigns (hundreds of backbones × sequences × refolds) are better run as
  an HPC/SLURM array; the same YAML and CLI run there unchanged.

## Credits

Built on [RosettaCommons/foundry](https://github.com/RosettaCommons/foundry)
(RFD3, LigandMPNN, RF3). See the Foundry repository and RFdiffusion3 documentation for model
details and licensing.
