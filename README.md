# Single-cell Plasticity Inference and Clonal Evolution (SPICE)

<img src="SPICE.png" alt="SPICE" width="300">

SPICE provides a modular command-line workflow for somatic SNV filtering, lineage-tree inference and clone assignment, ancestral cell-state reconstruction, and ordered-state plasticity analysis.

**Status:** the ancestry/plasticity integration is an implementation candidate. Real-data validation, comparison against historical outputs, and dataset-specific default tuning are still pending. Implemented analyses do not establish biological direction or validate a lineage tree by themselves.

Canonical repository: [Diaz Lab SPICE](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE).

## Workflow

| Module | Input | Main result |
| --- | --- | --- |
| `filter` | Monopogen somatic-SNV outputs and selected cell barcodes | Filtered SNV matrix and FASTA |
| `phylogeny` | FASTA | IQ-TREE2 inference, rooting, support-aware clone cutting, clone trees and assignments |
| `ancestry` | One rooted lineage tree and tip cell states | BayesTraits MultiState MCMC posteriors and convergence diagnostics |
| `plasticity` | The same tree/states, ancestral states, and a biological state-order table | Edge classes, dedifferentiation percentage, and optional permutation significance |

Two entry routes are supported:

- **Somatic-SNV-derived lineage:** `filter → phylogeny → ancestry → plasticity`.
- **Externally supplied lineage, including static-barcode-derived trees:** start at `ancestry` with a prepared rooted tree, then run `plasticity`. SPICE does not reconstruct a static-barcode tree from raw barcodes. The `phylogeny` command takes FASTA, not an external-tree argument.

Run ancestry/plasticity separately for each clone tree or other biologically justified lineage unit. The CLI does not automatically iterate over the clone-assignment table.

## Installation and dependencies

Run from a source checkout; this repository currently has no Python package-installation configuration.

```bash
git clone https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.git
cd SPICE
python3 SPICE.py --help
```

Use Python 3.9 or later with `pandas`, and an R installation with `Rscript` on PATH. Module dependencies are:

| Module | Additional dependencies |
| --- | --- |
| `filter` | R: `dplyr`, `progress` |
| `phylogeny` | IQ-TREE2; R: `ape`, `phangorn`, `phytools`, `ggplot2`, `ggtree`, `ggsci` |
| `ancestry` | BayesTraits; R: `ape`, `coda`, `btw`, `janitor` |
| `plasticity` | R: `ape`, `coda`, `btw`, `janitor`; BayesTraits when permutations are enabled |

The Python entry point imports `pandas` for all subcommands. The current plasticity entry point loads the ancestry dependencies even when permutations are disabled. Install R packages through their appropriate package sources; `ggtree` is distributed through Bioconductor. A tested, pinned environment is not yet provided.

Set `IQTREE2_BIN` if IQ-TREE2 is not discoverable on PATH. For BayesTraits, pass `--bayestraits_bin /absolute/path/to/BayesTraitsV4`, set `BAYESTRAITS_BIN`, or use a recognized executable on PATH. Use `python3 SPICE.py <module> --help` for the complete current option list.

## Inputs

### Monopogen and barcodes

`filter` expects the Monopogen chromosome 1–22 output layout, including per-chromosome cell/SNV tables and SNV matrix RDS files. The selected-barcode file is tab-separated with a **`cell_barcodes` header**:

```text
cell_barcodes
cell_001
cell_002
```

### Lineage tree and cell states

Supply exactly one rooted Newick tree, or a NEXUS file with `.nex`/`.nexus` extension. Tip labels must be unique. Every tip needs a state; extra state-table cells are ignored. Use a two-column TSV with `cell_id` first and `state` second:

```text
cell_id	state
cell_001	Progenitor
cell_002	Differentiated
```

Ancestry validates rooting but does not root the supplied tree. Root external trees before analysis and ensure branch lengths and topology are appropriate for BayesTraits. Use the **same tree file** for ancestry and plasticity: internal IDs `T1`, `T2`, etc. follow the parsed tree's node numbering, not persistent biological identifiers. Re-rooting or reordering a tree can invalidate that correspondence.

### Biological state order

Plasticity requires a headered TSV with `state` and numeric `order` columns. Higher values mean more differentiated states; these values must be supplied from biological knowledge.

```text
state	order
Progenitor	1
Intermediate	2
Differentiated	3
```

Every observed state must be covered. Equal order values are classified as self-renewal, including different labels assigned the same order. BayesTraits state encoding is deterministic but does not encode this biological ordering or constrain its transition-rate model to adjacent states.

