# Clone inference

[Home](Home.md) · [Next: Ancestry and plasticity](Ancestry-and-Plasticity.md)

SPICE classifies clones using a rooted, supported phylogeny, incoming branch lengths and minimum clone size. Results depend on each of those inputs and choices; automatic threshold stability does not establish biological ground truth.

## Two entry points

```bash
spice phylogeny /data/sample.fasta results/sample-tree sample
```

`phylogeny` runs IQ-TREE, then the shared clone-classification implementation. Its defaults are model `TEST`, 1,000 UFBoot replicates, 1,000 SH-aLRT replicates and one thread. `--threads 0` selects IQ-TREE AUTO. IQ-TREE writes beside the actual alignment supplied to `-s`, including when the FASTA is outside the output directory. Keep that location writable and preserve the supported `.treefile` output.

```bash
spice clones --tree /data/sample.fasta.treefile \
  --output_directory results/sample-clones --prefix sample
```

`clones` uses an existing supported IQ-TREE Newick tree. It needs R and its tree/plotting packages, but **does not require or execute IQ-TREE**, including a version probe. The input filename need not match the prefix or end in `.treefile`. Both entry points use the same rooting, support, cut-selection and export code.

IQ-TREE's paired support labels are **SH-aLRT / UFBoot**; for example, `79.2/93` means SH-aLRT 79.2 and UFBoot 93. Preserve those semantics. The validated major version is IQ-TREE 2.x, tested with 2.4.0; IQ-TREE 3 is not validated.

## Rooting and support

Midpoint rooting is the default. Supplying `--outgroup` takes precedence over `--root_method`; the named tips must exist. `--root_method none` requires an already rooted tree. Choose the biological root deliberately and assess rooting sensitivity.

A qualifying clade must meet both support cutoffs and the incoming-edge threshold. Cutting proceeds from the root downward; a qualifying clade groups all descendant tips. The threshold is an incoming branch length, not a root-to-tip distance. The classifier assumes a bifurcating tree.

| Shared option | Default |
| --- | --- |
| `--uf_support_threshold` | 90 |
| `--sh_support_threshold` | 75 |
| `--branch_cut_min`, `--branch_cut_max`, `--branch_cut_step` | 0, 0.5, 0.01 |
| `--clone_cut_mode` | `auto` |
| `--clone_cut_threshold` | Unset; required for manual mode |
| `--min_trusted_ratio` | 0.95 |
| `--min_partition_stability` | 0.95 |
| `--stability_window` | 3 consecutive eligible thresholds |
| `--min_tips` | 50 |
| `--root_method` | `midpoint` |
| `--outgroup` | Unset |

## Automatic and manual selection

The sweep records cluster counts, trusted-cluster ratio, exportable counts and adjacent-threshold Adjusted Rand Index (ARI). The trusted ratio is the number of trusted clusters divided by all clusters, not a fraction of cells. Partition stability uses the lower adjacent ARI where both neighbors exist.

Automatic selection finds consecutive thresholds meeting the trusted-ratio and stability criteria. Among eligible stable solutions it prefers the fewest clusters, then the longest plateau, resolving ties using median trusted ratio and stability. It selects a grid threshold nearest the plateau center. Minimum clone size controls export, not the definition of the trusted ratio.

If no stable region qualifies, selection fails; no fallback threshold is silently substituted. Inspect the sweep before selecting scientifically justified criteria or manual mode. Manual mode requires `--clone_cut_threshold` and applies that exact value, even between grid points. The nearest swept threshold is marked only for visualization.

## Inspect clone results

Review `Phylo/<prefix>.rooting_info.tsv`, `Phylo/branch_length_cut_analysis.tsv` and `Phylo/<prefix>.clone_cut_selection.tsv` together with the tree plots. Only trusted clusters meeting `--min_tips` are exported to `Clone/Clone_N/Clone_N.nwk` and `.nex`.

`Clone/<prefix>.clone_assignment.tsv` retains every input tip with `cell_id`, `clone_id`, `clone_status` and `in_trusted_cluster`. Assigned cells have a clone ID; others have `NA` with a `small`, `untrusted` or `none` status. Do not treat unassigned cells as evidence that no biological clone exists.

Use a fresh directory per analysis because some sweep/plot filenames are shared rather than prefixed. The detailed [clone engineering guide](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/clones.md) documents the full output inventory and equivalence validation.
