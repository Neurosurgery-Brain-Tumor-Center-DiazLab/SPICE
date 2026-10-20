# SPICE v0.2.0 public distribution and Galaxy prepublication validation

Date: **2026-10-19, America/Los_Angeles** (evidence timestamps use UTC).
Evidence root: `/tmp/spice-public-validation-20261019` on this Linux host.
No publication command was executed. This report does not authorize publication.

## Release and branch identity

- Repository: https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE
- Feature branch: `codex/public-bioconda-galaxy-v0.2.0`.
- Base/current remote main at validation: `bddd180bc1e201d648dd7093d55544bdebe6d0c4`.
- Initial clean local main was `495bfdb9b8d47a9fa7a1a65dd5477ecc95dd9969`;
  remote main was fetched before creating the feature branch.
- Immutable annotated `v0.2.0` tag object: `b58b44c4630287ef36314a6f56de690ea00ec8b6`.
- Dereferenced release commit: `5ebc4aec5df7df6c2e9cdb60c1259a2898e3e19f`.
- Release archive SHA-256:
  `48d67b1e5300203d5ce953f2bea25b958772d1887ed8ad1b83f31ce6ced71236`.
- [Bioconda PR #69381](https://github.com/bioconda/bioconda-recipes/pull/69381)
  merged at `2026-10-19T03:19:10Z` (October 18 Pacific), merge commit
  `10d7cc5d1b8a41e757c7e51a18b843627440d24d`.

`git-state.json`, `release-tag.response`, `bioconda-pr.json` and
`merged-recipe.response` retain the independent remote checks. The downloaded
release archive checksum matches the merged upstream recipe. The recipe itself
was not edited.

## Public Bioconda — PASS

Indexed **YES**; fresh installation **PASS**; smoke/functional checks **PASS**,
zero skips. This is an independently downloaded public package, not the local
build used in earlier Galaxy validation.

| Identity | Verified value |
| --- | --- |
| Name/version | `spice-lineage=0.2.0` |
| Build / build number | `pyhdfd78af_0` / `0` |
| Subdirectory / type | `noarch` / Python |
| Filename | `spice-lineage-0.2.0-pyhdfd78af_0.conda` |
| Public artifact | [spice-lineage-0.2.0-pyhdfd78af_0.conda](https://conda.anaconda.org/bioconda/noarch/spice-lineage-0.2.0-pyhdfd78af_0.conda) |
| SHA-256 | `42c1adce162effda9eb151c3f7ba87bd0a0dd23111f8d6f21f16f10e7bd42974` |
| Anaconda upload time | `2026-10-19 03:21:37.399000+00:00` |

The [Anaconda API](https://api.anaconda.org/package/bioconda/spice-lineage),
[official noarch index](https://conda.anaconda.org/bioconda/noarch/repodata.json.bz2),
independent artifact download, empty-cache Conda download and actual installed
`conda-meta` record agree on package identity and SHA-256.

Installation used Conda **26.7.2**, Linux x86_64 on WSL, a new prefix
`public-runtime`, new HOME and empty `package-cache` under the evidence root:

```bash
conda create --yes --prefix /tmp/spice-public-validation-20261019/public-runtime \
  --override-channels --strict-channel-priority \
  -c conda-forge -c bioconda 'spice-lineage=0.2.0'
```

`install-command.json` records the exact absolute executable, complete isolated
environment, OS, timestamp, `cache_initial_entries: []` and
`prefix_existed: false`. `install.log` and `install-exit.json` record completion.
All **201** installed package records come from public conda-forge or bioconda;
`public-runtime-explicit.log` is the complete URL/SHA-256 package export.
No Python version override or scientific dependency change was made to obtain
this solve. The actual resolved dependency versions include:

| Package | Version | Build |
| --- | --- | --- |
| python | 3.14.8 | hcd007b5_101_cp314 |
| pandas | 2.3.3 | py314ha0b5721_2 |
| numpy | 2.5.4 | py314hd3a7d6b_0 |
| r-base | 4.3.3 | hc28aa72_21 |
| r-ape | 5.8_1 | r43h3704496_1 |
| r-coda | 0.19_4.1 | r43hc72bb7e_1 |
| r-janitor | 2.2.1 | r43hc72bb7e_0 |
| r-posterior | 1.6.1 | r43hc72bb7e_0 |
| r-dplyr | 1.1.4 | r43h0d4f4ea_1 |
| r-progress | 1.2.3 | r43hc72bb7e_1 |
| r-phangorn | 2.12.1 | r43h9124c8a_2 |
| r-phytools | 2.5_2 | r43hc72bb7e_0 |
| r-ggplot2 | 3.5.2 | r43hc72bb7e_0 |
| r-ggsci | 3.2.0 | r43hc72bb7e_1 |
| bioconductor-ggtree | 3.10.0 | r43hdfd78af_0 |
| iqtree | 2.4.0 | h503566f_0 |

The independent smoke driver `phase1.py` and its exact commands are retained.
It runs outside Git with a clean environment, PYTHONPATH absent and Python user
site disabled. `phase1-result.json` records these successful checks:

- Installed console version/help and help for all seven subcommands:
  `import-monopogen`, `filter`, `phylogeny`, `clones`, `ancestry`, `plasticity`,
  `summarize`; installed Python import and pandas/numpy imports.
- All seven R resources and all eleven required R namespaces; R **4.3.3**.
- Actual `iqtree2 --version`: **2.4.0**, matching the installed package record.
- Every installed Python/R/version payload hash equals the immutable release.
  The downloaded Conda payload also passes the existing package allowlist,
  console-entry-point and license checks against that release.
- The release's own functional checks: standard-input filtering, supported-tree
  clone discovery, real IQ-TREE phylogeny, three-clone partition, tree exports,
  standalone/combined clone equivalence, unchanged inputs and runtime source/
  executable provenance. Negative ancestry testing fails clearly without
  BayesTraits and does not attempt inference.
- BayesTraits is absent from the Conda package/environment; it remains external.

Detailed evidence: `phase1-artifact/artifact.json`, retained API/index/archive,
`phase1-artifact/inspection/package-files.json`, `phase1-installed/`,
`public-release-checks.log`, `release-checks/output with spaces/`, and
`python-dependencies.log`. Historical source validation used Python 3.11; this
independent public solve used Python 3.14.8, with no claim about other platforms.

## Public BioContainer — INCOMPLETE / NO-GO gate

No anonymously accessible public `biocontainers/spice-lineage` image was found.
**Exact tag: unavailable. Digest: unavailable. Pull: NOT RUN. Execution: NOT RUN.**
No tag was invented, and no locally built image was substituted.

- Quay repository/tag API and anonymous registry-v2 token/tag requests returned
  HTTP **401**. This cannot distinguish a private repository from a nonexistent
  one; it does not establish a publicly pullable image.
- [Quay search](https://quay.io/api/v1/find/repositories?query=spice-lineage)
  returned HTTP 200 with `results: []`, `has_additional: false`.
- A known public `biocontainers/iqtree` tag API returned HTTP 200, confirming
  public Quay access worked. Its current tags were only a service-access control;
  no IQ-TREE 3 dependency was used or selected for SPICE.
- The BioContainers TRS API hostname failed DNS resolution on this host.
- Docker, Podman, Skopeo, Singularity and Apptainer were absent on this WSL host.
  A publicly discoverable tag/digest and a capable runtime remain required for
  the image pull/execution gate. BayesTraits must remain external there too.

Evidence: `quay-*.response`, `quay-*.http.json`, `quay-iqtree-control.json`,
`public-preflight.json`, `container-runtime.json`. The Quay HTML page's HTTP 200
is only a generic application shell and is not evidence of an existing image.

## Galaxy public-package validation

The first hosted public run **passed** all **six wrapper cases** and the **one
full workflow**, with **zero skips**, at commit
`458ab862f7a0c8326fcc2ea2adec9396d2e4626f` in
[run 39354962350](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/39354962350).
The public URL/build/SHA-256 and release payload were verified from Galaxy's
actual installed Conda records after both suites; its fresh cache contained the
same downloaded archive. The real IQ-TREE/BayesTraits integration job also passed.

A post-test log audit found directory registration repeatedly treating
`macros.xml` as a standalone tool (134,935 failed load messages). This did not
fail any required test, but produced an unnecessarily large log. Public mode now
registers the five wrapper XML files explicitly; a fresh hosted rerun is being
prepared for that validation-only correction. Local mode is unchanged.

The initial WSL1 attempt failed during input uploads before any SPICE job or
public SPICE installation: Galaxy's hard-coded Celery `forkserver` could not
reconstruct an AF_UNIX socket (`OSError: [Errno 22] Invalid argument`, then
`EOFError`). It was stopped with SIGINT. Temporary BayesTraits cleanup succeeded.
Its failure logs remain in `galaxy-public/`; no WSL workaround patched Galaxy.

The existing local-package validation remains the default, including its local
artifact checksum, payload and actual local Conda origin checks.
`--package-source public` is a separate path; it rejects reused local
`--distribution-result`, bootstraps an isolated Conda root/cache, resolves only
`conda-forge,bioconda`, and checks actual Galaxy-installed records after each
suite. The public artifact is independently checked against the official index
and immutable source before execution. Its downloaded cache file must match
as well. New tests reject wrong artifact identity, local dependency sources,
installed-source drift, IQ-TREE/R drift, missing records, incomplete case counts
and unsuccessful/skipped Galaxy cases.

Pins are preserved: wrappers `0.2.0+galaxy0`, Galaxy profile `25.0`, Galaxy commit
`ec10c792f94c6da0bc97b177f73be2a9287637dd` (`25.0.5.dev0`), Planemo `0.75.47`,
IUC IQ-TREE changeset `e727e82945af`, tool `2.4.0+galaxy2`, scientific executable
`2.4.0`, and external BayesTraits `V4.1.3`. Workflow scientific parameters and
production defaults are unchanged. The existing reduced synthetic tests do not
establish biological validity or recommended study settings.

## Tool Shed preparation — local PASS; publication stopped

Final `planemo lint`, `shed_lint`, `workflow_lint` and local `shed_build` all
returned **0**. Evidence: `shed-review.json` and `review-*.log`.

- Owner/repository: **diazlab/spice_lineage**; category **Phylogenetics**.
- Five wrapper IDs, versions and profiles lint successfully; six cases total.
- Each wrapper includes the shared SPICE citation. DOI
  [10.5281/zenodo.22821665](https://doi.org/10.5281/zenodo.22821665) independently
  resolves to SPICE v0.2.0 by Bohyeon Yu and Aaron Diaz (`citation-metadata.json`).
- Conda dependency remains `spice-lineage=0.2.0` in `macros.xml`. No legacy
  `tool_dependencies.xml` is needed. IQ-TREE is a separate workflow dependency
  pinned in `galaxy/workflows/tools.yml`, not an extra tool bundled in this shed.
- BayesTraits licensing/acquisition and administrator job-environment requirements
  are explicit in the README, macros/help and Galaxy administration guide.
- Test and Main Tool Shed read-only queries returned **[]** for
  `diazlab/spice_lineage`. Test `diazlab` repository enumeration also returned
  **[]**. These establish no visible repository, not account identity or ownership.
- The signed-in Test account is **UNVERIFIED** because browser initialization
  failed. Do not assume Main and Test account credentials are interchangeable.

Reviewed archive:
`/tmp/spice-public-validation-20261019/shed-review/galaxy/tools.tar.gz`

SHA-256:
`125a5180889a14186117a5e89235b8288da67e95abef3a0cb2d9804c952d19bc`

Its **31 regular files** exactly match staged source bytes: five XML wrappers,
`macros.xml`, `run_spice.py`, `README.rst`, and 23 synthetic-data/readme files.
Every member path/size/hash is in `shed-archive-inspection.json`. No archive
member is a symlink, native executable, dependency cache, credential/config
secret or temporary download. `.shed.yml` remains external publication metadata,
as expected for Planemo; the workflow is not bundled into the five-tool archive.

The [proposed publication runbook](test-toolshed-publication.md) uses explicit
Test Tool Shed URLs, separate initial-create versus existing-repository paths,
the reviewed tarball, observed post-upload IDs/revision, a fresh Galaxy
`shed_test` installation, public package provenance checks and the full workflow.
Only help/local commands were exercised. No `shed_create`, `shed_upload`,
`shed_update`, remote publish control or Tool Shed write API was executed.

## Failures and recovery

- The sandbox execution helper failed before starting commands. Host execution
  was approved and used for Linux work. The browser still failed to initialize;
  Test Tool Shed signed-in account identity remains unresolved.
- The first focused unit invocation used the distribution-build toolchain,
  which lacks pandas; two test modules could not import. Re-running with the
  newly installed public runtime passed all **19** focused tests. This did not
  require dependency-bound or scientific-code changes.
- Initial archive staging at `shed-stage/tools` triggered shed lint's URL/path
  heuristic. The configured source URL was correct. Staging at
  `shed-review/galaxy/tools` preserved the repository layout and all final lint
  checks passed without suppressing warnings or changing source metadata URLs.
- WSL Galaxy startup also logged missing optional visualization data tables and
  a data-manager watcher `None` path exception. The blocking failure was the
  Celery upload forkserver socket error; no scientific settings were changed.
- Container registry/DNS/runtime limitations above remain unresolved.

The repository required runner `scripts/check_ci.py` also passed using the public
runtime: `Python: discovered=54 run=54 skipped=0 failures=0 errors=0`. R QC tests
and all CLI help/version checks passed. Full log: `required-checks.log`; exit
record: `required-checks-exit.json`.

## Change and publication boundaries

Changed validation: `scripts/check_galaxy.py` adds the public choice while
preserving local default; `scripts/check_public_distribution.py` checks public
provenance/release payload; `tests/test_public_distribution.py` adds seven
failure-gate regressions; `.github/workflows/integration.yml` adds a manual
`package_source` choice (default `local`) and public text-evidence allowlist.

Changed documentation/metadata: `README.md`, `docs/distribution.md`,
`docs/galaxy.md`, `docs/integration-testing.md`, this report,
`docs/test-toolshed-publication.md`, `galaxy/README.md`,
`galaxy/tools/.shed.yml`, `galaxy/tools/README.rst`,
`packaging/bioconda/README.md`, `packaging/bioconda/spice-lineage/README.md`,
`wiki/Galaxy.md`, `wiki/Installation.md`. No wrapper scientific XML changed.

The immutable tag, scientific Python/R payload, algorithms, QC thresholds,
scientific defaults, workflow scientific settings, IUC revision, Bioconda
recipe/public package, Zenodo record and both Tool Sheds were untouched.
Temporary BayesTraits handling is reported with the Galaxy outcome above.
No GitHub PR has been created. The feature branch was pushed solely to dispatch
the isolated hosted validation run. Main and the release tag were not updated.

## Recommendation

**NO-GO pending the required hosted Galaxy result**, public BioContainer
verification and Test Tool Shed account confirmation. The verified public
Conda package and local lint/archive preparation pass independently. Stop
before any Test Tool Shed creation/upload and obtain separate explicit
maintainer authorization after reviewing the completed evidence.