## Example commands

Run these from the repository directory after substituting your own inputs. Use a separate output directory per lineage/clone. **Retain the trailing slash on filter/phylogeny output directories**, because existing helpers concatenate paths. Avoid spaces in paths used by the legacy phylogeny command.

### 1. Filter somatic SNVs

```bash
python3 SPICE.py filter /data/monopogen/ results/sample/ sample /data/cell_barcodes.tsv
```

Current defaults: reference/alternative support thresholds `5`/`5`, SVM score `0.1`, LD-refinement score `0.25`, maximum alternative BAF `0.5`, minimum alternative-supporting cells per SNV `5`, minimum SNVs per cell `5`, and `--threads 1`.

Principal outputs in `results/sample/` include `sample.cellID.filter.csv`, `sample.SNVs.filter.csv`, `sample.SNV_mat.RDS`, `sample.SNV_mat.filter.csv`, and `sample.SNV_mat.filter.fasta`. The final CSV stores variants as rows and cells as columns; FASTA stores one sequence per cell.

### 2. Infer phylogeny and assign clones

```bash
python3 SPICE.py phylogeny \
  results/sample/sample.SNV_mat.filter.fasta results/sample/ sample
```

Rooting defaults to `--root_method midpoint`. `--outgroup cell_001` (or multiple tip names) takes precedence and enables outgroup rooting. `--root_method none` requires an already rooted inferred tree; it does not add an external-tree input route.

Clone cutting defaults to `--clone_cut_mode auto`. The existing selection heuristic uses trust, adjacent-partition stability, and parsimony over the branch-length grid; it is not a guarantee of the biologically optimal clone count. A manual threshold can be supplied explicitly:

```bash
python3 SPICE.py phylogeny \
  results/sample/sample.SNV_mat.filter.fasta results/manual/ sample \
  --clone_cut_mode manual --clone_cut_threshold 0.10
```

`0.10` is an example, not a recommended threshold. Relevant unchanged defaults:

| Setting | Default |
| --- | --- |
| IQ-TREE2 model | `TEST` |
| UFBoot / SH-aLRT replicates | `1000` / `1000` |
| UFBoot / SH-aLRT support thresholds | `90` / `75` |
| Branch-cut grid min / max / step | `0` / `0.5` / `0.01` |
| Minimum clone tips | `50` |
| Minimum trusted ratio / partition stability | `0.95` / `0.95` |
| Stability window | `3` |
| `--include_failed_chisq` parser default | `false` (currently not wired into execution) |

Outputs include IQ-TREE2 files, `Phylo/` plots and diagnostics, `Phylo/sample.rooting_info.tsv`, `Phylo/branch_length_cut_analysis.tsv`, `Phylo/sample.clone_cut_selection.tsv`, and `Clone/Clone_1/Clone_1.nex` plus `.nwk` files for qualifying clones.

`Clone/sample.clone_assignment.tsv` standardizes cell assignments with columns `cell_id`, `clone_id`, `clone_status`, and `in_trusted_cluster`. Only trusted, size-qualified clusters receive a clone ID; other cells retain an audit status and an `NA` clone ID. This table supports downstream joins; ancestry/plasticity currently accept individual trees and state tables directly.

### 3. Infer ancestral states

```bash
python3 SPICE.py ancestry \
  results/sample/Clone/Clone_1/Clone_1.nex /data/cell_states.tsv \
  results/clone1/ clone1 --bayestraits_bin /path/to/BayesTraitsV4
```

For an external lineage, replace the tree argument with its rooted Newick/NEXUS path; filtering and IQ-TREE2 are unnecessary.

Defaults are 3 MCMC chains, 1,000,000 iterations per chain, 200,000 burn-in iterations, sampling every 1,000 iterations, 10 stepping stones of 1,000 iterations, `--hyperprior 'exp 0 10'`, and up to 3 parallel chains. ESS threshold is `200`, PSRF threshold is `1.1`, and minimum ancestral posterior probability is `0.90`.

Outputs:

- `clone1.ancestral_states.tsv`: internal-node IDs, inferred state/code, posterior mean for the selected state, posterior quantiles, confidence flag, and per-state posterior means.
- `clone1.mcmc_diagnostics.tsv`: parameter-level ESS, PSRF point/upper estimates, and pass flags. PSRF is unavailable for a single chain.
- `clone1.state_mapping.tsv`, `clone1.bayestraits_traits.tsv`, and `clone1.ancestry_run_info.tsv`: encoding, BayesTraits input, and run settings.
- `MCMC1/`, etc.: command/AddNode files, BayesTraits logs, stdout and stderr.
- `clone1_ASE.txt`: historical compatibility export, not the standard plasticity input.

