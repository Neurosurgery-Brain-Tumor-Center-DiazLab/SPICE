# Single-cell Plasticity Inference and Clonal Evolution (SPICE)

<img src="SPICE.png" alt="SPICE" width="300">

SPICE combines somatic SNV filtering, phylogenetic inference and subclone classification, ancestral cell-state reconstruction, and cellular plasticity analysis. It uses IQ-TREE for lineage inference and BayesTraits MultiState MCMC to estimate ancestral states. Ordered cell states then define self-renewal, differentiation, and dedifferentiation along lineage edges.

## Table of Contents

- [Workflow](#workflow)
- [Installation](#installation)
- [Input files](#input-files)
- [Somatic SNV filtering](#somatic-snv-filtering)
- [Phylogeny and subclone classification](#phylogeny-and-subclone-classification)
- [Ancestral state estimation](#ancestral-state-estimation)
- [Cellular plasticity](#cellular-plasticity)
- [External lineage example](#external-lineage-example)
- [Additional analysis scripts](#additional-analysis-scripts)
- [License and contact](#license-and-contact)

## Workflow

```text
Monopogen output → import-monopogen ─┐
                                    ├→ standard cell × variant bundle
User-supplied counts + metadata ─────┘
  → filter → IQ-TREE2 → clone/subclone trees ─┐
                                             ├→ ancestry → plasticity
External/static-barcode lineage               │
  → prepared clone/tree ──────────────────────┘
```

For either route, provide cell-state annotations for ancestry and a biological state-order table for plasticity. Analyze each clone using its own rooted tree and output directory. External/static-barcode analyses start with a prepared clone tree and enter at `ancestry`.

## Installation

### Software and packages

Use Python **3.10 or later** (the IQ-TREE helper uses `int | None` annotations), R with `Rscript` on PATH, and a Unix-like environment for parallel filtering. The packages directly loaded by the modular CLI are listed below; package installers also resolve their dependencies.

| Component | Required software/packages | Use |
| --- | --- | --- |
| Python CLI | `pandas` | Imported by the matrix and filtering helpers for all subcommands |
| `filter` | R: `dplyr`, `progress`, `parallel` | Merge chromosome matrices, select cells/variants, parse read counts |
| `phylogeny` | IQ-TREE 2; R: `ape`, `phangorn`, `phytools`, `ggplot2`, `ggtree`, `ggsci` | Tree inference, rooting, clone cutting, tree visualization |
| `ancestry` | BayesTraits; R: `ape`, `coda`, `janitor`, `posterior` | MultiState MCMC, log parsing, ESS/PSRF, node posteriors |
| `plasticity` | R: `ape`, `coda`, `janitor`, `posterior`; BayesTraits for permutations | Edge classification and permutation ancestry |
| R runtime | `parallel`, `stats`, `utils`, `tools`, base graphics | Included with R; no separate installation |

Monopogen is optional. Only users importing its results need to run [Monopogen](https://github.com/KChen-lab/Monopogen) upstream. Direct standard input requires no Monopogen installation or files. The importer uses base R to decode RDS files; the shared filter and phylogeny retain their R/IQ-TREE dependencies.

### Download SPICE and install Python packages

```bash
git clone https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.git
cd SPICE
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pandas
python3 SPICE.py --help
```

### Install R packages

Run in R:

```r
install.packages(c(
  "dplyr", "progress", "ape", "phangorn", "phytools", "ggplot2",
  "ggsci", "coda", "janitor", "posterior", "BiocManager"
))
BiocManager::install("ggtree")
```

`BiocManager` installs Bioconductor packages. The main CLI uses its own BayesTraits log parser and does not require `btw`. Install the BayesTraits executable separately. See the [ggtree package](https://bioconductor.org/packages/ggtree/) for package-specific installation instructions.

### Install external executables

Download an executable appropriate for your system from [IQ-TREE 2](https://github.com/iqtree/iqtree2) and [BayesTraits](https://github.com/AndrewPMeade/BayesTraits-Release). Make the binaries executable and configure their locations, for example:

```bash
chmod +x /path/to/iqtree2 /path/to/BayesTraitsV4
export IQTREE2_BIN=/path/to/iqtree2
export BAYESTRAITS_BIN=/path/to/BayesTraitsV4
```

IQ-TREE resolution uses `IQTREE2_BIN` first (an existing executable path), then `iqtree2`, then `iqtree` on PATH. Set its thread count with `phylogeny --threads`; a value of `0` selects IQ-TREE `AUTO`.

BayesTraits resolution tries `--bayestraits_bin`, then `BAYESTRAITS_BIN`, then `BayesTraitsV4`, `BayesTraitsV4.1.3`, and `BayesTraits` on PATH. An explicitly named executable can have another filename. SPICE sends MultiState/MCMC, `Iterations`, `Burnin`, `HyperPriorAll`, `Sample`, `AddTag`/`AddNode`, `LogFile`, and optional `Stones` commands and reads the resulting `.Log.txt` files. BayesTraits is required for ancestry and for plasticity with a positive permutation count.

### Check the installation

```bash
python3 SPICE.py filter --help
python3 SPICE.py phylogeny --help
python3 SPICE.py ancestry --help
python3 SPICE.py plasticity --help
Rscript -e 'p <- c("dplyr","progress","ape","phangorn","phytools","ggplot2","ggtree","ggsci","coda","janitor","posterior"); stopifnot(all(vapply(p, requireNamespace, logical(1), quietly=TRUE)))'
```

### Environment and version

```bash
conda env create -f environment.yml
conda activate spice
Rscript scripts/install_R_dependencies.R
python SPICE.py --version
```

The `--version` flag prints the code version and exits. The observed server
versions are recorded in [computing environment](docs/computing-environment.md).
Every analysis writes `<prefix>.runtime.json` with the SPICE version, source
hashes, git revision/status when available, Python/R package versions, executable
paths/hashes, settings and completion status. A retained BayesTraits banner is
included when available. Existing runtime records are preserved with timestamped
filenames. Summaries write `<output-filename>.runtime.json` beside the output.
See [CHANGELOG](CHANGELOG.md) for output-format changes and `CITATION.cff` for citation metadata.

## Input files

### Standard cell × variant bundle (schema v1)

A bundle is a directory containing exactly named `matrix.tsv`, `variants.tsv`, and
`cells.tsv` files (UTF-8, tab-separated, with headers). Additional files are ignored.
The matrix is **cells in rows, variants in columns**, not the legacy output CSV
orientation. No transposition, genotype inference, or imputation is guessed.

`matrix.tsv`:

```tsv
cell_id	chr1:10:A:G	chr1:20:C:T
cell_001	3/0	1/2
cell_002	0/4	0/0
```

- The first header is exactly `cell_id`; remaining headers are unique variant IDs.
- IDs are `chrom:pos:REF:ALT`; `pos` is a positive 1-based integer, alleles are
  uppercase A/C/G/T and must differ. Chromosome names contain no colon/whitespace.
- Each entry is **REF read count / ALT read count**, not a VCF genotype. Both are
  nonnegative integers without leading zeros; their sum is at most 2,147,483,647.
  `0/0` means no coverage and becomes `N` in FASTA. Empty, `NA`, `./.`, negative,
  fractional and malformed entries are rejected. Mixed support becomes the
  existing IUPAC ambiguity code; there is no new allele-fraction caller.
- Cell IDs must be unique and contain only letters, digits, `_`, `.`, or `-`.
  `Variant_ID` is reserved for the legacy output CSV. IDs remain unchanged
  through FASTA and downstream tip labels.
- Empty matrices, duplicate headers/cells, ragged rows and inconsistent metadata
  are errors. Distinct variants with identical count patterns remain separate sites.

`variants.tsv` (all five columns required):

```tsv
variant_id	chrom	pos	ref	alt
chr1:10:A:G	chr1	10	A	G
chr1:20:C:T	chr1	20	C	T
```

Every matrix variant must occur exactly once, with matching coordinates/alleles;
extra metadata variants are rejected. Matrix column order defines site order;
metadata row order does not matter. Additional annotation columns are preserved.
Optional quality metadata must include **all six** columns or none:
`Depth_total`, `Depth_ref`, `Depth_alt`, `SVM_pos_score`,
`LDrefine_merged_score`, `BAF_alt`. Values must be finite numbers; empty/`NA`
values become zero during metadata QC, preserving the existing Monopogen behavior.
Other caller scores must not be relabeled as Monopogen scores without justification.

`cells.tsv`:

```tsv
cell_id
cell_001
cell_002
```

Every matrix cell must occur exactly once, with no extra cells. Additional metadata
columns are allowed. Optional `pass_filter` is exactly `true` or `false` (default
`true`) and records upstream cell eligibility; false cells are excluded before
count filtering. Importing Monopogen sets it from the intersection of chromosome
filter lists and preserves per-chromosome metadata in names such as `chr1.index`.

### Optional Monopogen import

For each available `chr*.SNV_mat.RDS`, provide the matching
`chr*.cell_snv.cellID.csv` (with `cell`), `chr*.cell_snv.cellID.filter.csv`
(with `cell`), and `chr*.putativeSNVs.csv`. Putative metadata requires `chr`, `pos`,
`Ref_allele`, `Alt_allele` and the six quality columns above; all additional
annotations, including two-/three-locus scores, are preserved. Raw `.mat.gz` and
`snvID.csv` files are not needed when prepared RDS matrices exist. Partial chromosome
sets and chrX/chrY are supported; every discovered matrix must have its companions.

RDS matrices have variant IDs in row names, cell barcodes in column names, and
`REF_count/ALT_count` entries. Chromosome cell sets must match; differing column
orders are aligned by barcode. Every matrix variant needs putative metadata;
putative records absent from the matrix cannot become observed alignment sites.
Repeated variant IDs are collapsed only when counts and metadata agree; conflicts
are errors. Distinct variant IDs sharing count patterns are never collapsed.

```bash
python3 SPICE.py import-monopogen /data/monopogen inputs sample
# Writes inputs/sample/{matrix,variants,cells}.tsv, without SPICE quality/count filtering.
```

The standalone importer refuses to overwrite an existing bundle. The convenience
workflow can reuse its saved bundle only after re-importing and verifying that
all counts/metadata agree; changed input requires a new output directory/prefix. It retains all matrix cells
and marks upstream eligibility instead of discarding their counts. Import order is
chromosome order, then the original matrix site order; cell order follows the first
chromosome cell metadata. Source RDS filenames are retained in `source_file`.

### Optional selected barcodes

The selected-barcode file has exactly one `cell_barcodes` header:

```text
cell_barcodes
cell_001
cell_002
```

Omit it to use all eligible cells. Duplicate or unknown selected IDs are errors;
known cells marked `pass_filter=false` remain excluded. The selected file determines
cell order when supplied. Otherwise matrix row order is used.

### Cell states: `cell_states.tsv`

Use a tab-separated table with `cell_id` in the first column and `state` in the second:

```text
cell_id	state
cell_001	Progenitor
cell_002	Differentiated
```

Cell IDs must be unique and match tree tip labels exactly. Annotate every tip in the supplied tree; a sample-wide table can include additional cells, which are subset to that tree. A headerless two-column table is also accepted. State labels are encoded deterministically for BayesTraits and recorded in `.state_mapping.tsv`.

### Biological order: `state_order.tsv`

```text
state	order
Progenitor	1
Intermediate	2
Differentiated	3
```

Supply unique state names and numeric order values covering every observed state. Higher order means more differentiated. Equal order values define self-renewal, including transitions between distinct state labels assigned the same order. This biological order is supplied independently of the BayesTraits numeric state codes.

### Clone membership: `clone_assignment.tsv`

The SNV route writes `Clone/<prefix>.clone_assignment.tsv`:

```text
cell_id	clone_id	clone_status	in_trusted_cluster
cell_001	Clone_1	Clone_1	TRUE
cell_002	NA	small	FALSE
```

`cell_id` identifies a tree tip. `clone_id` identifies a trusted, size-qualified clone, or is `NA`. `clone_status` is the clone name for assigned cells or `small`, `untrusted`, or `none`. `in_trusted_cluster` indicates membership in a trusted, size-qualified clone. Use this table to join cell annotations to clone results. For external lineages, retain your known clone membership in a `clone_assignment.tsv` and supply each corresponding tree directly to ancestry/plasticity.

### Trees

Ancestry/plasticity take one rooted Newick tree or a NEXUS file with `.nex`/`.nexus` extension. Use unique, whitespace-free tip labels and a tree with branch lengths suitable for BayesTraits. Keep the exact same tree file for both stages: internal IDs `T1`, `T2`, … correspond to its parsed internal-node numbering.

## Somatic SNV filtering

Both inputs use the same filtering implementation. Metadata QC runs first when enabled, followed by cell eligibility/selection, the existing variant ALT-support count cutoff, and then the cell retained-SNV cutoff. A supporting cell has ALT count > 0. The count filter is one pass in this order; it does not iterate after excluding cells. Distinct genomic variants are retained even when their read-count patterns match; duplicate variant IDs are collapsed only when their patterns agree.

### Usage

```text
python3 SPICE.py filter input_directory output_directory prefix [cell_barcode] [options]
```

```bash
python3 SPICE.py filter /data/monopogen/ results/sample/ sample /data/cell_barcodes.tsv \
  --min_alt_cells_per_snv 5 --min_snvs_per_cell 5 --threads 4
```

Direct input, with the same cutoffs:

```bash
python3 SPICE.py filter inputs/sample results/sample sample --input_format standard \
  --min_alt_cells_per_snv 5 --min_snvs_per_cell 5 --threads 4
```

Output paths may contain spaces and need no trailing slash. Metadata QC additionally
requires `Depth_total >= depth_ref + depth_alt`. With `--variant_qc auto`, the six
quality fields trigger the existing quality thresholds; if absent, only shared
cell/SNV count filtering applies. `metadata` requires the six fields; `none`
explicitly disables metadata QC. Partial quality schemas and changed quality
thresholds when QC is disabled/absent are rejected. No empty FASTA is produced when
filters remove all variants or cells.

### Parameters

| Parameter | Type / accepted values | Default | Description |
| --- | --- | --- | --- |
| `input_directory` | Directory | `Required` | Monopogen output or standard bundle directory, selected by --input_format. |
| `output_directory` | Directory | `Required` | Directory for this stage’s outputs. |
| `prefix` | String | `Required` | Sample/lineage identifier used in output filenames. |
| `cell_barcode` | TSV file | All eligible cells | Optional selected cell barcodes with a cell_barcodes header. |
| `--input_format` | monopogen / standard | `monopogen` | Input representation; preserves the existing convenience command. |
| `--variant_qc` | auto / metadata / none | `auto` | Metadata quality policy; count filtering always applies. |
| `--depth_ref` | Integer ≥ 0 | `5` | Minimum Monopogen Depth_ref value (≥ cutoff). |
| `--depth_alt` | Integer ≥ 0 | `5` | Minimum Monopogen Depth_alt value (≥ cutoff). |
| `--svm_pos_score` | Number | `0.1` | Minimum threshold from the Monopogen SVM module |
| `--ldrefine_merged_score` | Number | `0.25` | Minimum threshold from the Monopogen LD refinement module |
| `--baf_alt` | Number | `0.5` | Maximum threshold for the alternative allele frequency (BAF) |
| `--min_alt_cells_per_snv` | Integer ≥ 0 | `5` | Retain variants with ALT reads in at least this many selected cells. |
| `--min_snvs_per_cell` | Integer ≥ 0 | `5` | Retain cells supporting at least this many variants after the variant-count filter. |
| `--threads` | Integer ≥ 1 | `1` | R worker processes for parsing the SNV matrix. |
| `-h`, `--help` | Flag | Exit only when supplied | Display this stage’s usage and options, then exit. |

### Outputs

Files are written in `output_directory`; `<prefix>` is `sample` in the example.

| File | Content |
| --- | --- |
| `<prefix>.standard/` | Validated unfiltered standard bundle saved by the Monopogen convenience route |
| `<prefix>.cellID.filter.csv` | Selected eligible cells and 1-based analysis indices; original importer indices remain in cells.tsv |
| `<prefix>.selected_cells.tsv` | Selected eligible cells supplied to the existing R filter |
| `<prefix>.SNV_mat.input.tsv` | Quality-filtered variant × selected-cell count matrix supplied to the RDS bridge |
| `<prefix>.SNVs.filter.csv` | Variants passing enabled metadata QC, with preserved annotations |
| `<prefix>.SNV_mat.RDS` | Merged matrix after call filtering and variant-ID deduplication |
| `CellMutationDist.pdf` | Mutation-per-cell and cell-per-mutation distributions before count cutoffs |
| `<prefix>.SNV_mat.filter.csv` | Final selected matrix: `Variant_ID` followed by cell columns, with read-count entries |
| `<prefix>.SNV_mat.filter.fasta` | One nucleotide sequence per cell; mixed REF/ALT support uses IUPAC codes and missing calls use `N` |

## Phylogeny and subclone classification

Infer a maximum-likelihood tree with IQ-TREE, root it, and define clones using incoming branch length and branch support. IQ-TREE dual support labels are read in **SH-aLRT / UFBoot** order. A cluster is accepted when its incoming parent-to-child branch length and both support values meet their thresholds; trusted clusters with at least `min_tips` cells are exported.

### Usage

```text
python3 SPICE.py phylogeny fasta_path output_directory prefix [options]
```

For a single command from counts through clone partitioning, use:

```bash
python3 SPICE.py phylogeny inputs/sample results/sample sample --input_format standard \
  --min_alt_cells_per_snv 5 --min_snvs_per_cell 5 --threads 4
# Or use --input_format monopogen with a Monopogen directory as the first argument.
```

`phylogeny --input_format` defaults to `fasta` (existing behavior). `standard` and
`monopogen` run shared filtering and create `<prefix>.fasta` automatically before
IQ-TREE2. They accept the filtering parameters/defaults above and optional
`--cell_barcode FILE`; `--threads` is shared with IQ-TREE. For these combined routes,
`--threads 0` uses available CPUs for R parsing and IQ-TREE AUTO. Rooting, support,
and auto/manual clone-cut parameters below are unchanged. The default remains
midpoint; use `--outgroup` for a biologically justified root when available.

For the existing separate FASTA route, store the alignment as `<output_directory>/<prefix>.fasta` so that IQ-TREE produces the `<prefix>.fasta.treefile` consumed by clone cutting:

```bash
cp results/sample/sample.SNV_mat.filter.fasta results/sample/sample.fasta
python3 SPICE.py phylogeny results/sample/sample.fasta results/sample/ sample \
  --threads 4 --root_method midpoint --clone_cut_mode auto
```

For outgroup rooting, add `--outgroup cell_001` or several space-separated tip names at the end of the command. Supplying outgroups selects outgroup rooting automatically. `none` retains an already rooted IQ-TREE result.

Automatic clone cutting evaluates the threshold grid, requires the trusted-cluster fraction and adjacent-partition ARI to meet their cutoffs for a consecutive stability window, and prefers the smallest cluster count among eligible solutions. It chooses a grid point nearest the center of the longest such plateau, breaking plateau ties by median trusted ratio and then median stability. Manual mode applies a specified incoming branch-length threshold:

```bash
mkdir -p results/manual/
cp results/sample/sample.SNV_mat.filter.fasta results/manual/sample.fasta
python3 SPICE.py phylogeny results/manual/sample.fasta results/manual/ sample \
  --clone_cut_mode manual --clone_cut_threshold 0.10 --threads 4
```

### Parameters

| Parameter | Type / accepted values | Default | Description |
| --- | --- | --- | --- |
| `--model` | String | `TEST` | IQ-TREE substitution model/model-selection specification, passed as -m. |
| `--uf_bootstrap_replicates` | Integer ≥ 1000 | `1000` | Ultrafast bootstrap replicates, passed to IQ-TREE as -B. |
| `--sh_alrt_replicates` | Integer ≥ 1000 | `1000` | SH-aLRT replicates, passed to IQ-TREE as --alrt. |
| `--uf_support_threshold` | Integer, 0–100 | `90` | Minimum UFBoot support for a trusted cluster. |
| `--sh_support_threshold` | Integer, 0–100 | `75` | Minimum SH-aLRT support for a trusted cluster. |
| `--branch_cut_min` | Number ≥ 0 | `0` | Minimum incoming branch-length threshold in the sweep. |
| `--branch_cut_max` | Number ≥ minimum | `0.5` | Maximum incoming branch-length threshold in the sweep. |
| `--branch_cut_step` | Number > 0 | `0.01` | Increment between incoming branch-length thresholds. |
| `--clone_cut_mode` | auto / manual | `auto` | How to choose the final incoming branch-length threshold. 'auto' selects a stable, trusted, parsimonious solution; 'manual' uses --clone_cut_threshold. |
| `--clone_cut_threshold` | Number ≥ 0 | `None (unset)` | Incoming parent-to-child branch-length threshold; required in manual mode, applied exactly even between grid points. |
| `--min_trusted_ratio` | Number in [0, 1] | `0.95` | Minimum fraction of clusters marked trusted at an automatically eligible threshold. |
| `--min_partition_stability` | Number in [0, 1] | `0.95` | Minimum adjacent-threshold Adjusted Rand Index (ARI); uses the smaller of the previous/next ARIs when both exist. |
| `--stability_window` | Integer ≥ 2 | `3` | Minimum consecutive eligible sweep thresholds forming a stable region. |
| `--min_tips` | Integer ≥ 1 | `50` | Minimum tips in a trusted cluster to export it as a clone. |
| `--threads` | Integer | `1` | IQ-TREE -T value; positive values set threads, 0 or negative values select AUTO. |
| `--root_method` | midpoint / outgroup / none | `midpoint` | Root the IQ-TREE result by midpoint or named outgroup; none preserves an already rooted result. |
| `--outgroup` | One or more tip names | `None (unset)` | Space-separated outgroup tip labels; takes precedence over root_method. Required for outgroup rooting. |
| `fasta_path` | File or directory | `Required` | FASTA alignment by default; bundle/Monopogen directory with --input_format standard/monopogen. |
| `output_directory` | Directory | `Required` | Directory for this stage’s outputs. |
| `prefix` | String | `Required` | Sample/lineage identifier used in output filenames. |
| `-h`, `--help` | Flag | Exit only when supplied | Display this stage’s usage and options, then exit. |

### Outputs

| File/location | Content |
| --- | --- |
| `<prefix>_iqtree2.sh` | Runnable IQ-TREE command |
| `<fasta_path>.treefile`, `.iqtree`, `.log`, and other IQ-TREE files | Inferred tree, inference report, logs, and support-analysis products beside the input FASTA |
| `Phylo/<prefix>.rooting_info.tsv` | Rooting method and outgroup metadata |
| `Phylo/branch_length_cut_analysis.tsv` | Swept thresholds, cluster counts, trusted fraction, adjacent ARIs, and selection flags |
| `Phylo/<prefix>.clone_cut_selection.tsv` | Selected incoming branch-length threshold and selection settings |
| `Phylo/*.pdf` | Rooted trees, branch/support distributions, threshold analysis, and clone visualizations |
| `Clone/Clone_1/Clone_1.nex`, `Clone/Clone_1/Clone_1.nwk`, … | NEXUS/Newick trees for exported clones |
| `Clone/<prefix>.clone_assignment.tsv` | Cell-to-clone assignments and membership status |

## Ancestral state estimation

Estimate ancestral cell states on each clone tree using independent BayesTraits MultiState MCMC chains. The inferred state at each internal node is the state with the highest posterior mean across parsed chains. Posterior quantiles and a confidence flag accompany the call. Convergence QC uses rank-normalized split/folded R-hat, bulk ESS, and tail ESS, while retaining coda ESS and Gelman–Rubin PSRF for comparison. The defaults require R-hat < 1.01 and both modern ESS values ≥ 400. MCSE of the mean is also reported. These diagnostics require at least two chains; the default is three.

### Usage

```text
python3 SPICE.py ancestry tree states output_directory prefix [options]
```

```bash
python3 SPICE.py ancestry \
  results/sample/Clone/Clone_1/Clone_1.nex /data/cell_states.tsv \
  results/clone1/ clone1 \
  --mcmc_chains 3 --threads 3 --min_ancestral_probability 0.90
```

Required inputs are a rooted tree and its cell-state table. Run once per clone in a separate output directory; BayesTraits locations can be set as described under installation.

### Parameters

| Parameter | Type / accepted values | Default | Description |
| --- | --- | --- | --- |
| `tree` | Newick/NEXUS file | `Required` | Rooted lineage tree in Newick or NEXUS format |
| `states` | TSV file | `Required` | TSV containing cell_id and state columns |
| `output_directory` | Directory | `Required` | Directory for this stage’s outputs. |
| `prefix` | String | `Required` | Sample/lineage identifier used in output filenames. |
| `--bayestraits_bin` | Executable path/name | `None (unset)` | BayesTraits executable; resolved from this option, BAYESTRAITS_BIN, then recognized names on PATH. |
| `--mcmc_chains` | Integer ≥ 2 | `3` | Number of independent BayesTraits MCMC chains. |
| `--iterations` | Integer > burnin | `1000000` | Total MCMC iterations per ancestry chain. |
| `--burnin` | Integer ≥ 0, < iterations | `200000` | Burn-in iterations per ancestry chain. |
| `--log_sample_period` | Integer ≥ 1 | `1000` | Sample every this many MCMC iterations. |
| `--stepping_stones` | Integer ≥ 0 | `10` | Number of stepping stones; 0 disables stepping-stone sampling. |
| `--stone_iterations` | Integer ≥ 1 | `1000` | Iterations per stepping stone when enabled. |
| `--effective_size_threshold` | Number | `200` | ESS ≥ this value sets ESS_pass in ancestry diagnostics; used in internal permutation diagnostics for plasticity. |
| `--psrf_threshold` | Number | `1.1` | PSRF point estimate ≤ this value sets PSRF_pass with at least two chains; also used internally for permutations. |
| `--min_ancestral_probability` | Number in [0, 1] | `0.9` | Minimum posterior mean probability for a confident internal-node state. Plasticity recalculates confidence at its requested cutoff while retaining convergence QC requirements. |
| `--rhat_threshold` | Finite number > 1 | `1.01` | Modern R-hat must be strictly below this threshold. |
| `--bulk_ess_threshold` | Finite number > 0 | `400` | Minimum pooled bulk ESS across chains. |
| `--tail_ess_threshold` | Finite number > 0 | `400` | Minimum pooled tail ESS across chains. |
| `--max_retries` | Integer ≥ 0 | `2` | Maximum fresh attempts after the initial run fails QC. |
| `--retry_multiplier` | Finite number > 1 | `2` | Multiply iterations and burn-in at each retry; sample period stays fixed. |
| `--mcmc_seed` | Integer 1–2147483646 | `12345` | Base BayesTraits random seed; distinct deterministic seeds are assigned to chains, retries, and permutation replicates. |
| `--hyperprior` | Quoted string | `exp 0 10` | BayesTraits HyperPriorAll specification, e.g. "exp 0 10". |
| `--threads` | Integer ≥ 1 | `3` | Maximum simultaneous MCMC chains, capped by mcmc_chains. |
| `-h`, `--help` | Flag | Exit only when supplied | Display this stage’s usage and options, then exit. |

### Outputs

| File/location | Content |
| --- | --- |
| `<prefix>.ancestral_states.tsv` | `node_id`, `node_number`, `inferred_state`, `inferred_state_code`, `posterior_probability`, `posterior_q025`, `posterior_q975`, `confident`, `node_qc_pass`, `run_qc_pass`, `usable`, `tree_md5`, `states_md5`, `qc_policy`, `spice_version`, QC thresholds, hyperprior, and per-state `posterior_state_<code>` means |
| `<prefix>.mcmc_diagnostics.tsv` | `parameter`, `ESS`, `PSRF_point`, `PSRF_upper`, `ESS_pass`, `PSRF_pass`, `Rhat`, `ESS_bulk`, `ESS_tail`, `MCSE_mean`, `diagnostic_status`, `qc_pass`, parameter scope/node, and draw counts |
| `<prefix>.state_mapping.tsv` | State labels and BayesTraits state codes |
| `<prefix>.bayestraits_traits.tsv` | Headerless cell/state-code input supplied to BayesTraits |
| `<prefix>.ancestry_run_info.tsv` | Input paths, executable, MCMC settings, and confidence/QC thresholds |
| `<prefix>.qc_attempts.tsv` | Attempt settings, seed base, status, failed-node count, and execution errors |
| `<prefix>.qc_status.tsv` | Final QC decision and thresholds |
| `<prefix>.attempts/attempt_01/MCMC1/`, … | Command files, AddNode definitions, BayesTraits logs, stdout, and stderr per chain |
| `<prefix>_ASE.txt` | Additional export with `node`, `anc_state`, `anc_prob`, and `confident` |

Pass `.ancestral_states.tsv` to plasticity. Join `.state_mapping.tsv` to map the unique posterior state-code columns to original labels. The input requires the current `qc_policy`; before permutations, modern QC thresholds and the hyperprior must match the observed ancestry. A different posterior cutoff is supported and recalculated. Results created before policy metadata was introduced must be regenerated. `posterior_probability` is the selected state’s posterior mean, with 2.5% and 97.5% quantiles of its sampled probabilities. The `confident` flag uses `min_ancestral_probability`; `usable` additionally requires model and node QC to pass. Model QC covers likelihood and rate parameters. Node QC covers all sampled state probabilities for that node. State probabilities that have exactly the same finite value in [0,1] across all retained draws of every chain are marked `constant_consistent` and are eligible for use when model QC and the remaining node probabilities pass. Their R-hat/ESS diagnostics remain unavailable; this exception does not establish convergence or biological certainty. Different chain constants, partially constant chains, and constant model parameters do not qualify. Other unavailable diagnostics remain failures. `constant_probability_terms` and `node_qc_status` identify affected nodes in the ancestry output.

A QC failure triggers a fresh set of all chains, with longer iterations and burn-in, up to the retry budget. With defaults, attempts use 1, 2, and 4 million iterations per chain. Only the final attempt supplies downstream posteriors; samples from different attempts are not pooled. Model QC failure blocks downstream analysis. When model QC passes but some nodes still fail after retries, those nodes remain uncertain. Process or malformed-log errors stop immediately and retain their logs.

Use a fresh output directory or prefix for every run. All attempts and command files are retained. Fixed `--mcmc_seed` values make chain seed assignment independent of `--threads`; use a different seed to assess Monte Carlo stability. The seed for attempt a, chain c is the base plus `(a−1) × chains + (c−1)`, wrapped to the supported positive integer range.

## Cellular plasticity

Classify each parent-to-child edge using `state_order.tsv`:

| Child order relative to parent | Transition |
| --- | --- |
| Equal | Self-renewal |
| Higher | Differentiation |
| Lower | Dedifferentiation |
| Endpoint state/order unavailable or below confidence criteria | Uncertain |

Observed tips have probability 1. Internal endpoints must pass node QC and meet the plasticity posterior-probability cutoff. The cutoff is recalculated from stored probabilities, allowing 0.7, 0.8, and 0.9 sensitivity analyses from the same ancestry output. Model QC and matching tree/cell-state fingerprints are required. Each informative edge has equal weight:

```text
cellular_plasticity (%) = 100 × dedifferentiation /
                         (self-renewal + differentiation + dedifferentiation)
```

Uncertain edges are excluded from the denominator; the score is `NA` when no informative edges remain.

### Usage

```text
python3 SPICE.py plasticity tree states ancestral_states state_order output_directory prefix [options]
```

Calculate observed plasticity:

```bash
python3 SPICE.py plasticity \
  results/sample/Clone/Clone_1/Clone_1.nex /data/cell_states.tsv \
  results/clone1/clone1.ancestral_states.tsv /data/state_order.tsv \
  results/clone1/ clone1 --perm_replicates 0
```

Run the permutation test:

```bash
python3 SPICE.py plasticity \
  results/sample/Clone/Clone_1/Clone_1.nex /data/cell_states.tsv \
  results/clone1/clone1.ancestral_states.tsv /data/state_order.tsv \
  results/clone1/ clone1 --perm_replicates 1000 --threads 4 --seed 12345
```

Each replicate shuffles tip states without replacement on the fixed tree, preserves their frequencies, re-estimates ancestry, and recalculates plasticity. `--threads` parallelizes replicates. `--seed` controls the tip-state shuffles. The empirical p-value is `(b + 1)/(n + 1)`, where `n` is the requested replicate count. A p-value is reported only when every requested replicate completes QC and yields a finite score; otherwise the test is marked `incomplete`, significance fields are `NA`, and the command exits unsuccessfully while preserving results. For `greater`, `b` counts null scores ≥ observed; `less` uses ≤ observed; `two-sided` compares absolute distances from the null median. The test output reports requested/successful replicate counts and `test_status`. Each replicate uses the same convergence and confidence rules as the observed analysis. Retries preserve the same shuffled labels. The BayesTraits seed base for replicate i is `mcmc_seed + (i−1) × perm_chains × (max_retries+1)`, wrapped to the positive supported range; within each replicate, attempt/chain offsets follow ancestry.

### Parameters

| Parameter | Type / accepted values | Default | Description |
| --- | --- | --- | --- |
| `tree` | Newick/NEXUS file | `Required` | Rooted lineage tree in Newick or NEXUS format |
| `states` | TSV file | `Required` | TSV containing cell_id and state columns |
| `ancestral_states` | TSV file | `Required` | Ancestral-state TSV produced by SPICE ancestry |
| `state_order` | TSV file | `Required` | TSV containing state and order columns |
| `output_directory` | Directory | `Required` | Directory for this stage’s outputs. |
| `prefix` | String | `Required` | Sample/lineage identifier used in output filenames. |
| `--perm_replicates` | Integer ≥ 0 | `1000` | Number of tip-state shuffles with ancestry re-estimation; 0 calculates observed plasticity only. |
| `--sig_direction` | greater / less / two-sided | `greater` | Alternative hypothesis for empirical permutation significance |
| `--bayestraits_bin` | Executable path/name | `None (unset)` | BayesTraits executable; resolved from this option, BAYESTRAITS_BIN, then recognized names on PATH. |
| `--perm_chains` | Integer ≥ 2 when permutations enabled | `3` | Number of MCMC chains per permutation, run sequentially within each replicate. |
| `--perm_iterations` | Integer > perm_burnin | `1000000` | Total MCMC iterations per permutation chain. |
| `--perm_burnin` | Integer ≥ 0, < perm_iterations | `200000` | Burn-in iterations per permutation chain. |
| `--perm_sample_period` | Integer ≥ 1 | `1000` | Sampling interval for permutation MCMC. |
| `--stepping_stones` | Integer ≥ 0 | `0` | Number of stepping stones; 0 disables stepping-stone sampling. |
| `--stone_iterations` | Integer ≥ 1 | `1000` | Iterations per stepping stone when enabled. |
| `--effective_size_threshold` | Number | `200` | ESS ≥ this value sets ESS_pass in ancestry diagnostics; used in internal permutation diagnostics for plasticity. |
| `--psrf_threshold` | Number | `1.1` | PSRF point estimate ≤ this value sets PSRF_pass with at least two chains; also used internally for permutations. |
| `--min_ancestral_probability` | Number in [0, 1] | `0.9` | Minimum posterior mean probability for a confident internal-node state. Plasticity recalculates confidence at its requested cutoff while retaining convergence QC requirements. |
| `--rhat_threshold` | Finite number > 1 | `1.01` | Modern R-hat must be strictly below this threshold. |
| `--bulk_ess_threshold` | Finite number > 0 | `400` | Minimum pooled bulk ESS across chains. |
| `--tail_ess_threshold` | Finite number > 0 | `400` | Minimum pooled tail ESS across chains. |
| `--max_retries` | Integer ≥ 0 | `2` | Maximum fresh attempts after the initial run fails QC. |
| `--retry_multiplier` | Finite number > 1 | `2` | Multiply iterations and burn-in at each retry; sample period stays fixed. |
| `--mcmc_seed` | Integer 1–2147483646 | `12345` | Base BayesTraits random seed; distinct deterministic seeds are assigned to chains, retries, and permutation replicates. |
| `--hyperprior` | Quoted string | `exp 0 10` | BayesTraits HyperPriorAll specification, e.g. "exp 0 10". |
| `--seed` | Nonnegative integer; seed + replicate count ≤ 2147483646 | `12345` | Tip-state shuffling seed: replicate i uses seed + i. Applies to shuffling only. |
| `--threads` | Integer ≥ 1 | `1` | Maximum simultaneous permutation replicates, capped by perm_replicates. |
| `-h`, `--help` | Flag | Exit only when supplied | Display this stage’s usage and options, then exit. |

### Outputs

| File | Content |
| --- | --- |
| `<prefix>.transitions.tsv` | `edge_id`, `parent_node`, `child_node`, endpoint states/probabilities, and `transition` |
| `<prefix>.plasticity.tsv` | Transition counts, informative/total edges, class fractions, and plasticity percentage |
| `<prefix>.permutation_plasticity.tsv` | Replicate number, plasticity, and status |
| `<prefix>.plasticity_test.tsv` | Observed score, null mean/SD/median, empirical p-value, z-score, requested/successful counts, and alternative |
| `<prefix>.plasticity_run_info.tsv` | Inputs and analysis settings |
| `<prefix>_ASE_Summary.txt` | Transition export with parent/child labels and states |
| `<prefix>_cellular_plasticity.tsv` | Additional clone-summary export |

With `--perm_replicates 0`, the permutation table contains headers only and significance fields are `NA`. Per-replicate MCMC commands, logs, diagnostics, and attempts are retained under `<prefix>.permutations/perm_0001/`, etc. Use a fresh output directory or prefix for each plasticity run.

## External lineage example

For a prepared lineage derived from static barcodes or another external source, use its rooted clone tree with the same state formats:

```bash
python3 SPICE.py ancestry \
  /data/external/clone_A.nwk /data/cell_states.tsv \
  results/clone_A/ clone_A --threads 3

python3 SPICE.py plasticity \
  /data/external/clone_A.nwk /data/cell_states.tsv \
  results/clone_A/clone_A.ancestral_states.tsv /data/state_order.tsv \
  results/clone_A/ clone_A --perm_replicates 1000 --threads 4 --seed 12345
```

Repeat for each known clone/tree, retaining clone membership in `clone_assignment.tsv` and using a distinct results directory for each lineage.

## Summarize clone tests

Create a tab-separated manifest for the full family of clones to be tested:

```text
clone_id	plasticity_test
Clone1	results/Clone1/Clone1.plasticity_test.tsv
Clone2	results/Clone2/Clone2.plasticity_test.tsv
```

Paths are relative to the manifest. Supply one distinct result per clone and the
same test alternative throughout the family.

```bash
python SPICE.py summarize clone_tests.tsv clone_summary.tsv --alpha 0.05
```

| Parameter | Type / accepted values | Default | Meaning |
|---|---|---|---|
| `manifest` | TSV path | Required | Clone IDs and result-file paths. |
| `output` | New TSV path | Required | Combined result table; existing files are not overwritten. |
| `--alpha` | Finite number strictly between 0 and 1 | `0.05` | Threshold for BH-adjusted p-values. |
| `-h`, `--help` | Flag | Exit only when supplied | Display usage. |

The output contains clone ID, result path/status, observed score, empirical p-value,
alternative, BH `q_value`, `significant`, and `n_tests_planned`. Declare the family
before selecting significant clones. Missing, failed and unrequested tests remain
in the planned family, using p=1 internally for correction; their displayed p/q
values are `NA` and they cannot be significant. An adjusted p-value concerns the
specified permutation null and does not by itself establish biological plasticity.

## Additional analysis scripts

The repository also includes standalone read-count and BayesTraits analysis scripts. Install their additional packages when using them:

| Scripts | Additional directly loaded packages |
| --- | --- |
| `modules/cell_read_counter.py` | Python: `pysam`, `tqdm` |
| `scripts/BayesTraits.R`, `scripts/RunBayesTraits.R`, `scripts/AncestralStatesMCMC.R` | R: `posterior`, `tidybayes`, `tidytree`, `tidyverse`, `patchwork`, `dplyr`, `tidyr`, plus the `ape`, `coda`, `janitor`, `posterior`, `ggtree`, and `ggplot2` packages listed above; `parallel` is included with R |

`tidyverse` also supplies `readr` and its other component packages used in these workflows.

```bash
python3 -m pip install pysam tqdm
```

```r
install.packages(c("posterior", "tidybayes", "tidytree", "tidyverse", "patchwork", "dplyr", "tidyr"))
```

To count BAM reads carrying selected `CB` barcode tags, provide a headerless barcode list, one barcode per line:

```bash
python3 modules/cell_read_counter.py \
  /data/sample.bam /data/barcodes.txt results/read_counts/ sample
```

The output `sample.cell_read_counts.tsv` contains `cell` and `count` columns, sorted by count.

The legacy BayesTraits runner resolves `BAYESTRAITS_BIN` or a recognized executable
on PATH. Its extra packages can be installed with `remotes::install_github("rgriff23/btw")`
after installing `remotes`. Use the main `SPICE.py` commands for current QC and output formats.

## License and contact

SPICE is distributed under the [GNU General Public License v3.0](LICENSE).

- Repository and issues: [Diaz Lab SPICE](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE)
- Contact: Bohyeon Yu, [bohyeon.yu@ucsf.edu](mailto:bohyeon.yu@ucsf.edu)

Trees used by ancestry must provide finite, nonnegative lengths for every edge; zero lengths are retained as supplied. `state_order.tsv` requires finite numeric orders.

## Input-route regression tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

The input tests create small real chromosome RDS fixtures using base R, run the
existing R count filter for imported and direct bundles, and compare retained
matrices/FASTA against each other and the legacy merge/filter path. Tests cover
site multiplicity, conflicting duplicates, reordered cells, schema errors,
missing quality metadata, empty results and CLI parameter forwarding. External
IQ-TREE/clone computation is mocked in the forwarding test; this test does not
claim numerical tree-inference reproducibility across IQ-TREE runs or versions.
RDS/filter tests require R and the filter packages listed above.
