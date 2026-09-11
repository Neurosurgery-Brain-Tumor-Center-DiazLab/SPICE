# Real external-tool integration (Phases 3 and 4)

This suite validates the installed SPICE package against **IQ-TREE 2.4.0** and
**BayesTraits V4.1.3** on Linux x86_64. It uses only committed, synthetic data.
It does not establish biological accuracy, calibrated statistical significance,
optimal clone thresholds or statistical power.

## Run locally

From the checkout, with micromamba 2.3.2 available:

```bash
micromamba create -y -p "$PWD/.local-ci/integration-env" -f ci/integration-linux-64.lock
micromamba run -p "$PWD/.local-ci/integration-env" python3 scripts/check_integration.py
# Retain evidence at a chosen NEW directory outside the checkout and any Git repo:
micromamba run -p "$PWD/.local-ci/integration-env" python3 scripts/check_integration.py \
  --work-dir /tmp/spice-integration-review --repeat 3
```

The runner always retains its temporary output directory and prints its location.
Failures return nonzero. No tool is silently skipped. The optional repeat count
reruns both fixtures with independent IQ-TREE invocations and different
BayesTraits seed bases; default one is sufficient for a routine smoke test.

To supply an existing official V4.1.3 installation instead of downloading:

```bash
export BAYESTRAITS_BIN=/absolute/path/to/BayesTraitsV4
micromamba run -p "$PWD/.local-ci/integration-env" python3 scripts/check_integration.py
```

The path must name an executable Linux ELF binary. Its V4.1.3 banner and SHA-256
are recorded before inference. An explicitly supplied binary is never modified.
IQ-TREE uses `IQTREE2_BIN` or executable discovery (`iqtree2`, then `iqtree`);
the runner requires exactly 2.4.0. It never uses shell aliases.

The runner builds a fresh wheel, creates an external venv, and non-editably
installs the wheel with Python dependency versions constrained to the locked
environment. It removes PYTHONPATH/PYTHONHOME and Git environment overrides.
The test prints the wheel's site-packages import path and absolute `spice`
executable, verifies pip's wheel URL/hash, and compares runtime package hashes
to the source. All analysis commands run from an external directory, including
paths with spaces. Logs, provenance and command durations remain available;
the source checkout is never the tested import location.

## Reproducible dependencies and binary acquisition

`ci/integration-environment.yml` records dependency intent.
`ci/integration-linux-64.lock` pins 210 conda-forge/Bioconda packages by exact
URL and SHA-256, separately from the unchanged Phase 1 environment. It includes
Python 3.11, R 4.3.3, posterior 1.6.0, ggplot2 3.5.2, ggtree 3.10.0 and IQ-TREE
2.4.0. The runner prints Python/R/tool versions and all directly required R
package versions. Missing packages fail before inference.

