# SPICE engineering handoff — Phase 3

## Starting state and scope

Checkout: `/home/aaron/SPICE`, remote
`https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.git`.
The clean feature branch `codex/phase3-integration-tests`, HEAD and fetched
origin/main all started at `10a73f62dbd9817967f7b971af21059e945a6b29`.
No intervening main changes or applicable AGENTS.md were found.
No reset, stash, discarded work, rebase or main-branch commit was used.

Phase 3 adds real-tool integration of the installed wheel. Phase 4 has not
started; no standalone clone command, scientific redesign, PyPI/Bioconda/
container publication or Galaxy work is included. The prior Phase 2 handoff
is retained in Git at the starting commit.

## Implementation and reviewed boundary

- `scripts/check_integration.py`: Linux-only, zero-skip runner; exact tool
  version checks, official BayesTraits download and pre-execution SHA-256
  verification, fresh wheel/venv, constrained runtime dependencies, neutral
  external cwd, logs/timings, and cleanup of downloaded executables.
- `tests/integration/`: explicit synthetic bundles, installed CLI assertions,
  independent R tree checks, and failure checks. No real-tool mocks.
- `ci/integration-environment.yml`, `ci/integration-linux-64.lock`: separate
  210-package integration environment. The explicit SHA-256 lock was recreated
  in a second isolated prefix before successful real-tool validation.
- `.github/workflows/integration.yml`: **SPICE Phase 3 Integration**,
  workflow_dispatch only, Ubuntu 24.04, read-only contents, pinned Action SHAs,
  75-minute timeout, no secrets, and an explicit text-only artifact allowlist.
- `MANIFEST.in`, `scripts/check_package.py`: include and verify integration
  development material in the sdist. Wheel contents stay unchanged.
- README, CHANGELOG, docs/ci.md, docs/packaging.md and
  [integration-testing.md](integration-testing.md): execution, checksums,
  fixture settings and scientific limits.

Only `spice_lineage/resources/r/spice_ancestry_utils.R` changes production code:

1. Real V4.1.3 rejected the original Newick subprocess input with
   `Tree file does not have a valid nexus tag`. A small boundary helper
   writes an attempt-local NEXUS with 17-digit branch lengths; existing NEXUS
   passes through. Original parsed-tree node IDs and input fingerprints remain
   authoritative. The real Newick wheel test failed before this fix; an
   additional fast file round-trip regression verifies root, topology, tip
   order and branch lengths.
2. Real V4.1.3 rejected an absolute `LogFile` path containing spaces.
   Each chain now runs from its own directory and uses its MCMC basename;
   expected absolute log paths remain unchanged. All inputs/executable paths
   are resolved before changing cwd, which is restored on exit. The real
   space-containing path assertion failed before the fix and now verifies
   complete chain logs and explicit local LogFile commands.

No variant filtering/count/FASTA semantics, site order/multiplicity, IQ-TREE
defaults/support order, clone algorithm/selection/rooting, BayesTraits model/
priors/MCMC defaults/seeds/retry policy, QC policy/threshold defaults,
posterior policy, state order, transition classification, permutation method,
P-value/BH calculation, scientific tables or overwrite safeguards changed.
Version remains **0.2.0 (unreleased)**; the engineering fixes are documented
without creating a new public release.

An external runtime issue was also diagnosed: the official binary's static
OpenBLAS spawned threads that failed WSL1 cleanup (`munmap` EINVAL), including
after completed inference. Test-only OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1
resolve it and bound resources. No exit code is ignored; version probes and
all real inference must exit zero.

## Synthetic fixtures and test-only settings

Phylogeny: **15 cells x 700 variants**, filtered to exactly **13 x 696**.
Ref plus A1-A4, B1-B4, C1-C4 remain; LowSupport and Excluded are removed.
Four all-REF sites are removed. 240 constant, 60 ingroup, and 132 sites per
four-cell group provide transparent strong signal, sister-pair and private
variation. Ref is the explicit outgroup. The trusted partition must be the
three four-cell sets, allowing arbitrary clone labels; Ref is unassigned.

One thread, JC, 1000 UFBoot/1000 SH-aLRT replicates, manual incoming-edge
cutoff 0.10, existing 90/75 support cutoffs and minimum clone size two.
Complete matrix/site/cell/FASTA assertions precede output metadata, partition,
tree readability and provenance checks. No exact stochastic tree is required.

Ancestry: **12 tips, 11 internal nodes, 22 positive-length edges**, two states
with six tips each. Reversed annotation rows test reconciliation; state order
(Progenitor=1, Differentiated=2) differs from alphabetical numeric encoding.
The input is independent of IQ-TREE output.

Two chains, 50,000 iterations, burn-in 10,000, sample period 100 (400 retained
draws/chain), no stepping stones; R-hat <1.2, bulk/tail ESS >=20, recorded
legacy ESS/PSRF cutoffs 20/1.2, posterior cutoff 0.5, one retry allowed.
Existing exponential hyperprior and seed derivation remain unchanged.
Plasticity uses matching settings and exactly three permutations with the
greater alternative and shuffle seed 12345. Three permutations test execution;
they are not a calibrated significance/power benchmark.

## Observed local results

Host: Ubuntu 20.04 under WSL1, Linux x86_64, glibc 2.31.
Windows sandbox process setup failed; authorized WSL commands ran directly
without modifying the system environment.

Both pre-edit baselines passed:
- Phase 1: 21 discovered/run, zero skips/failures/errors, all R QC and CLI checks.
- Phase 2: wheel/sdist inspection plus five non-editable-install checks.

