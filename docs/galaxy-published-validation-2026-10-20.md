# Published Test Tool Shed validation — 2026-10-20 UTC

**GO for continued evaluation of published revision `5132fb8a542e`.** All six
wrapper tests and the complete synthetic workflow passed with zero failures
and zero skips on hosted Ubuntu 24.04. This result uses the documented Planemo
0.75.47 compatibility adapter below; unadapted Planemo encountered two harness
defects. This assessment does not authorize Main Tool Shed publication or GTN
submission.

Accepted run: [39378220823](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/39378220823).
Validated implementation: `c18889fe662580fca73bf9fa434c3a7bb45f7146`, on
`codex/validate-published-testshed-v0.2.0`, based on main
`6b5f69815d8a9b77b0f494ab9fd2430e3cc44a1a`.

## Results

| Check | Observed result |
| --- | --- |
| Published wrapper tests | 6/6 passed; 0 failures; 0 skips |
| Complete workflow | 1/1 passed; 0 failures; 0 skips |
| Installed published revision | Five GUIDs at `5132fb8a542e` in both Galaxy instances |
| Published and installed payload | All 31 reviewed file sizes and SHA-256 values match |
| Public-package executions | 6 wrapper jobs + 9 workflow SPICE jobs, all using the installed public package |
| Clone mapping | `Clone_1`, `Clone_2`, `Clone_3`; 3 ancestry and 3 correctly paired plasticity jobs |
| External BayesTraits | V4.1.3 inference banners and binary hash verified in 2 wrapper jobs + 6 workflow jobs; temporary binary removed |
| Separate real-tool integration job | Passed |
| Offline checks | 63 tests passed, 0 skips; actionlint and diff checks passed |

The retained summary has three successful rows. For each synthetic clone,
observed plasticity is `0`, empirical p is `1`, q is `1.0`, and significance is
`False`, with three planned tests and alternative `greater`. Each mapped
plasticity test completed all three requested permutations. Eleven actual
clone assignment, ancestry/QC, plasticity and summary tables are retained;
their dataset UUIDs and file hashes were checked after download.

## Published identity and payload

- Server: https://testtoolshed.g2.bx.psu.edu
- Owner/repository: `diazlab/spice_lineage`; repository ID `34b0910123274f01`.
- Changeset: `5132fb8a542e`; full Mercurial node `5132fb8a542e93ebecfca1a2bb9628c02b96137a`.
- Public metadata before and after execution: downloadable, five valid tools,
  all six tests present, and the expected revision still latest.

The observed GUID prefix is
`testtoolshed.g2.bx.psu.edu/repos/diazlab/spice_lineage/`:

| Tool | GUID suffix | Tests |
| --- | --- | ---: |
| Filter | `spice_filter/0.2.0+galaxy0` | 1 |
| Clones | `spice_clones/0.2.0+galaxy0` | 1 |
| Ancestry | `spice_ancestry/0.2.0+galaxy0` | 1 |
| Plasticity | `spice_plasticity/0.2.0+galaxy0` | 2 |
| Summarize | `spice_summarize/0.2.0+galaxy0` | 1 |

All five specify Galaxy profile `25.0`, require the Conda package
`spice-lineage=0.2.0`, and expand the shared Yu/Diaz software citation for
version 0.2.0, DOI `10.5281/zenodo.22821665`.

The original 31-file archive was rehashed as
`125a5180889a14186117a5e89235b8288da67e95abef3a0cb2d9804c952d19bc`.
An anonymous Mercurial clone of the published node matched every intended
file in [the reviewed archive manifest](../tests/galaxy/reviewed-toolshed-archive.json),
with no additional payload files. The `.hg` transport directory is excluded.
Both Galaxy installations independently matched the same manifest.

## Environment and provenance

Planemo is `0.75.47`; Galaxy source is
`ec10c792f94c6da0bc97b177f73be2a9287637dd`, with profile 25.0 and server Python
3.11. GitHub job metadata confirms `ubuntu-24.04`. The wrapper phase invokes
Planemo `shed_test` against the published repository, followed by a separate
Galaxy instance for the workflow. No local wrapper substitute is provided.

The disposable workflow changes only the five SPICE identifiers and adds their
published repository revision. An inverse comparison proves that all parameters,
connections and other steps remain unchanged. IUC IQ-TREE remains
`2.4.0+galaxy2`, revision `e727e82945af`; its job executed IQ-TREE `2.4.0` with
the existing JC/DNA, SH-aLRT 1000 and ultrafast-bootstrap 1000 settings.

