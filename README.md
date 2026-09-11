# SPICE: Single-cell Plasticity Inference and Clonal Evolution

<img src="SPICE.png" alt="SPICE" width="300">

SPICE combines somatic SNV filtering, phylogenetic inference and subclone classification, ancestral cell-state reconstruction, and cellular plasticity analysis. It uses IQ-TREE for single-cell lineage inference and BayesTraits MultiState MCMC to estimate ancestral states. Ordered cell states then define self-renewal, differentiation, and dedifferentiation along lineage edges.

## Workflow

```text
Monopogen results -> import-monopogen --+
                                      +-> standard counts -> filter
User-supplied counts and metadata -----+                       |
                                                              v
                                              IQ-TREE 2 -> clones
                                                              |
Prepared rooted lineage/clone tree ----------------------------+
                                                              v
Cell-state annotations -----------------------------------> ancestry
                                                              |
Investigator-supplied state order -------------------------> plasticity
                                                              |
Planned family of clone tests -----------------------------> summarize
```

Analyze each clone using its own rooted tree and output directory. An existing supported IQ-TREE tree can enter at `clones`; a prepared external lineage enters at `ancestry`.

## Capabilities and commands

- Accept caller-independent cell × variant read counts or import prepared Monopogen outputs.
- Filter variants and cells, infer supported phylogenies, and classify/export clones.
- Reconstruct ancestral cell states with MCMC diagnostics, QC and retained retry evidence.
- Classify lineage edges, quantify dedifferentiation-based plasticity, and test a tip-state permutation null.
- Combine a planned family of clone tests using Benjamini–Hochberg FDR correction.

| Command | Role |
| --- | --- |
| `spice import-monopogen` | Convert Monopogen results to a standard input bundle. |
| `spice filter` | Filter a standard bundle or Monopogen input and write FASTA. |
| `spice phylogeny` | Run IQ-TREE 2 and classify clones; optionally filter counts first. |
| `spice clones` | Classify an existing supported IQ-TREE Newick tree without running IQ-TREE. |
| `spice ancestry` | Infer ancestral states on one supplied rooted tree. |
| `spice plasticity` | Measure edge transitions and optionally run permutation tests. |
| `spice summarize` | Summarize clone tests and adjust for multiple testing. |

<details>
<summary>Ancestry and plasticity option index</summary>

See the [ancestry and plasticity guide](wiki/Ancestry-and-Plasticity.md) for meanings, defaults and QC policy; `spice ancestry --help` and `spice plasticity --help` list accepted arguments.

- Shared controls: `-h`, `--help`, `--bayestraits_bin`, `--threads`, `--hyperprior`, `--min_ancestral_probability`, `--stepping_stones`, `--stone_iterations`.
- Shared diagnostics/retries: `--mcmc_seed`, `--rhat_threshold`, `--bulk_ess_threshold`, `--tail_ess_threshold`, `--max_retries`, `--retry_multiplier`, `--effective_size_threshold`, `--psrf_threshold`.
- Ancestry: `--mcmc_chains`, `--iterations`, `--burnin`, `--log_sample_period`.
- Plasticity: `--perm_replicates`, `--sig_direction`, `--perm_chains`, `--perm_iterations`, `--perm_burnin`, `--perm_sample_period`, `--seed`.

</details>

## Minimal source quick start

Use Python 3.10+ in a Unix-like environment. This installs the Python package and bundled R scripts; analysis also needs the stage-specific R packages and external executables described in [Installation](wiki/Installation.md).

```bash
git clone https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.git
cd SPICE
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
spice --version
spice --help
```

The distribution name is `spice-lineage`, the command is `spice`, and the import namespace is `spice_lineage`. IQ-TREE 2.x (tested 2.4.0) is used for inference. BayesTraits remains externally supplied and is not redistributed.

## Documentation

The **[repository-local wiki](wiki/Home.md)** is the canonical, version-controlled user guide:

- [Installation](wiki/Installation.md), [input data](wiki/Input-Data.md) and [workflow](wiki/Workflow.md)
- [Clone inference](wiki/Clone-Inference.md) and [ancestry and plasticity](wiki/Ancestry-and-Plasticity.md)
- [Galaxy](wiki/Galaxy.md), [tutorial](wiki/Tutorial.md) and [outputs and provenance](wiki/Outputs-and-Provenance.md)
- [Scientific assumptions and limitations](wiki/Scientific-Assumptions-and-Limitations.md) and [citation and release](wiki/Citation-and-Release.md)

Detailed engineering records remain under [docs/](docs/), including [packaging](docs/packaging.md), [distribution staging](docs/distribution.md), [Galaxy administration](docs/galaxy.md) and [integration validation](docs/integration-testing.md). Use each command's `--help` for the complete argument reference.

## Reproducibility and status

Analysis commands record settings, software versions, package source hashes, executable paths/hashes and completion status in runtime JSON. Git revision/status are available only for a verified source checkout; installed packages still retain source hashes. Preserve inputs, tree/state identity, diagnostics and logs alongside results. Synthetic CI fixtures validate software operation, not biological accuracy.

**Version 0.2.0 remains unreleased.** Local Conda/OCI and Galaxy integration are staged; public PyPI, Bioconda, container, Tool Shed and GTN publication is not established. The code is licensed under [GPL-3.0-only](LICENSE). Cite the software version and commit used, following [CITATION.cff](CITATION.cff); authorship, corresponding contact and DOI decisions remain with the human maintainers before release.

Contact: Bohyeon Yu, [bohyeon.yu@ucsf.edu](mailto:bohyeon.yu@ucsf.edu).
