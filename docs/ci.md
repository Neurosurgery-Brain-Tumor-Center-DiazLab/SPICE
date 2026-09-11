# Phase 1 checks

The required GitHub job is **Phase 1 required checks** in **SPICE CI**.
An authorized maintainer should require that status check before merging, after
observing its first completed run. This repository change does not enable branch
protection. PRs, pushes to main, and manual dispatch run on clean Ubuntu 24.04
runners with read-only contents permission, no persisted checkout credentials,
no secrets, no shared environment cache, and a 30-minute timeout. No research
data or environment files are uploaded as artifacts.

## Reproduce locally

Run in Linux (including an Ubuntu WSL terminal), from this checkout. Install
micromamba separately; the tested bootstrap version is 2.3.2. No system R install
or administrator access is needed. The lock targets Linux x86_64.

```bash
micromamba create -y -p "$PWD/.local-ci/env" -f ci/linux-64.lock
micromamba run -p "$PWD/.local-ci/env" python3 scripts/check_ci.py
```

After activating any compatible isolated environment, the single check command is
`python3 scripts/check_ci.py`. All analysis fixtures are synthetic. Temporary
outputs, including paths containing spaces, are automatically removed.

The script fails if Python is older than 3.10, the host is not Linux, Rscript
or required R packages are missing, discovery finds no tests, any Python test
fails/errors/skips, an R assertion fails, or any CLI smoke check fails. It prints
discovered/run/skipped/failure/error counts and installed dependency versions.
The new example test deliberately has no optional-R skip decorator.

The required R packages are ape, coda, janitor, posterior >= 1.6.0, dplyr, progress,
and base parallel. Tree plotting packages, IQ-TREE, and BayesTraits are outside
this job's execution scope. CLI help/version do not establish their availability.

## Checks and scope

- Existing Python regression discovery: schema validation, duplicate variant
  handling, cell order/selection, input-route equivalence, QC option forwarding,
  provenance preservation, and clone-summary BH correction.
- Real RDS import/export and real R filtering for the standard and Monopogen
  fixtures, including comparison with the legacy merge/filter route.
- Checked-in `examples/standard` through the actual CLI, R bridge,
  `mutation_filter.R`, and Python FASTA converter. Fixture cutoffs are
  `--min_alt_cells_per_snv 2 --min_snvs_per_cell 1 --threads 1`;
  production defaults remain 5 and 5. Assertions cover the complete filtered
  count matrix, three ordered site IDs, three ordered cell IDs, exact FASTA
  sequences GGC/RRT/AAT, nonempty sidecars, PDF header, and successful provenance.
- Actual `Rscript --vanilla tests/test_mcmc_qc.R`: real diagnostics and parser/QC
  functions over synthetic draws and tables. Retry tests replace the MCMC runner;
  no BayesTraits chain is executed.
- Top-level help, version compared with VERSION, and help for every parser-defined
  subcommand (currently import-monopogen, filter, phylogeny, ancestry, plasticity,
  summarize).

The existing route forwarding test mocks IQ-TREE and BranchSupportCut.R, and the
release test uses a shell echo fixture. These are interface tests, not real tree
inference or clone classification. This job is not a full biological-pipeline test.

## Dependency maintenance

`ci/environment.yml` records the Phase 1 dependency intent. `ci/linux-64.lock`
records the resolved URLs and SHA-256 hashes for all 162 packages; CI installs
the lock, avoiding a fresh unconstrained solve on each PR. Actions are pinned
to verified commits and micromamba to 2.3.2-0. Versions are printed in job logs.

To deliberately refresh the lock, solve `ci/environment.yml` into a new isolated
prefix with strict conda-forge channel priority. Export using
`micromamba list -p PREFIX --explicit --sha256`, retain only package URL lines,
and precede them with `@EXPLICIT`. Check that every URL has its SHA-256 fragment.
Recreate another fresh prefix from that lock and run the required checks before
committing it. Do not include local paths, credentials, or private channels.

The previous general environment specified R 4.2 with Conda posterior >= 1.6,
which cannot solve: the available posterior 1.6.0 builds require R 4.3 or 4.4.
The installation target now uses R 4.3.3 and posterior 1.6.0. This retains the
observed posterior version and avoids upgrading all analysis dependencies.

R 4.3 pairs with Bioconductor 3.18 (R 4.2 paired with 3.16), per the
[Bioconductor release table](https://bioconductor.org/about/release-announcements/).
For the optional full plotting installation, use the Bioconductor release for
the active R version; do not force the current Bioconductor release into old R.
The existing BiocManager-based helper selects the matching release. The Phase 1
lock does not install ggtree or validate its plotting compatibility. A successful
solve of the general environment is not a successful full pipeline installation.

## Phase 2 package checks

The same **Phase 1 required checks** job retains its source/R checks and adds
`python -m pip install -r ci/requirements-build.txt` followed by
`python3 scripts/check_package.py`. No additional ruleset status-check name is
needed. No artifacts are published and no repository secrets are used.

The package checker builds wheel and sdist with an isolated backend, inspects
their complete contents, installs the wheel non-editably in a fresh external
venv, and checks actual R filtering, resource/version metadata, legacy equivalence,
and provenance outside Git. Python runtime dependencies in the wheel install
resolve within the declared compatible bounds; the source/R environment still
uses the unchanged Phase 1 lock. Build frontend tooling is pinned separately.
See [packaging.md](packaging.md) for commands and resource ownership.

## Phase 3 manual real-tool integration

**Actions -> SPICE Phase 3 Integration -> Run workflow** executes the full
IQ-TREE 2.4.0 / BayesTraits V4.1.3 suite through an external installed wheel.
It is manual only, is not required for PR merge, and does not change the
**Phase 1 required checks** job or any ruleset. Its separate 210-package
SHA-256 lock includes the plotting and real inference dependencies.

Local entry: `python3 scripts/check_integration.py` in the dedicated Linux
environment. Budget about 5–15 minutes including setup; success requires all
real-tool assertions and all three permutation smoke replicates, with zero
skips. Inspect the job log and the text-only `spice-integration-text-evidence`
artifact for commands, QC, provenance and failure details. No executable,
archive or wheel is uploaded. GitHub's initial default-branch workflow
registration requirement is documented with the dispatch instructions.

See [integration-testing.md](integration-testing.md) for exact installation,
official download checksums, test-only MCMC settings, fixture scope and logs.
Synthetic integration fixtures are not biological validation or a benchmark.