The official [University of Reading V4.1.3 page](https://www.evolution.reading.ac.uk/BayesTraitsV4.1.3/BayesTraitsV4.1.3.html)
links the [Linux archive](https://www.evolution.reading.ac.uk/BayesTraitsV4.1.3/Files/BayesTraitsV4.1.3-Linux.tar.gz).
The runner downloads that unauthenticated HTTPS URL, verifies the pinned archive
hash, extracts only its regular executable member, then verifies the binary
hash **before** making it executable:

- Archive SHA-256: `cf0f5d9afa6ab74ae5aa6f386d1b3a4bc20d25643878aecddab459259b030674`.
- Binary SHA-256: `711024887c5484d5f6e768313b1aafea01c83705234e9a1172d5ed8e8f33bb4d`.
- Member: `BayesTraitsV4.1.3-Linux/BayesTraitsV4`.
- Banner: `BayesTraits V4.1.3 (Sep 27 2024)`.

These hashes were calculated from the official HTTPS download; they are
repository integrity pins, not a claim of an upstream signature. Changed
downloads fail closed. There is no unofficial mirror, repository secret,
vendored binary or V5 fallback. Downloaded binaries live in a separate temporary
directory that is removed on success and failure. They are executable only for
the run, never retained in the evidence directory or uploaded.

V4.1.3 has no version-query API; its usage banner identifies the version.
The runner supplies a newline and requires a zero exit code. Test-only
`OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` bound numerical-library
resources and avoid an observed WSL1 failure tearing down the official binary's
static OpenBLAS threads (`munmap` returned EINVAL). Every inference also must
exit zero, create complete logs and pass all QC. No external exit is ignored.
Core dumps are disabled for integration runs.

To refresh the environment deliberately, solve the intent file with strict
conda-forge/Bioconda priority, export `micromamba list -p PREFIX --explicit --sha256`,
retain only HTTPS package URLs after `@EXPLICIT`, and check every SHA-256.
Recreate a second prefix from the resulting lock and run the full suite there.
Do not update the normal Phase 1 lock for integration-only dependencies.

## Fixture contracts

The [phylogeny fixture](../tests/integration/fixtures/phylogeny/README.md) contains
15 cells x 700 variants. Filtering must produce exactly 13 cells x 696 sites,
preserving ordered REF/ALT counts and FASTA bases. Real IQ-TREE, with JC and
1000 UFBoot/SH-aLRT replicates, feeds the packaged BranchSupportCut.R.
Manual cutoff 0.10, support cutoffs 90/75, minimum two tips and Ref rooting must
recover three four-cell groups up to clone-label permutation. Assertions cover
real support labels, rooting/selection metadata, trusted membership, readable
NEXUS/Newick exports and executable provenance. No exact stochastic tree,
branch length or support percentage is required.

Each real phylogeny run is followed by installed `spice clones` using an identical
copy of its IQ-TREE tree at `external IQ-TREE input/renamed supported tree.nwk`.
The separate `clones with spaces` output uses the same sample and clone/rooting
settings. It runs despite an invalid `IQTREE2_BIN` inference setting; the required
fast subprocess regression separately forbids IQ-TREE dispatch, including version
probes. The real suite substitutes no inference executable.

The comparison requires identical parsed rooting/selection metadata and complete
branch-cut tables, clone partitions up to label permutation, and per-tip trusted
status and unassigned reasons. Independent R checks match clone exports by tip
sets and compare rooted topology and branch lengths in both Newick and NEXUS,
including the number of exportable clones. The Phylo file inventory and PDF
headers are checked; PDF bytes, timestamps and differing command provenance are
not compared. The input copy must remain unchanged, with no inference artifacts
created in the standalone output. Installed missing-tree and absent-outgroup
failures must retain failed runtime JSON.

`clones` provenance includes the original tree path, every shared setting, R
versions and installed source hashes. Its executable inventory still records
discoverable paths/hashes but omits the IQ-TREE version probe. Discovery does not
mean the command executed that tool. See [clones.md](clones.md).

The separate [ancestry fixture](../tests/integration/fixtures/ancestry/README.md)
has twelve tips, eleven internal nodes and two states with six tips each.
Its reversed state-table order checks reconciliation. Two chains use 50,000
iterations, 10,000 burn-in and sampling every 100 (400 retained draws each),
no stepping stones, one retry, R-hat < 1.2, bulk/tail ESS >= 20, recorded legacy
ESS/PSRF cutoffs 20/1.2 and posterior cutoff 0.5. These are explicit test-only
settings. Every final chain must complete its exact sample grid, and model
and node QC must pass. Posterior ranges/sums, state mapping, confidence gating
and real BayesTraits banner/path/hash provenance are checked.

Plasticity uses matching settings for three real permutation ancestry runs,
the greater alternative and shuffle seed 12345. Every replicate must succeed;
finite P-values must satisfy the existing empirical formula. Edge classification,
counts and denominator are checked independently from state order. An installed
`spice summarize` smoke check connects the resulting test to the summary layer.

Fast negative checks reject a missing tip state before BayesTraits execution,
an absent IQ-TREE executable, and model-QC-failed ancestry before plasticity.
Existing deterministic R tests retain retry/failure-isolation coverage; the
real suite uses no mocked inference executables or in-process inference mocks.

## Manual GitHub Actions workflow

Maintainers run:

**Actions -> SPICE Phase 3 Integration -> Run workflow -> select branch -> Run workflow**

The separate `.github/workflows/integration.yml` has **workflow_dispatch only**:
no pull_request, push or schedule triggers. It is **not required for PR merge**.
The existing **Phase 1 required checks** job and its normal PR gate remain intact;
this phase does not change branch protection or rulesets.

The workflow uses Ubuntu 24.04, read-only contents permission, pinned Action
commits, no shared environment cache, no secrets and a 75-minute timeout.
Allow roughly 5–15 minutes including installation, subject to runner/network
speed; observed local timings belong in the engineering handoff.

Success means the full runner exits zero with zero skipped tools/tests, the combined and standalone clone paths, ancestry and all three permutations passing. Inspect the job log and
`result.json`; the `spice-integration-text-evidence` artifact retains selected
text logs, QC tables and provenance for 14 days, including failure evidence.
Its explicit file allowlist excludes binaries, wheels, archives and environments.

[GitHub requires a workflow file on the default branch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)
to enable workflow_dispatch.
A newly introduced manual-only workflow may therefore need maintainer registration
on main before its first feature-branch dispatch. Do not add an automatic trigger
or merge this PR merely to bypass that restriction. Hosted success must be
reported only after observing a successful run; local success is separate.

## Engineering boundary

Real V4.1.3 execution exposed that SPICE passed accepted Newick input directly
to a tool requiring NEXUS. SPICE now writes a full-precision attempt-local NEXUS
subprocess input for Newick. Node identities, original-input fingerprints, tree
rooting/lengths and calculations remain tied to the original parsed tree.
Already-NEXUS input is passed through unchanged. A second reproduced defect
was the BayesTraits command language splitting an absolute LogFile path on
spaces. Each chain now runs from its own directory with a local log basename;
the same absolute log locations and chain outputs are retained.
The installed assertions require space-containing output paths and complete
chain logs at those original locations. A fast real-file regression and
the installed-wheel Newick fixture verify preservation.

The version remains 0.2.0 (unreleased); this compatibility correction is recorded
in CHANGELOG.md. Scientific algorithms/defaults, tables and overwrite guards
are unchanged. Phase 4 adds only the shared clone interface and explicit R tree
path; the R scientific body is unchanged. No SPICE,
IQ-TREE or BayesTraits software is published; Bioconda/container/PyPI/Galaxy
publication and scientist-led method validation remain out of scope.
