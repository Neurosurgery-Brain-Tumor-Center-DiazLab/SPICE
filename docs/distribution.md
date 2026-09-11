# Conda and OCI distribution staging (Phase 5)

SPICE **0.2.0 remains unreleased**. These recipes and scripts build local review
artifacts only. Nothing has been published to PyPI, Anaconda.org/Bioconda,
GHCR, Quay or Docker Hub; no release or tag is created. Public installation
commands are not yet available. Phase 6 Galaxy testing uses this unpublished
local package; see [the Galaxy guide](galaxy.md).

## Architecture and immutable source

The classic recipe is
[packaging/bioconda/spice-lineage/meta.yaml](../packaging/bioconda/spice-lineage/meta.yaml).
The package-named directory can later be copied into bioconda-recipes.
The recipe builds the existing Python distribution with pip, with dependency
installation, build isolation and pip caching disabled. Conda supplies the
actual build requirements: Python, pip and setuptools >=77.

The immutable source is the tested Phase 6 serialization-fix commit:
d0570d923d7880139a3f4c0a7a2b2e7ce65bc307. The commit-addressed GitHub archive
has SHA-256
47ab47321d96bb09c5c2089a0155a029e415610929fef43aa8522f51d6fb703b.
No moving branch, invented tag or placeholder hash is used. A commit archive
also avoids the Bioconda lint restriction on git_url/git_rev.
The staged source now includes the minimal BayesTraits serialization fix for
IQ-TREE internal support labels. Only the temporary subprocess NEXUS copy omits
that metadata; original trees/supports, fingerprints, node identities and
scientific calculations remain unchanged. Exact seeded ancestry equivalence
and format/topology/branch-length regressions cover the fix.

The package is **noarch: python**, version **0.2.0**, build **0**. Its own
payload is interpreted Python/R source; platform-specific R and IQ-TREE
dependencies do not turn that payload into a compiled Python extension.
Validation targets Linux x86_64 with Python 3.11. No other operating system or
container architecture is claimed to be validated. Recipe lightweight tests may
also resolve another supported Python version; evidence records the actual solve.

Conda owns the spice executable, spice_lineage imports and packaged R resources.
The package includes its license and metadata. It excludes source fixtures,
.git, environments, caches, patient data, arbitrary legacy scripts and
BayesTraits binaries. The checker verifies the exact Python/R payload hashes
and an allowlist of distribution metadata.

## Direct runtime dependency policy

These constraints start from the successful Phase 3/4 integration lock.
They do not pin every transitive dependency. R stays on 4.3; posterior and
ggtree stay on the validated minor versions; ggplot2 stays on 3.5 to preserve
the plotting stack tested with ggtree 3.10. Other R packages stay within the
validated major boundary (coda within 0.19). The Python project contract
remains >=3.10 and pandas >=1.5,<3. IQ-TREE remains version 2.

| Conda package | Recipe constraint | Phase 4 tested version |
| --- | --- | --- |
| python | >=3.10,<4 | 3.11.16 |
| pandas | >=1.5,<3 | 2.2.3 |
| r-base | >=4.3.3,<4.4.0a0 | 4.3.3 |
| r-ape | >=5.8,<6 | 5.8_1 |
| r-coda | >=0.19,<0.20 | 0.19_4.1 |
| r-janitor | >=2.2,<3 | 2.2.1 |
| r-posterior | >=1.6.0,<1.7 | 1.6.0 |
| r-dplyr | >=1.1,<2 | 1.1.4 |
| r-progress | >=1.2,<2 | 1.2.3 |
| r-phangorn | >=2.12,<3 | 2.12.1 |
| r-phytools | >=2.5,<3 | 2.5_2 |
| r-ggplot2 | >=3.5.2,<3.6 | 3.5.2 |
| r-ggsci | >=3.2,<4 | 3.2.0 |
| bioconductor-ggtree | >=3.10,<3.11 | 3.10.0 |
| iqtree | >=2.4,<3 | 2.4.0 |

