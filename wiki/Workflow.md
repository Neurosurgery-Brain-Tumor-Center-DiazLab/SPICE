# Workflow

[Home](Home.md) · [Next: Clone inference](Clone-Inference.md)

Choose the entry point that matches your data. The commands below are templates for study data, using production defaults unless a value is explicitly shown. Replace paths and prefixes; use fresh output directories for each analysis and each clone.

## From read counts to clones

A direct standard bundle requires no Monopogen installation:

```bash
spice filter inputs/sample results/sample-filter sample --input_format standard
spice phylogeny results/sample-filter/sample.SNV_mat.filter.fasta results/sample-tree sample
```

Alternatively, combine filtering, IQ-TREE inference and clone classification:

```bash
spice phylogeny inputs/sample results/sample sample --input_format standard
```

For prepared Monopogen results, import explicitly and then follow the standard route:

```bash
spice import-monopogen /data/monopogen inputs sample
```

The convenience form `spice filter /data/monopogen results/sample-filter sample` defaults to Monopogen input. `phylogeny` defaults to FASTA; explicitly choose `--input_format standard` or `--input_format monopogen` when supplying a directory.

### Filtering order

SPICE applies metadata QC when enabled, then upstream cell eligibility/selection, then the variant ALT-support count cutoff, then the retained-SNV cutoff per cell. A supporting cell has ALT count > 0. This is one pass: removing cells does not trigger another round of variant filtering.

| Setting | Default |
| --- | --- |
| `--variant_qc` | `auto` |
| `--depth_ref`, `--depth_alt` | 5 each; metadata minima |
| `--svm_pos_score` | 0.1 minimum |
| `--ldrefine_merged_score` | 0.25 minimum |
| `--baf_alt` | 0.5 maximum |
| `--min_alt_cells_per_snv` | 5 |
| `--min_snvs_per_cell` | 5 |
| `--threads` | 1 |

Metadata QC also requires `Depth_total >= depth_ref + depth_alt`. Input without quality fields still receives count filtering under `auto`. If no variants or cells survive, the command fails instead of writing an empty FASTA. Cell and variant selection audits precede count filtering; inspect the final filtered matrix/FASTA for retained dimensions.

## From an existing supported tree

```bash
spice clones --tree /data/supported.treefile \
  --output_directory results/sample-clones --prefix sample
```

This performs rooting, support filtering, cut selection, assignments and clone export without executing IQ-TREE. See [Clone inference](Clone-Inference.md) before choosing rooting or cut settings. External lineage trees that do not have IQ-TREE support semantics should enter at ancestry after appropriate independent preparation.

## Analyze one rooted clone

Suppose the clone tree is `results/sample-tree/Clone/Clone_1/Clone_1.nwk` and the sample-wide annotations are in `inputs/cell_states.tsv`:

```bash
spice ancestry results/sample-tree/Clone/Clone_1/Clone_1.nwk \
  inputs/cell_states.tsv results/Clone_1/ancestry Clone_1
spice plasticity results/sample-tree/Clone/Clone_1/Clone_1.nwk \
  inputs/cell_states.tsv results/Clone_1/ancestry/Clone_1.ancestral_states.tsv \
  inputs/state_order.tsv results/Clone_1/plasticity Clone_1
```

The same commands accept a prepared external rooted lineage/clone tree in place of the exported tree. Retain the tree and annotations unchanged between stages. Plasticity's default 1,000 permutations rerun ancestry and can be computationally substantial. See [Ancestry and plasticity](Ancestry-and-Plasticity.md) for QC, production settings and observed-only mode.

## Summarize the planned clone family

Create `results/clone_tests.tsv` with one row per planned clone, including missing or unsuccessful tests. Paths are relative to the manifest:

```tsv
clone_id	plasticity_test
Clone_1	Clone_1/plasticity/Clone_1.plasticity_test.tsv
Clone_2	Clone_2/plasticity/Clone_2.plasticity_test.tsv
```

```bash
spice summarize results/clone_tests.tsv results/clone_summary.tsv --alpha 0.05
```

All supplied tests must use the same alternative. Missing or unsuccessful tests remain in the planned correction family with an internal P-value of 1; their displayed P/q values remain `NA`. Only valid successful tests receive q-values and significance calls. The output must be a new file. Retain the manifest and examine [outputs and provenance](Outputs-and-Provenance.md).