**QC is reported, not enforced:** posterior summaries pool parsed chains even when convergence flags fail. Inspect diagnostics before interpretation. Node confidence is based on posterior probability and is separate from convergence status.

### 4. Classify transitions and test plasticity

```bash
python3 SPICE.py plasticity \
  results/sample/Clone/Clone_1/Clone_1.nex /data/cell_states.tsv \
  results/clone1/clone1.ancestral_states.tsv /data/state_order.tsv \
  results/clone1/ clone1 --perm_replicates 0
```

Each parent-to-child edge is classified as self-renewal (equal order), differentiation (increasing order), dedifferentiation (decreasing order), or uncertain. Internal endpoints must have a true confidence flag and posterior probability at least `--min_ancestral_probability` (default `0.90`). Tips use observed states with probability 1. Missing/unusable endpoint states produce uncertain transitions.

```text
cellular_plasticity (%) = 100 × dedifferentiation /
                         (self-renewal + differentiation + dedifferentiation)
```

Uncertain edges are excluded from this denominator. All edges are counted equally; branch lengths do not weight the score. With no informative edges, plasticity is `NA`.

For a small **debugging** permutation run, use the same inputs with `--perm_replicates 20 --bayestraits_bin /path/to/BayesTraitsV4`. This is not a production recommendation. Omitting the override runs the current default of **1,000 permutations**, each requiring BayesTraits inference.

Permutations shuffle tip states without replacement on the fixed tree, preserving state counts, and re-estimate ancestry for each replicate. Defaults: 1 chain per permutation, 1,000,000 iterations, 200,000 burn-in, sampling every 1,000 iterations, no stepping stones, `--threads 1`, `--seed 12345`, and `--sig_direction greater`. The seed controls tip-state shuffling; it does not explicitly seed BayesTraits MCMC.

The empirical p-value is `(b + 1)/(n + 1)`, using successful finite null scores. `greater` counts null scores ≥ observed; `less` counts ≤ observed; `two-sided` compares absolute distances from the null median. Failed/non-finite replicates do not contribute. Requested and successful counts are reported. A successful replicate is not necessarily a convergence-passing replicate: the current implementation does not gate on QC or retain per-permutation diagnostic files.

Outputs:

| File suffix (prefixed with `clone1`) | Content |
| --- | --- |
| `.transitions.tsv` | Edge IDs, endpoint states/probabilities and transition class |
| `.plasticity.tsv` | Class counts, informative/total edge counts, fractions and plasticity percentage |
| `.permutation_plasticity.tsv` | Replicate ID, score and status |
| `.plasticity_test.tsv` | Observed/null summaries, empirical p-value, z-score and replicate counts |
| `.plasticity_run_info.tsv` | Inputs and selected run settings |
| `_ASE_Summary.txt`, `_cellular_plasticity.tsv` | Historical compatibility exports |

With zero permutations, the permutation table is empty and significance fields are `NA`.

## Current caveats and validation scope

- `--include_failed_chisq` is accepted by the parser but is not consumed by the current phylogeny execution path; do not rely on it to exclude cells. This pre-existing behavior is unchanged.
- Real-data end-to-end validation, BayesTraits log-format compatibility checks, historical-output regression comparisons, and default tuning remain pending. Syntax checks alone do not validate scientific results.
- Root placement, branch lengths, clone-cut settings, biological state ordering, convergence, and posterior-confidence thresholds can materially affect interpretation. Examine uncertain-edge counts alongside plasticity.
- The default single-chain permutation configuration cannot provide between-chain PSRF; failed/non-finite replicates and lack of QC gating can affect the null distribution.
- Tree/state consistency is checked, but node IDs do not prove that an ancestral-state file came from the same topology. Keep the exact tree with its outputs.
- Historical R scripts remain in `scripts/`; the current CLI uses `ancestry_core.R` and `plasticity_core.R` with their shared utilities. Compatibility exports are not a claim of numerical equivalence to the historical pipeline.
- Epigenetic-regulation and mutational-signature analyses are not exposed by the current four-module CLI.

## License and contact

See [LICENSE](LICENSE). Report implementation issues through the [Diaz Lab repository](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/issues), or contact Bohyeon Yu at bohyeon.yu@ucsf.edu. A complete publication citation will be added when available.