Galaxy installed the official public artifact
[spice-lineage-0.2.0-pyhdfd78af_0.conda](https://conda.anaconda.org/bioconda/noarch/spice-lineage-0.2.0-pyhdfd78af_0.conda),
SHA-256 `42c1adce162effda9eb151c3f7ba87bd0a0dd23111f8d6f21f16f10e7bd42974`.
The isolated Conda root began with an empty package cache and used only
`conda-forge` and `bioconda`. Installed metadata, cached artifact bytes,
immutable release payload and all 15 per-job execution markers agree.
The 201-package runtime includes Python `3.14.8`, R `4.3.3` and IQ-TREE `2.4.0`;
full package records are retained for both validation phases.

BayesTraits remains external V4.1.3, with binary SHA-256
`711024887c5484d5f6e768313b1aafea01c83705234e9a1172d5ed8e8f33bb4d`.
Eight retained inference runtime records contain the actual execution banner
`BayesTraits V4.1.3 (Sep 27 2024)`. The executable was removed after testing and
is absent from retained artifacts.

## Failures and compatibility limitations

- HTTP revision archive URLs returned 403; the legacy download endpoint returned
  404. Anonymous Mercurial retrieval of the exact published node succeeded.
- [Run 39376813691](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/39376813691)
  failed before wrapper execution with `Invalid URL scheme: b''`. Planemo
  generated a Main-only Shed registry because registry discovery inspects
  workflow runnables, while `shed_test` supplies tool runnables.
- [Run 39377498127](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/39377498127)
  installed and ran published tools but reported only five successful cases.
  The validator rejected it. Planemo expands five placeholders into six cases,
  then pairs responses with the original five placeholders, truncating the
  final report.
- [The adapter](../scripts/planemo_published.py) registers Test Tool Shed and
  pairs every actual expanded case with its unchanged response, checking count
  and identity. It leaves published tests, assertions and outcomes unchanged.
  A regression test proves that a failing sixth result stays a failure. No
  installed Planemo files or pinned Galaxy source files are patched. The
  accepted run records the adapter hash.
- Planemo's workflow `tool_ids` linter queries Main Tool Shed even for Test
  Tool Shed IDs. Only that lookup is excluded and replaced by direct metadata,
  installed revision and GUID checks. Structural lint uses `--fail_level error`
  for expected Test Tool Shed best-practice warnings. No execution test is skipped.
- Local preflight corrected profile-token expansion and Python 3.11 syntax in
  the new validator. Initial offline invocations used a build environment without pandas or
  omitted Rscript from PATH; the public Python/R environment passed all 63 tests. These
  corrections did not require scientific or published-wrapper changes.

## Reproduction and retained evidence

Dispatch `integration.yml` on the validation branch with
`package_source=published`, or run on fresh Linux x86_64 using the bootstrap
lock `ci/distribution-linux-64.lock` and `ci/requirements-galaxy.txt`:

```bash
python scripts/check_published_galaxy.py \
  --planemo /absolute/path/to/planemo/bin/planemo \
  --conda-prefix /absolute/path/to/distribution-toolchain \
  --work-dir /absolute/new/evidence-directory
```

The evidence directory must be new and outside Git. `--metadata-only` explicitly
reports an incomplete result and cannot establish execution success.

The accepted run's `spice-galaxy-text-evidence` ZIP has SHA-256
`3a0b05638e4c02007e8128dcca3939675fca6079cf6bd1a852c5ab1111a7a9b9`;
the downloaded ZIP was checked against GitHub's artifact digest. It contains
structured reports, logs, public metadata, installed revision records, Conda
metadata, per-job provenance, runtime records, the disposable workflow and
actual result tables. GitHub retention is 14 days. Downloaded evidence for all
three attempts, the published payload and offline checks is also retained in
`.local-ci/published-testshed-5132fb8a542e/` in the local checkout.

Changes are limited to the manual CI workflow, the new published validator and
Planemo adapter, archive manifest, offline tests and this report. Existing local
and public package validation paths remain intact. Scientific code, parameters,
original wrappers/workflow and the immutable `v0.2.0` tag are unchanged. No user
API key was requested or read, no Tool Shed was uploaded or updated, no PR was
merged, and no Main Tool Shed publication or GTN submission was performed.

Validation is complete. Any later publication or merge remains a separate
authorization decision.
