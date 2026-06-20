# RFdiffusion3 Design Pipeline (Colab)

[![Single](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/amiralito/RFdiffusion3_Colab/blob/main/RFdiffusion3_design_pipeline.ipynb)

End-to-end protein design on Google Colab using the
[RosettaCommons Foundry](https://github.com/RosettaCommons/foundry) stack:
**RFD3 → LigandMPNN → RF3**. Generate backbones with all-atom diffusion, design sequences
with LigandMPNN, and validate by refolding with RF3 — all from a single notebook with
form-field inputs.

Supports unconditional generation, motif scaffolding, protein–protein **binder design**, and
**Cn/Dn symmetric** design (e.g. symmetric caps against oligomeric targets).

## Pipeline

```
RFD3            →   LigandMPNN          →   RF3
(all-atom           (sequence design /      (AF3-class structure
 backbone            inverse folding)        prediction, validation)
 diffusion)
```

## Requirements

- Google Colab with a **GPU runtime** (`Runtime → Change runtime type → GPU`).
- **A100 (40/80 GB) or L4 recommended.** T4 (16 GB) works for small/trimmed targets with
  `LOW_MEMORY` enabled.
- ~10 GB for model weights (downloaded once per session, or persisted to Google Drive).

## Quick start

1. Open the notebook in Colab and select a GPU runtime.
2. Run **Step 1** (GPU check) and **Setup** (output directory / optional Drive mount).
3. Run **Step 2** (install) and **Step 3** (download weights) — slow, once per session.
4. Provide a target (**Step 4**), prepare it (**Steps 5–6**), configure the design (**Step 7**).
5. Run **RFD3 → MPNN → RF3** (**Steps 8–10**), collect metrics (**Step 11**), download (**Step 12**).

## Notebook structure

| Step  | Purpose |
|-------|---------|
| 1     | Check the allocated GPU |
| Setup | Set the `WORK` output directory; optionally mount Google Drive |
| 2     | Install `rc-foundry[all]` |
| 3     | Download RFD3 / LigandMPNN / RF3 weights |
| 4     | Upload or fetch the target structure |
| 5     | *(Symmetric only)* align the symmetry axis to z and idealise the assembly |
| 6     | Strip ligands / trim residues (keeps the model within GPU memory) |
| 7     | Build the RFD3 `input.json` |
| 8     | Run RFD3 backbone generation |
| 9     | LigandMPNN sequence design |
| 10    | RF3 refold / validation |
| 11    | Collect confidence metrics and rank designs |
| 12    | Download / persist results |

## Configuring a design (Step 7)

A design is specified by a **contig** plus optional **hotspots**.

**Contig** — a left-to-right recipe for the output structure:
- Chain-labelled ranges (`A210-260`) are **kept from the input** as fixed motif.
- Unlabelled ranges (`100-150`) are **designed** (length sampled uniformly in the range).
- `/0` is a **chain break** (separates target from binder, or one designed segment from the next).

**Hotspots** — interface residues the binder should contact, e.g. `A230-240,D230-240`.

**Symmetric** — set `USE_SYMMETRY=True` + `SYM_ID` (e.g. `C6`); the contig describes one
asymmetric unit and RFD3 replicates it n-fold.

### Design modes

| Mode | `INPUT_PDB` | `CONTIG` | Symmetry |
|------|-------------|----------|----------|
| Unconditional / monomer | *(empty)* | *(empty)*; set `BINDER_LENGTH` | off |
| Binder vs one protomer | target | `A<range>,/0,<len>` | off |
| Binder bridging protomers | target | `A<range>,/0,B<range>,/0,<len>` | off |
| Symmetric cap | symmetric target | `A<range>,/0,<len>` (one asymmetric unit) | on (`C6`, …) |

## Sequence design (Step 9)

- `FIXED_CHAINS` — keep the target chains fixed so **only the binder is designed**
  (otherwise MPNN redesigns the target sequence too).
- `TIE_CHAINS` — *(symmetric only)* tie binder subunit chains to one shared sequence
  (`--homo_oligomer_chains`), required so a symmetric cap keeps its symmetry.
- `MODEL_TYPE = ligand_mpnn` works for protein-only targets too; use it whenever the target
  retains ligands / nucleotides / metals.

> **Note:** `mpnn` requires an explicit `--checkpoint_path` and `--is_legacy_weights` (unlike
> `rfd3`/`rf3`, which auto-discover weights). The cell handles this automatically.

## Outputs

Everything lands under your `WORK` directory (local or Drive):

- `rfd3_out/` — generated backbones (`.cif.gz`)
- `mpnn_out/` — designed sequences (`.cif`, `.fa`)
- `rf3_out/`  — refolded structures + confidence
- `design_metrics.csv` — ranked metrics table

## Notes & gotchas

- **Memory** — RFD3 cost scales as O(N²) in tokens. Trim the input (Step 6) and strip ligands.
  `LOW_MEMORY=True` and `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` help on small GPUs.
- **Symmetric runs** use `diffusion_batch_size=1`; scale the number of designs with `N_DESIGNS`.
- **Chain relabelling** — RFD3 renumbers/relabels output chains; re-inspect chain IDs before
  setting `FIXED_CHAINS`.
- **Validation is in-family** — RF3 shares lineage with RFD3, so cross-check top designs with an
  independent predictor (AlphaFold3, Boltz-2) before committing.

## Credits

Built on [RosettaCommons/foundry](https://github.com/RosettaCommons/foundry)
(RFD3, LigandMPNN, RF3). See the Foundry repository and RFdiffusion3 documentation for model
details and licensing.