R's base/recommended packages (parallel, stats, utils, tools and graphics) come
with r-base. There is no runtime r-biocmanager: ggtree is a direct Bioconda
dependency, not installed during an R session. Monopogen is optional upstream
software and is not required by standard-input processing.

The declarative recipe describes compatible requirements. Each run records
exact runtime URLs/builds/hashes; the OCI image consumes that exact solved lock,
including the local SPICE artifact. This reproduces an observed environment;
the recipe alone does not promise byte-identical artifacts across future
repodata changes.

## Build and validate locally

Use Linux x86_64, Git, Docker for complete validation, and micromamba 2.3.2.
The toolchain intent is ci/distribution-environment.yml; its explicit
SHA-256-pinned realization is ci/distribution-linux-64.lock.

~~~bash
micromamba create -y -p /tmp/spice-distribution-tools \
  -f ci/distribution-linux-64.lock --strict-channel-priority
micromamba run -p /tmp/spice-distribution-tools \
  python3 scripts/check_distribution.py --work-dir /tmp/spice-distribution
~~~

Choose a **new directory outside every Git checkout**, without spaces for
Conda-build's prefix support. The tests create input/output paths with spaces.
Logs and artifacts are retained there; nothing is added to a public channel.
The default requires all Conda and container checks. Missing tools, failed
assertions and failed commands return nonzero.

On a machine without Docker, explicitly run only the local Conda stage:

~~~bash
micromamba run -p /tmp/spice-distribution-tools \
  python3 scripts/check_distribution.py --conda-only \
  --work-dir /tmp/spice-conda-review
~~~

This prints PARTIAL and records complete=false with container pending.
It is not a Phase 5 completion result; the full manual hosted workflow must
still pass. Docker absence is never silently treated as a successful full run.

The checker renders/builds/tests the recipe, indexes a new local channel,
solves a fresh prefix, verifies package origin and executable/import locations,
prints the exact runtime package list, checks the artifact content and SHA-256,
and runs real R filtering, fixed-tree clones and IQ-TREE phylogeny. It also
checks independent R clone exports/equivalence, CLI help, missing-BayesTraits
errors, source hashes, versions and runtime provenance. No PYTHONPATH or
source checkout import is permitted.

For individual recipe commands after activating the toolchain:

~~~bash
export CONDA_CHANNEL_PRIORITY=strict
export CONDA_SOLVER=libmamba
conda render packaging/bioconda/spice-lineage --python 3.11 \
  --override-channels -c conda-forge -c bioconda
conda build packaging/bioconda/spice-lineage --python 3.11 \
  --override-channels -c conda-forge -c bioconda \
  --no-anaconda-upload --output-folder /tmp/spice-local-channel
conda index /tmp/spice-local-channel
conda create -y -p /tmp/spice-local-install --strict-channel-priority \
  --override-channels -c file:///tmp/spice-local-channel \
  -c conda-forge -c bioconda 'spice-lineage=0.2.0' 'python=3.11'
cd /tmp
/tmp/spice-local-install/bin/spice --version
~~~

Priority is **local channel, conda-forge, bioconda**, strictly ordered, with
defaults and user channels excluded. Build dependencies use only conda-forge
and bioconda. Keep any caches or outputs outside the repository.

## OCI image and external BayesTraits

[Containerfile](../packaging/container/Containerfile) uses the Linux/amd64
mambaorg/micromamba:2.3.2 manifest digest
sha256:955819619f303e2aa1dc1ba89beefe7f326a378b3d0782a4a0d28b1cf11b68b6.
A minimal generated context contains only the local package, exact solved
runtime lock and build definition. The install stage installs those packages;
the runtime stage copies only the installed /opt/conda environment. Package
archives, build files and the temporary channel remain outside the final image.

The image has an empty ENTRYPOINT and spice on PATH. OCI labels record SPICE
version, immutable source commit, GPL-3.0-only license and source repository;
an additional label records the Conda artifact SHA-256. The checker records
the local image ID. A locally built, unpushed image need not have a registry
RepoDigest; an empty RepoDigests list is not a public digest or publication.

