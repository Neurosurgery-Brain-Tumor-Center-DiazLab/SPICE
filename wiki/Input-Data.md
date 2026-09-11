# Input data

[Home](Home.md) · [Next: Workflow](Workflow.md)

## Standard count bundle

A bundle directory contains exactly named **`matrix.tsv`, `variants.tsv`, and `cells.tsv`** files. Use UTF-8, tabs and headers. Additional files are ignored. The matrix is **cells × variants**: cells in rows and variants in columns.

`matrix.tsv`:

```tsv
cell_id	chr1:10:A:G	chr1:20:C:T
cell_001	3/0	1/2
cell_002	0/4	0/0
```

Each entry is **REF_count/ALT_count**, not a genotype. Counts are nonnegative integers without leading zeros, with a combined maximum of 2,147,483,647. `0/0` means no coverage and becomes `N` in FASTA. Empty values, `NA`, `./.`, negative or fractional counts are rejected. REF-only/ALT-only support maps to the respective nucleotide; mixed support maps to the existing IUPAC ambiguity code. SPICE does not infer a new allele-fraction genotype call or impute missing counts.

The first header must be `cell_id`. Cell IDs must be unique and use only letters, digits, `_`, `.` or `-`; `Variant_ID` is reserved. Variant IDs must be unique `chrom:pos:REF:ALT` identifiers: positive 1-based positions, distinct uppercase A/C/G/T alleles, and chromosome names without colons or whitespace. Distinct sites with identical count patterns remain separate.

`variants.tsv`:

```tsv
variant_id	chrom	pos	ref	alt
chr1:10:A:G	chr1	10	A	G
chr1:20:C:T	chr1	20	C	T
```

All five columns are required. Every matrix variant must occur exactly once with matching coordinates and alleles; extra or missing metadata variants are errors. Matrix column order defines site order. Metadata row order need not match; additional annotation columns are allowed.

`cells.tsv`:

```tsv
cell_id	pass_filter
cell_001	true
cell_002	true
```

Every matrix cell must occur exactly once, with no extras. Additional metadata columns are allowed. The optional `pass_filter` column accepts exactly `true` or `false` and defaults to `true` when absent. False cells remain in the input bundle but are excluded before count filtering.

### Optional variant quality metadata

Include all six fields or none: `Depth_total`, `Depth_ref`, `Depth_alt`, `SVM_pos_score`, `LDrefine_merged_score`, `BAF_alt`. Values must be finite numbers; empty/`NA` quality values become zero during metadata QC. A partial schema is rejected even when metadata QC is disabled. Do not relabel unrelated caller scores as Monopogen scores without a scientific justification.

`--variant_qc auto` applies metadata QC when all six fields exist; `metadata` requires them; `none` skips metadata QC. Count filtering still applies. Changing quality thresholds while metadata QC is disabled or absent is an error. See [Workflow](Workflow.md) for filtering order and defaults.

## Optional Monopogen import

For each available `chr*.SNV_mat.RDS`, supply matching `chr*.cell_snv.cellID.csv` and `chr*.cell_snv.cellID.filter.csv` files containing `cell`, plus `chr*.putativeSNVs.csv`. Putative metadata requires `chr`, `pos`, `Ref_allele`, `Alt_allele` and the six quality fields above. Prepared RDS matrices use variants in rows, cell barcodes in columns and REF/ALT counts. Raw `.mat.gz` and `snvID.csv` files are unnecessary when these RDS matrices exist.

Partial chromosome sets and chrX/chrY are supported; every discovered matrix needs its companion files. Chromosome cell sets must match, although differing orders are aligned by barcode. Duplicate variant IDs are collapsed only when counts and metadata agree; conflicts fail. The importer preserves extra metadata and marks cell eligibility from the intersection of chromosome filter lists.

```bash
spice import-monopogen /data/monopogen inputs sample
```

This writes `inputs/sample/{matrix,variants,cells}.tsv` without SPICE quality/count filtering. It refuses to overwrite bundle files. The Monopogen convenience route can reuse its saved bundle only after verifying that re-imported input agrees; changed input requires a new output directory/prefix.

## Selected cells

The optional barcode file contains exactly one `cell_barcodes` header:

```tsv
cell_barcodes
cell_001
cell_002
```

Duplicate or unknown selected IDs fail. Selected cells with `pass_filter=false` remain excluded. Selection-file order defines cell order when supplied; otherwise matrix row order is retained.

## Cell-state annotations

Use `cell_id` and `state` as the first two tab-separated columns:

```tsv
cell_id	state
cell_001	Progenitor
cell_002	Differentiated
```

Cell IDs must be unique and cover every tip in the supplied tree. Extra cells in a sample-wide table are ignored for that tree. A headerless two-column table is also accepted. State labels are deterministically encoded for BayesTraits; retain the resulting `.state_mapping.tsv`.

## Investigator-supplied state order

```tsv
state	order
Progenitor	1
Intermediate	2
Differentiated	3
```

States must be unique and order values finite and numeric, covering every observed state. Higher order means more differentiated. Equal order defines self-renewal even between distinct labels. This table is a biological assumption supplied by the investigator, separate from BayesTraits numeric state codes.

## Trees and clone membership

`clones` accepts a supported IQ-TREE **Newick** tree with SH-aLRT/UFBoot labels. It is not a generic tree-format converter. `ancestry` and `plasticity` accept exactly one rooted Newick tree or a NEXUS tree with `.nex`/`.nexus` extension. Each edge requires a finite, nonnegative branch length; use unique, whitespace-free tip labels suitable for BayesTraits.

Keep the exact same tree file and matching state annotations for ancestry and plasticity. SPICE checks fingerprints; internal `T1`, `T2`, … identifiers refer to the original parsed tree. Original IQ-TREE support labels are preserved; only a temporary BayesTraits NEXUS copy omits them.

The SNV route exports `Clone/<prefix>.clone_assignment.tsv` with `cell_id`, `clone_id`, `clone_status` and `in_trusted_cluster`. Only trusted, size-qualified clones receive IDs. For external lineages, retain your known clone membership separately and provide each prepared rooted clone tree directly to ancestry.