After the integration fixes, both passed again with the added file conversion
regression. `git diff --check` and actionlint for both workflows passed.
The normal ci.yml, Phase 1 lock, CLI defaults and VERSION files are unchanged.

The full real suite first passed at `/tmp/spice-phase3-integration-05` in
**133.53 seconds**, including fresh wheel installation and three permutations.
The final repeated validation at `/tmp/spice-phase3-final-integration` passed
**three complete runs, zero skips, in 170.72 seconds total**. Seed bases were
12345, 13345 and 14345; each used independent IQ-TREE inference and three
BayesTraits-backed permutation replicates. All clone partitions and ancestry/
permutation QC assertions passed. Optional summary and deterministic failure
checks passed. These times exclude environment installation.

The final wheel:
`/tmp/spice-phase3-final-integration/dist/spice_lineage-0.2.0-py3-none-any.whl`

SHA-256:
`0d0689329260b7e74df02d1381070ddc4903a8736a482ec1471056d4f4b6d99d`

Installed executable:
`/tmp/spice-phase3-final-integration/venv/bin/spice`

Verified import:
`/tmp/spice-phase3-final-integration/venv/lib/python3.11/site-packages/spice_lineage`

Pip's non-editable wheel URL/hash and runtime source hashes were checked.
Runtime records explicitly report Git unavailable and include real executable
paths/hashes, IQ-TREE version output and retained BayesTraits banners.

## Exact external/runtime identity

- IQ-TREE **2.4.0**, from the SHA-256-pinned Bioconda package.
  Path: `/home/aaron/SPICE/.local-ci/integration-locked-env/bin/iqtree2`.
  Executable SHA-256:
  `77f5aaabea6427da0d9cc1c32e390f3b5bfb4916ce673be1c9bd95c141f22b82`.
- BayesTraits **V4.1.3 (Sep 27 2024)**, official University of Reading HTTPS
  [Linux archive](https://www.evolution.reading.ac.uk/BayesTraitsV4.1.3/Files/BayesTraitsV4.1.3-Linux.tar.gz).
  Archive SHA-256:
  `cf0f5d9afa6ab74ae5aa6f386d1b3a4bc20d25643878aecddab459259b030674`.
  Binary SHA-256:
  `711024887c5484d5f6e768313b1aafea01c83705234e9a1172d5ed8e8f33bb4d`.
  Final run path `/tmp/spice-bayestraits-2jd7m3yv/BayesTraitsV4` was deleted after
  execution. Version probe and every inference returned zero.
- Python **3.11.16**, R **4.3.3**; locked integration pandas **2.2.3**,
  NumPy **2.4.6**.
- R packages: ape **5.8-1**, coda **0.19-4.1**, janitor **2.2.1**,
  posterior **1.6.0**, dplyr **1.1.4**, progress **1.2.3**,
  phangorn **2.12.1**, phytools **2.5.2**, ggplot2 **3.5.2**,
  ggtree **3.10.0**, ggsci **3.2.0**, base parallel **4.3.3**.

## Commands and retained evidence

From `/home/aaron/SPICE`:

```bash
MM=.local-ci/bootstrap/bin/micromamba
$MM run -p "$PWD/.local-ci/locked-env" python3 scripts/check_ci.py
$MM run -p "$PWD/.local-ci/locked-env" python -m pip install -r ci/requirements-build.txt
$MM run -p "$PWD/.local-ci/locked-env" python3 scripts/check_package.py --work-dir /tmp/spice-phase3-final-package
$MM create -y -p "$PWD/.local-ci/integration-env" -f ci/integration-environment.yml --strict-channel-priority
$MM create -y -p "$PWD/.local-ci/integration-locked-env" -f ci/integration-linux-64.lock
$MM run -p "$PWD/.local-ci/integration-locked-env" python scripts/check_integration.py --work-dir /tmp/spice-phase3-final-integration --repeat 3
.local-ci/bootstrap/actionlint .github/workflows/ci.yml .github/workflows/integration.yml
git diff --check
```

Work directories must be new; choose another suffix when reproducing.
The full exact subprocess argument arrays, exit codes and durations are in
`/tmp/spice-phase3-final-integration/result.json` and
`external tests with spaces/commands.json`. Each run retains tool/command logs,
QC attempt tables, ancestry, plasticity and runtime provenance. The original
baseline and subsequent validation logs use `/tmp/spice-phase3-*` names.
No environment, binary, cache or ad hoc inference output is tracked.

## Delivery and remaining hosted validation

The intended PR targets main and must not be merged by this task.
The PR description records final commit IDs, PR URL and actually observed
hosted statuses; local success does not establish hosted success.

The separate manual workflow is not required for merge. Read-only inspection
of the active Protect main ruleset confirmed that its only required context
remains **Phase 1 required checks**. No ruleset was changed.

A first workflow_dispatch needs the workflow registered on the default branch.
At implementation time only SPICE CI was registered; this new manual workflow
was absent from main. The agent must attempt branch dispatch and record the
actual response in the PR. If GitHub refuses it, maintainer registration is
required before hosted validation can finish; no push/PR trigger should be
added as a workaround. The normal PR gate must still be observed separately.

Recommended next step: review the feature PR and its required CI, resolve any
initial manual-workflow registration requirement, then run **Actions ->
SPICE Phase 3 Integration -> Run workflow** against the reviewed branch.
No scientific-method defect was established. Scientist-led biological validation
remains in maintainer-decisions.md. **Phase 4 has not started.**
