# Tutorial

[Home](Home.md) · [Installation](Installation.md) · [Galaxy](Galaxy.md)

These exercises use synthetic fixtures to inspect software behavior. They are not biological benchmarks. Run commands from the repository root after installing SPICE and the relevant dependencies. Choose a fresh output directory when repeating a run.

## Small command-line filtering exercise

The committed [standard example](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/tree/main/examples/standard) contains `matrix.tsv`, `variants.tsv` and `cells.tsv`.

```bash
spice filter examples/standard results/example example --input_format standard \
  --min_alt_cells_per_snv 2 --min_snvs_per_cell 1
```

The reduced cutoffs are specific to this tiny fixture; the production defaults are five ALT-supporting cells per SNV and five retained SNVs per cell. No Monopogen quality columns are present, so automatic metadata QC leaves the shared count filter in effect.

Inspect `results/example/example.SNV_mat.filter.csv` and `results/example/example.SNV_mat.filter.fasta`. Expected retained data are **three variants and three cells**, with FASTA sequences:

| Cell | Sequence |
| --- | --- |
| `Ref` | `GGC` |
| `cell-2` | `RRT` |
| `cell_3` | `AAT` |

The first two distinct sites share count patterns and both remain. The fourth site and cell fail the cutoffs. Also inspect `example.runtime.json`; use the final CSV/FASTA for retained dimensions, because the selection audit tables precede count filtering. This fixture exercises filtering only and is too small to validate biological tree inference.

## Full staged Galaxy exercise

Use the existing [Galaxy tutorial draft](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/galaxy/training/tutorial.md) with its [test job settings](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/galaxy/workflows/spice_lineage_analysis-job.yml). It is repository-local and has not been submitted to or endorsed by GTN.

A prepared server needs Galaxy 25.0+, the five staged SPICE tools, IUC IQ-TREE revision `e727e82945af` (`2.4.0+galaxy2`) and administrator-supplied BayesTraits. Upload the five files from [the workflow fixture](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/tree/main/galaxy/tools/test-data/workflow): `matrix.tsv`, `variants.tsv`, `cells.tsv`, `states.tsv` and `state_order.tsv`.

Follow Filter → IUC IQ-TREE → Clones → mapped Ancestry → paired mapped Plasticity → Summarize, or import the committed workflow and supply the explicit test-job settings. Keep original clone-tree and ancestry collections paired by order and `Clone_N` identifiers. Supply the same states throughout.

### Test-only settings

| Control | Synthetic exercise |
| --- | --- |
| Filter count cutoffs | 1 supporting cell per SNV; 1 retained SNV per cell |
| IQ-TREE | DNA, JC model, BIC criterion, outgroup `Ref`, seed 12345, one thread; 1,000 SH-aLRT and 1,000 UFBoot replicates |
| Clone selection | Manual cutoff 0.10; minimum 2 tips; outgroup `Ref` |
| Ancestry/permutation chains | 2 |
| Iterations / burn-in / sampling period | 50,000 / 10,000 / 100 |
| Observed ancestry stepping stones | 0 |
| Permutations | 3 |
| Modern QC | R-hat < 1.2; bulk and tail ESS ≥ 20 |
| Posterior cutoff | 0.5 |

**These settings are test-only.** The tiny clone fixture has no stable automatic region under the production criteria. The manual cutoff and relaxed QC exercise execution and collection identity; they are not recommendations for real study analyses. Workflow/tool defaults remain the production defaults documented in [Ancestry and plasticity](Ancestry-and-Plasticity.md) and [Clone inference](Clone-Inference.md).

Inspect ancestry probabilities, state mapping, diagnostics, QC attempts and runtime JSON for every clone. Plasticity needs valid matching ancestry and every requested permutation to succeed. Check successful/requested counts, test status and clone IDs before reading P/q values. Three permutations cannot support a claim of adequate statistical power.

For a real study, prepare appropriate inputs, justify rooting/clone/state-order choices, use production settings as a starting point, and assess convergence and scientific suitability. Read [Scientific assumptions and limitations](Scientific-Assumptions-and-Limitations.md) before interpreting results.
