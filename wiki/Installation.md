# Installation

[Home](Home.md) · [Next: Input data](Input-Data.md)

SPICE 0.2.0 is unreleased. Install from the lab source repository, or use a locally built package following the engineering guides. No public PyPI, Bioconda or container installation is claimed here.

## Recommended installation: Conda/micromamba

The independently cold-start-validated source stack is **Linux x86_64, Python 3.11, R 4.3.3 and IQ-TREE 2.4.0**. Other platforms and IQ-TREE 3 are not validated. Conda is preferred because the R/Bioconductor phylogenetics and plotting stack can drift. The compatibility bounds below reproduce the dependency family used in packaging and the successful independent cold-start run; they are not an exact transitive lock.

### Prerequisites and fresh environment

Use a Linux x86_64 Bash terminal with Git and micromamba available. The cold-start run used micromamba **2.3.2**. Start without inherited Python or R library overrides (such as custom `PYTHONPATH` or `R_LIBS_USER`). Run the following in the same terminal, choosing an unused environment name:

```bash
eval "$(micromamba shell hook --shell bash)"
micromamba create -y -n spice-source \
  --override-channels -c conda-forge -c bioconda \
  --strict-channel-priority 'python=3.11'
micromamba activate spice-source
```

### Install the validated dependencies

Keep conda-forge before bioconda and strict channel priority:

```bash
micromamba install -y -p "$CONDA_PREFIX" \
  --override-channels \
  -c conda-forge \
  -c bioconda \
  --strict-channel-priority \
  'python=3.11' \
  'pip' \
  'setuptools>=77' \
  'wheel' \
  'pandas>=1.5,<3' \
  'r-base=4.3.3' \
  'r-ape>=5.8,<6' \
  'r-coda>=0.19,<0.20' \
  'r-janitor>=2.2,<3' \
  'r-posterior>=1.6.0,<1.7' \
  'r-dplyr>=1.1,<2' \
  'r-progress>=1.2,<2' \
  'r-phangorn>=2.12,<3' \
  'r-phytools>=2.5,<3' \
  'r-ggplot2>=3.5.2,<3.6' \
  'r-ggsci>=3.2,<4' \
  'bioconductor-ggtree>=3.10,<3.11' \
  'iqtree=2.4.0'
```

### Clone and install SPICE

Install non-editably from a fresh checkout into the activated environment. Dependencies and build tools were installed above, so pip need not resolve or download them:

```bash
git clone https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.git
cd SPICE
python -m pip install --no-index --no-deps --no-build-isolation .
python -m pip check
spice --version
spice --help
spice import-monopogen --help
spice filter --help
spice phylogeny --help
spice clones --help
spice ancestry --help
spice plasticity --help
spice summarize --help
```

The distribution name is `spice-lineage`; it installs the `spice` command and active R resources. Help checks command availability, not scientific-tool execution. Keep this checkout for the [synthetic CLI tutorial](Tutorial.md#end-to-end-synthetic-cli-exercise).

### Configure external BayesTraits

Acquire **BayesTraits V4.1.3** separately from the official upstream source. Follow the [integration guide's download and checksum details](../docs/integration-testing.md#reproducible-dependencies-and-binary-acquisition), then configure the existing executable:

```bash
export BAYESTRAITS_BIN=/absolute/path/to/BayesTraitsV4
```

Replace that path with your verified executable. BayesTraits remains external and is **not redistributed** in the SPICE wheel, Conda package, source archive or OCI image.

The dependency recipe already supplies IQ-TREE 2.4.0. IQ-TREE resolution uses `IQTREE2_BIN`, then `iqtree2`, then `iqtree` on PATH. If an explicit path is needed, set `IQTREE2_BIN` to the installed 2.4.0 executable; an invalid explicit value is an error. BayesTraits resolution tries `--bayestraits_bin`, `BAYESTRAITS_BIN`, then `BayesTraitsV4`, `BayesTraitsV4.1.3` and `BayesTraits` on PATH.

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

## Advanced alternatives and engineering validation

The former unpinned CRAN/BiocManager procedure is not the currently cold-start-validated route. On fresh R 4.3.3 it failed to install/load required dependencies, including phangorn, phytools and ggtree. Unpinned resolution changes over time; use the Conda/micromamba procedure above for the validated dependency family.

From a source checkout, `python SPICE.py` uses the same parser and implementation as `spice`. Local wheel development remains in [packaging](../docs/packaging.md), and specialized locked checks remain in [source CI](../docs/ci.md) and [real-tool integration](../docs/integration-testing.md). Conda/OCI build instructions remain in [distribution staging](../docs/distribution.md). For a server-managed installation, see [Galaxy](Galaxy.md).
