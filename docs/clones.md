# Classify clones from an existing IQ-TREE tree

```bash
spice clones --tree "/path/to/supported tree.treefile" \
  --output_directory /path/to/output --prefix SAMPLE
```

`--tree`, `--output_directory` and `--prefix` are required. Prefix validation is
shared with other SPICE commands: a single filename component without tabs or
newlines. Both the installed `spice` and legacy `python SPICE.py` entry points
use the same implementation.

Input is an existing readable IQ-TREE Newick supported tree. The filename need
not end in `.treefile` or match the output prefix. Node labels retain their
**SH-aLRT/UFBoot** interpretation (for example, `79.2/73`). This is not a generic
format converter; NEXUS is not an input format for `clones`. Rooting/support
failures retain the existing R errors and do not weaken thresholds.

## Options shared with phylogeny

| Option | Default | Existing meaning |
| --- | --- | --- |
| `--uf_support_threshold` | `90` | UFBoot cutoff for a trusted node. |
| `--sh_support_threshold` | `75` | SH-aLRT cutoff for a trusted node. |
| `--branch_cut_min` | `0` | First incoming branch-length threshold in the sweep. |
| `--branch_cut_max` | `0.5` | Last sweep limit. |
| `--branch_cut_step` | `0.01` | Sweep increment. |
| `--clone_cut_mode` | `auto` | `auto` stable/parsimony selection or `manual`. |
| `--clone_cut_threshold` | unset | Required for manual mode; applied exactly, even between grid points. |
| `--min_trusted_ratio` | `0.95` | Minimum trusted-cluster ratio for automatic selection. |
| `--min_partition_stability` | `0.95` | Minimum adjacent-partition Adjusted Rand Index for automatic selection. |
| `--stability_window` | `3` | Minimum consecutive eligible thresholds; must be at least two. |
| `--min_tips` | `50` | Minimum tips in a trusted cluster to export a clone. |
| `--root_method` | `midpoint` | `midpoint`, `outgroup`, or `none`; none requires an already rooted tree. |
| `--outgroup` | unset | One or more tip labels; overrides root_method. Required for outgroup rooting. |

The support parser, rooting precedence, cut sweep, ARI, stable-window definition,
trusted-cluster definition, automatic selection, minimum-tip semantics, clone IDs
and export logic are unchanged. Automatic selection can fail when no eligible
stable region exists, just as in `phylogeny`; inspect the reported error and use
scientifically justified settings. No fallback threshold is silently substituted.

The command needs Rscript and ape, phangorn, phytools, ggplot2, ggtree and ggsci.
It does not require or execute IQ-TREE and exposes no inference options for model,
replicate counts or threads. `phylogeny` keeps its filtering/IQ-TREE flags and
runs IQ-TREE before calling the same `run_clone_classification` Python function.
IQ-TREE still writes beside the actual alignment passed to `-s`.

## Existing outputs

All names and schemas are preserved. Use a clean output directory per analysis;
several sweep/plot names are shared rather than prefixed.

- `Phylo/<prefix>.rooting_info.tsv`: sample, rooting method and outgroups.
- `Phylo/branch_length_cut_analysis.tsv`: complete threshold sweep, cluster and
  export counts, trusted ratio, adjacent ARIs, eligibility and selection flags.
- `Phylo/<prefix>.clone_cut_selection.tsv`: mode, selected threshold and criteria.
- `Clone/<prefix>.clone_assignment.tsv`: `cell_id`, `clone_id`, `clone_status`,
  `in_trusted_cluster`.
- `Clone/Clone_*/Clone_*.nwk` and `.nex`: trusted, size-qualified clone trees.
- `Phylo/<prefix>.rooted_tree.pdf`, `.rooted_tree_with_branch_length.pdf`,
  `.rooted_tree_with_branch_support.pdf`, `.rooted_tree_with_branch_length_support.pdf`.
- `Phylo/branch_length_distributions.pdf`, `UFBoot_distributions.pdf` (when the
  existing support condition applies), `SHaLRT_distributions.pdf`.
- `Phylo/branch_cut_analysis.pdf`, `trusted_clusters.pdf`, `rooted_tree_clustered.pdf`,
  `rooted_tree_clustered_with_brach_length.pdf` (historical spelling retained).
- `<prefix>.runtime.json`: command `clones`, supplied tree path, clone settings,
  installed source hashes, Python/R environment, timestamps and success/failure.
  Existing runtime records are preserved with timestamped filenames.

Runtime `executables` is an inventory of discoverable paths/hashes, not an
executed-tool ledger. An IQ-TREE entry can exist when IQ-TREE happens to be
installed. For `clones`, its `version_probe` is omitted so that even
`IQ-TREE --version` is never launched. Other commands retain existing provenance.

## Internal R interface

Both commands call the packaged `BranchSupportCut.R` using an argument list
without a shell. The output directory retains a trailing separator for existing
R path concatenation. The internal arguments are:

```text
Rscript BranchSupportCut.R
  output_directory sample_id
  uf_support sh_support cut_min cut_max cut_step min_tips
  root_method outgroups_csv_or_NA
  clone_cut_mode clone_cut_threshold_or_NA
  min_trusted_ratio min_partition_stability stability_window
  explicit_tree_file
```

Arguments 1-15 retain their historical positions; **argument 16** is the explicit
absolute tree path. Appending it minimizes the R diff and preserves direct
callers: omitting argument 16 still reads
`<output_directory><sample_id>.fasta.treefile`. Both Python commands always pass
argument 16. The only executable R change chooses that path; the scientific body
and plots are unchanged.

## Orchestration boundary

Option A: `spice phylogeny ...` performs IQ-TREE inference then clone analysis.
Option B: an external or Galaxy IQ-TREE tool produces its supported `.treefile`,
then `spice clones --tree ...` performs clone analysis. Both yield the same
scientific clone outputs for the same tree and options. The real integration
suite verifies that comparison with an arbitrary filename containing spaces.
Phase 4 includes no Galaxy wrappers, Planemo workflows, Tool Shed work, or
package/container publication. Version remains 0.2.0 unreleased.
