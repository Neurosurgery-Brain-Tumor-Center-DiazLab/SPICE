# SPICE engineering handoff - Phase 5

## Scope and starting gate

Started on clean codex/phase5-packaging at current origin/main
e6c23ca39f44a47a8351e49d642e977ad8a7f87b, using the lab repository https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.
[PR #4](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/pull/4) was merged. The exact main commit had
[successful normal CI](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34625525228).
The final Phase 4 commit had [successful real integration](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34587686887),
including clone_equivalence=pass and arbitrary_tree_path=pass.
No applicable AGENTS.md was found. Approved WSL commands worked around the
Windows sandbox helper's initialization failure.

Before edits, all merged baselines passed: 35 source tests with zero skips,
five installed-wheel checks, and the full real IQ-TREE/BayesTraits suite.
Local logs are /tmp/spice-phase5-baseline-ci.log,
/tmp/spice-phase5-baseline-package.log and
/tmp/spice-phase5-baseline-integration/result.json.

## Architecture and source identity

Classic recipe: packaging/bioconda/spice-lineage/meta.yaml.
Package: spice-lineage 0.2.0, build 0, noarch: python.
Import namespace: spice_lineage. Executable: spice.
The package-named recipe directory supports later Bioconda submission.
Its interpreted Python/R payload is architecture independent; Phase 5's tested
runtime platform is Linux x86_64. No additional platform is claimed.

The recipe uses the exact Phase 4 commit archive, not a moving branch or fake
release. Source archive SHA-256:
0102b4896cdb8bcaa4a1bcda22cf373d195b462863c01c0d8408b74c2a00257f.
The Conda artifact payload is compared byte-for-byte by SHA-256 with all
production Python files, the version file and all seven R resources.
No production Python or R file changed. Scientific algorithms, default
parameters, QC/retries, clone/rooting behavior and output schemas are unchanged.

Direct runtime requirements:

- bioconductor-ggtree >=3.10,<3.11
- iqtree >=2.4,<3
- pandas >=1.5,<3
- python >=3.10,<4
- r-ape >=5.8,<6
- r-base >=4.3.3,<4.4.0a0
- r-coda >=0.19,<0.20
- r-dplyr >=1.1,<2
- r-ggplot2 >=3.5.2,<3.6
- r-ggsci >=3.2,<4
- r-janitor >=2.2,<3
- r-phangorn >=2.12,<3
- r-phytools >=2.5,<3
- r-posterior >=1.6.0,<1.7
- r-progress >=1.2,<2

The dependency rationale and Phase 4 tested versions are in
[distribution.md](distribution.md). The new clean runtime resolves Python 3.11;
the recipe's noarch lightweight tests also passed with Python 3.14. The exact
solved runtime list contains 205 packages and is retained in the evidence.
BayesTraits V4.1.3 is external through --bayestraits_bin, BAYESTRAITS_BIN or PATH;
neither the recipe nor image downloads or redistributes it.

## Observed local validation

- Required source/R/CLI: 40 tests, zero skips/failures/errors.
  /tmp/spice-phase5-final-ci.log.
- Wheel/sdist: exact allowlists (23 wheel files, 98 sdist files), all five
  external installed-wheel tests passed. /tmp/spice-phase5-final-package.log.
- Full real integration: pass, zero skips, 267.84 seconds.
  Clone equivalence, ancestry, all three plasticity permutations, summary and
  negative paths passed. /tmp/spice-phase5-final-integration/result.json.
  The temporary official BayesTraits executable was verified removed.
- Conda recipe render/build/tests, fresh local channel, fresh installation and
  all installed checks passed. Evidence: /tmp/spice-phase5-reviewed-distribution/result.json.
- Package: spice-lineage-0.2.0-py_0.conda.
- Package SHA-256: 8b55609157a321790afacd939a4a7a1b5a0c42baa0d9a2da640fe5a4cf17f603.
- Clean prefix: /tmp/spice-phase5-reviewed-distribution/runtime-env.
- Executable proven inside that prefix: /tmp/spice-phase5-reviewed-distribution/runtime-env/bin/spice.
- Import proven inside that prefix: /tmp/spice-phase5-reviewed-distribution/runtime-env/lib/python3.11/site-packages/spice_lineage.
- Conda checks ran all CLI help/version commands, actual standard filtering,
  a supported synthetic tree, real IQ-TREE phylogeny, independent R clone export
  and equivalence checks, missing-BayesTraits error handling and provenance.
  No required Conda check skipped. A hand-written test tree was replaced with
  an already validated synthetic IQ-TREE tree; no production fix was needed.
- actionlint passed for all three workflows; git diff --check passed.

Installed tool versions:

```text
IQ-TREE multicore version 2.4.0 for Linux x86 64-bit built Feb 12 2025
Developed by Bui Quang Minh, Nguyen Lam Tung, Olga Chernomor, Heiko Schmidt,
Dominik Schrempf, Michael Woodhams, Ly Trong Nhan, Thomas Wong
R version 4.3.3 (2024-02-29)
       ape       coda    janitor  posterior      dplyr   progress   phangorn
   "5.8.1" "0.19.4.1"    "2.2.1"    "1.6.1"    "1.1.4"    "1.2.3"   "2.12.1"
  phytools    ggplot2     ggtree      ggsci
   "2.5.2"    "3.5.2"   "3.10.0"    "3.2.0"
```

## Container and hosted gates

Base image: mambaorg/micromamba:2.3.2@sha256:955819619f303e2aa1dc1ba89beefe7f326a378b3d0782a4a0d28b1cf11b68b6.
The generated minimal context consumes this local Conda artifact and the exact
runtime lock. A second stage copies only the installed environment. It excludes
.git, credentials, BayesTraits, channel/build files and downloaded package caches.
OCI labels retain version, source, license, source revision and package hash.
ENTRYPOINT is empty and spice is on PATH.

This local machine is WSL1 without Docker. The explicit --conda-only run records
complete=false and container pending, not a complete Phase 5 pass. No local
OCI image ID or successful local container result is claimed.
The manual hosted distribution workflow must build/test the image with read-only
synthetic inputs, writable host-owned results, paths with spaces and no network.
It records the image ID/base digest and verifies BayesTraits absence.

The required normal CI job stays Phase 1 required checks. Existing integration.yml
is unchanged, manual-only and non-required. New distribution.yml is also
workflow_dispatch only, non-required, read-only and uses pinned Actions and a
locked toolchain. Only text logs/JSON/explicit lock evidence is uploaded.
The PR records actual hosted CI, Phase 3 Integration and Phase 5 Distribution
URLs and outcomes. Phase 5 is incomplete until both manual hosted gates pass.
If GitHub requires default-branch registration of the new workflow, maintainer
direction is required: do not commit to main, add automatic triggers or merge
this PR to bypass that restriction.

## Release and handoff

Version remains 0.2.0 unreleased. No public package/image was published, no
GitHub release/tag was created, and no external Bioconda PR was opened.
Galaxy/Planemo/Phase 6 has not started. Review the lab-repository Phase 5 PR,
finish all hosted gates, then separately authorize any publication or Phase 6.
The exact local build/install/container commands and eventual Bioconda release
checklist are in [distribution.md](distribution.md).