Container tests run as the invoking host UID/GID, mount inputs read-only and
results writable, and verify host-owned/readable outputs. They run without
network access against a read-only root filesystem, with writable /tmp.
See [container instructions](../packaging/container/README.md) for manual
build/run and BayesTraits bind-mount examples.

BayesTraits V4.1.3 remains separately acquired and externally supplied with
--bayestraits_bin, BAYESTRAITS_BIN or PATH. Neither recipe nor image downloads,
bundles or redistributes it. The distribution suite checks absence and clear
missing-tool errors. The unchanged
[real integration suite](integration-testing.md) verifies licensed/official
V4.1.3 execution separately.

## Manual hosted validation and evidence

**SPICE Phase 5 Distribution** in .github/workflows/distribution.yml uses
workflow_dispatch only, Ubuntu 24.04, read-only contents permission, pinned
Actions and a locked packaging toolchain. It requires no secrets or registry
credentials, never uploads a package/image to a registry and is non-required.
The existing **Phase 1 required checks** status name is unchanged.
**SPICE Phase 3 Integration** remains manual-only and must also pass on the PR branch.

After opening the lab-repository PR:

~~~bash
gh workflow run integration.yml --repo Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE \
  --ref codex/phase5-packaging
gh workflow run distribution.yml --repo Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE \
  --ref codex/phase5-packaging
~~~

GitHub may require a newly introduced manual workflow to be registered on the
default branch before dispatch. If dispatch is unavailable, report it as a
blocker and obtain maintainer direction; do not add push/PR triggers, commit
to main or merge the PR to bypass it.

The workflow retains text-only logs, JSON manifests and explicit runtime lock
for 14 days. No Conda binary, image tarball, BayesTraits executable/archive,
environment or cache is uploaded. Evidence includes source and checkout commits,
recipe hash/version/build, artifact filename/SHA-256, solved packages, installation
prefix/import/executable paths, SPICE/IQ-TREE/R versions, base digest, local image
ID, command results and BayesTraits absence. Local paths in run evidence describe
that run; they are not hard-coded into the recipe.

## Eventual Bioconda submission (separate authorization)

1. Review/merge Phase 5 only after required source/package CI and both manual
   workflows are green. Obtain separate maintainer authorization for publication.
2. Choose/review the public version and source release. Prefer a real official
   release tag/archive; update version/build/source SHA-256 consistently. Never
   invent a release tag or reuse this unreleased staging build as a public release.
3. Confirm the software name remains available, the license/source and all runtime
   constraints are appropriate, and a consenting recipe-maintainer handle.
4. In a separately authorized Bioconda contribution, copy the package-named
   recipe directory into recipes/spice-lineage. Run the then-current
   bioconda-utils lint/build/container tests and resolve reviewer feedback.
5. Follow Bioconda's contribution workflow for the external PR. Do not upload
   artifacts manually or include BayesTraits.
6. After acceptance and actual publication, verify the public package and
   associated BioContainer identifiers before documenting public install commands.
   Bioconda infrastructure builds package-associated BioContainers; this staging
   PR does not establish that a public SPICE BioContainer exists.
7. Authorize Galaxy/Planemo separately after distribution validation and release
   decisions. No Galaxy implementation is part of Phase 5.

References, checked for this phase:
[Bioconda contribution workflow](https://bioconda.github.io/contributor/workflow.html),
[recipe guidelines](https://bioconda.github.io/contributor/guidelines.html),
[lint rules](https://bioconda.github.io/contributor/linting.html),
[Bioconda contributions and automated containers](https://bioconda.github.io/contributor/index.html),
[micromamba container usage](https://micromamba-docker.readthedocs.io/en/stable/advanced_usage.html).

## Phase 6 Galaxy staging

The [Galaxy guide](galaxy.md) documents five native wrappers and a collection
workflow pinned to IUC IQ-TREE 2.4.0. The existing manual integration workflow
retains the real scientific job and adds a separate Galaxy job. It builds and
checks this unpublished local Conda package before resolving Galaxy dependencies
from its file channel. BayesTraits remains temporary and external. Normal
required CI does not start Galaxy. Tool Shed/GTN and public package/container
publication remain separate maintainer decisions.
