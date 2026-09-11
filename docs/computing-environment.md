# Observed computing environment

Collected directly from the active `c4-n31` allocation (Slurm job 1665477),
Conda environment `r-env`, on 2026-09-07 America/Los_Angeles.
This is an inventory of the existing environment, not a tested clean-install lockfile.

| Component | Observed version |
|---|---|
| Python | 3.11.0 |
| R | 4.2.0 (2022-04-22) |
| Linux kernel | 4.18.0-553.123.1.el8_10.x86_64 |
| glibc | 2.28 |
| BayesTraits | 4.1.3 (Sep 27 2024 build banner) |
| IQ-TREE | Not resolved from current PATH or IQTREE2_BIN |
| Monopogen | Not resolved from current PATH or MONOPOGEN_BIN |

Unresolved executables may exist elsewhere on the server; this inventory does not
assert that they are absent from the entire server. Monopogen is upstream of the
SNV workflow. Neither program is required for prepared-tree ancestry/plasticity.
BayesTraits version was read from an actual retained execution banner.

| Python package | Version | Use |
|---|---|---|
| pandas | 1.5.1 | Main CLI |
| numpy | 1.23.4 | pandas dependency |
| pysam | 0.20.0 | Optional read counter |
| tqdm | 4.66.1 | Optional read counter |

| R package | Version | Use |
|---|---|---|
| ape | 5.7-1 | Main CLI |
| coda | 0.19-4 | Main CLI |
| janitor | 2.1.0 | Main CLI |
| posterior | 1.6.0 | Main CLI |
| dplyr | 1.1.3 | Main CLI |
| progress | 1.2.2 | Main CLI |
| phangorn | 2.11.1 | Phylogeny |
| phytools | 2.1-1 | Phylogeny |
| ggplot2 | 3.4.3 | Phylogeny |
| ggtree | 3.6.2 | Phylogeny |
| ggsci | 3.2.0 | Phylogeny |
| btw | 2.0 | Legacy scripts only |
| tidybayes | 3.0.7 | Legacy scripts only |
| tidytree | 0.4.5 | Legacy scripts / ggtree dependency |
| tidyverse | 1.3.2.9000 | Legacy scripts only |
| patchwork | 1.1.3 | Legacy scripts only |
| tidyr | 1.3.0 | Legacy scripts / dependency |

For portable setup, use `environment.yml` followed by
`Rscript scripts/install_R_dependencies.R`. Install external binaries separately.
The environment definition specifies a compatible installation target; its full
resolution in a new environment has not been tested here.

## Phase 1 clean Linux test environment

The historical inventory above is unchanged. The general Conda target now uses
R 4.3.3 and posterior 1.6.0 because conda-forge has no posterior 1.6.0 build for
R 4.2. The revised general environment solved successfully; its complete plotting
installation was not executed. R 4.3 uses Bioconductor 3.18, as detailed in
[CI installation notes](ci.md).

The required Phase 1 subset was installed locally in isolated Ubuntu 20.04/WSL1
prefixes with micromamba 2.3.2. Resolved direct versions: Python 3.11.16,
pandas 2.2.3, R 4.3.3, ape 5.8.1, coda 0.19-4.1, janitor 2.2.1,
posterior 1.6.0, dplyr 1.1.4, progress 1.2.3. NumPy resolved to 2.4.6.
All 162 package URLs and SHA-256 hashes are in ../ci/linux-64.lock.
See [engineering handoff](engineering-handoff.md) for actual check outcomes.
This does not establish real IQ-TREE/BayesTraits or plotting compatibility.
