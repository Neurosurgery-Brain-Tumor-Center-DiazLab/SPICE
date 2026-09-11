# Installation

[Home](Home.md) · [Next: Input data](Input-Data.md)

SPICE 0.2.0 is unreleased. Install from the lab source repository, or use a locally built package following the engineering guides. No public PyPI, Bioconda or container installation is claimed here.

## Install from source

Use Python 3.10+ and a Unix-like environment. Distribution validation targets Linux x86_64; other platforms are not claimed to be validated.

```bash
git clone https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.git
cd SPICE
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
spice --version
spice --help
```

This installs `spice-lineage`, its `spice` command, `pandas>=1.5,<3`, and the active R resources. R, R packages, IQ-TREE and BayesTraits must be configured separately. From a source checkout, `python SPICE.py` uses the same parser and implementation as `spice`.

## Analysis dependencies

| Stage | Additional requirements |
| --- | --- |
| `import-monopogen` | Rscript/base R to read prepared RDS matrices; Monopogen is optional upstream software. |
| `filter` | Rscript; `dplyr`, `progress`, and R's bundled `parallel`. |
| `phylogeny` | IQ-TREE 2 plus the R packages used by `clones`. |
| `clones` | Rscript; `ape`, `phangorn`, `phytools`, `ggplot2`, `ggtree`, `ggsci`. IQ-TREE is not executed. |
| `ancestry` | BayesTraits; Rscript; `ape`, `coda`, `janitor`, `posterior`. |
| `plasticity` | The ancestry R packages; BayesTraits when permutations are requested. |
| `summarize` | The installed Python package. |

For a source installation, run in R:

```r
install.packages(c(
  "dplyr", "progress", "ape", "phangorn", "phytools", "ggplot2",
  "ggsci", "coda", "janitor", "posterior", "BiocManager"
))
BiocManager::install("ggtree")
```

For the tested R 4.3.3 environment and compatible plotting-package constraints, use the [distribution dependency guide](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/distribution.md). Unpinned R installation commands can resolve different versions over time.

## External executables

Use IQ-TREE **2.x**, tested with **2.4.0**. IQ-TREE 3 has not been validated for SPICE. Obtain IQ-TREE and BayesTraits separately, then configure their executable paths:

```bash
export IQTREE2_BIN=/path/to/iqtree2
export BAYESTRAITS_BIN=/path/to/BayesTraitsV4
```

Replace the example paths with existing executable files. IQ-TREE resolution uses `IQTREE2_BIN`, then `iqtree2`, then `iqtree` on PATH. An invalid explicit `IQTREE2_BIN` is an error. BayesTraits resolution tries `--bayestraits_bin`, `BAYESTRAITS_BIN`, then `BayesTraitsV4`, `BayesTraitsV4.1.3` and `BayesTraits` on PATH. The real integration suite tested BayesTraits V4.1.3.

BayesTraits is external and is not redistributed in the SPICE wheel, Conda package, source archive or OCI image. Consult the [integration guide](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/integration-testing.md) for the tested upstream download and checksum details.

## Check command availability

```bash
spice import-monopogen --help
spice filter --help
spice phylogeny --help
spice clones --help
spice ancestry --help
spice plasticity --help
spice summarize --help
```

Help confirms command availability; it does not exercise R or external scientific tools. Try the small [filtering tutorial](Tutorial.md) after installing the analysis dependencies.

Local wheel development remains in [packaging](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/packaging.md). Conda/OCI build instructions remain in [distribution staging](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/distribution.md). For a server-managed installation, see [Galaxy](Galaxy.md).
