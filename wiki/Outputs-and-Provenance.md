# Outputs and provenance

[Home](Home.md) · [Scientific limitations](Scientific-Assumptions-and-Limitations.md)

Use fresh output directories/prefixes per stage and clone. Retain inputs, settings, diagnostics and logs with final tables. An absent or failed result is not a zero-valued biological observation.

## Main analysis products

Paths below are relative to the stage's output directory unless stated otherwise.

| Stage | Main files | Interpretation |
| --- | --- | --- |
| Import | `<prefix>/matrix.tsv`, `variants.tsv`, `cells.tsv` | Validated standard bundle before SPICE filtering. |
| Filter | `<prefix>.SNV_mat.filter.csv`, `<prefix>.SNV_mat.filter.fasta` | Final retained variants/cells and aligned sequences. The legacy CSV has variants in rows, unlike the standard input matrix. |
| Filter audits | `<prefix>.cellID.filter.csv`, `<prefix>.SNVs.filter.csv`, `<prefix>.selected_cells.tsv` | Cell/variant selection before count filtering; not final retained dimensions. |
| Phylogeny | `<prefix>_iqtree2.sh`; IQ-TREE files beside the actual FASTA | Recorded inference command and supported tree/logs. |
| Clone analysis | `Phylo/<prefix>.rooting_info.tsv`, `Phylo/branch_length_cut_analysis.tsv`, `Phylo/<prefix>.clone_cut_selection.tsv` | Rooting decision, threshold sweep and final cut selection. |
| Clone assignment/export | `Clone/<prefix>.clone_assignment.tsv`, `Clone/Clone_N/Clone_N.nwk` and `.nex` | Membership/status for input tips and trusted, size-qualified clone trees. |
| Ancestry | `<prefix>.ancestral_states.tsv`, `<prefix>.state_mapping.tsv` | Node posterior summaries, state codes, QC flags and input fingerprints. |
| Ancestry QC | `<prefix>.mcmc_diagnostics.tsv`, `<prefix>.qc_status.tsv`, `<prefix>.qc_attempts.tsv`, `<prefix>.attempts/` | Model/node diagnostics, final status and separate attempts with chain evidence. |
| Plasticity | `<prefix>.transitions.tsv`, `<prefix>.plasticity.tsv` | Edge classifications, counts, uncertainty and observed plasticity percentage. |
| Permutations | `<prefix>.permutation_plasticity.tsv`, `<prefix>.plasticity_test.tsv`, `<prefix>.permutations/` when requested | Replicate statuses, test summary and retained per-replicate evidence. |
| Run settings | `<prefix>.ancestry_run_info.tsv`, `<prefix>.plasticity_run_info.tsv` | Stage-specific MCMC/QC/order/permutation settings. |
| Summary | User-selected output TSV | Clone status, observed plasticity, empirical P, q-value, significance and planned family size. |

Tree plots and historical compatibility outputs are also retained. The [clone engineering guide](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/clones.md) lists plot filenames. Prefer current `.ancestral_states.tsv` and `.plasticity*.tsv` outputs for downstream work; legacy ancestry tables without current QC/provenance fields cannot bypass validation.

## Check status before interpretation

Ancestry records run and node QC separately from posterior confidence. `usable` requires all relevant conditions. Model-QC failure blocks downstream work; remaining failed node diagnostics yield uncertain incident edges when model QC passes. Review constant-probability status explicitly rather than interpreting unavailable diagnostics as estimated convergence.

Plasticity test status is `pass`, `incomplete` or `not_requested`. A requested test needs all replicates to succeed and a finite observed result. An incomplete test retains evidence but has no valid P-value and exits unsuccessfully. Zero permutations produce `not_requested` with `NA` significance. A run with no informative edges has `NA` plasticity.

Summarize retains missing/unsuccessful planned clones in the correction family. Their P/q values remain `NA`; only passing tests receive adjusted results. Keep the manifest used to define that family.

## Runtime JSON

Analysis commands write `<prefix>.runtime.json`. Summarize writes `<output-filename>.runtime.json` beside its output. Existing runtime files are preserved by using timestamped filenames for subsequent records.

Runtime records include the SPICE version, command/settings, start/finish timestamps and success, platform/Python version, discoverable Python/R package versions, package Python/R source SHA-256 hashes, and external executable paths/hashes. A retained BayesTraits banner is included when available. Unavailable tools or version information are recorded explicitly rather than invented.

Git commit/status are recorded only when the running package belongs to a verified SPICE checkout. An installed wheel outside Git still records package source hashes, with Git fields explicitly unavailable. Save the version and commit used for source installation as part of your study record.

The executable inventory records discovery, not proof of execution. An IQ-TREE entry can appear in a standalone `clones` runtime record if installed, but `clones` never launches it, including for `--version`.

Tree MD5 and reconciled cell-state fingerprints in ancestry bind results to downstream inputs; they complement runtime provenance rather than replace a complete archive of study data. Preserve the exact original tree, state annotations, state-order table, clone manifest and external-tool logs. See [Citation and release](Citation-and-Release.md) for reporting the software used.
