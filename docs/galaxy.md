# Galaxy integration

SPICE 0.2.0 is exposed through five native Galaxy tools, all versioned
`0.2.0+galaxy0` with profile `25.0`. This is an orchestration layer around the
installed CLI. Filtering, clone membership/rooting/selection, MCMC, QC/retries,
plasticity and BH correction remain in the existing Python/R package.

## Inputs, outputs and collection identity

| Tool | Inputs | Main outputs |
| --- | --- | --- |
| Filter | matrix.tsv, variants.tsv, cells.tsv; optional selected-cell list | filtered FASTA/CSV; cell and variant audit tables; runtime JSON |
| Clones | supported IQ-TREE Newick/NHX | assignment, rooting, branch-cut and selection tables; list of clone trees; runtime JSON |
| Ancestry | rooted clone tree; full states.tsv | ancestral probabilities; diagnostics, QC/attempts, state mapping, run settings and runtime JSON |
| Plasticity | same rooted tree; same states; matching ancestry; state_order.tsv | plasticity-test TSV, observed values/transitions, permutations, run settings and runtime JSON |
| Summarize | list of plasticity-test datasets | existing SPICE combined BH/FDR table and runtime JSON |

Filter accepts three ordinary datasets. Its job stages symlinks named exactly
`standard/matrix.tsv`, `standard/variants.tsv`, `standard/cells.tsv` and invokes
`spice filter --input_format standard`. Cell/variant audit tables describe the
selection before count filtering; the filtered CSV/FASTA describe the final
matrix. No archive upload or scientific output renaming is required.

Clones discovers SPICE's `Clone_N/Clone_N.nwk` exports as a list with identifiers
`Clone_N`; it does not recalculate membership. Galaxy maps Ancestry over that
list and Plasticity over the paired original-tree/ancestry lists. Keep both
lists in the same order with the same identifiers. The full states dataset is
shared across jobs: SPICE requires every tree tip and ignores extra cells.
Tree/state fingerprints and QC policy are checked by the CLI.
BayesTraits V4 cannot parse IQ-TREE internal support labels. SPICE omits this
metadata only from its temporary NEXUS subprocess copy; original input bytes,
supports, node identities, rooted topology and branch lengths are retained.
Fast invariance and real seeded-equivalence regressions cover Newick and NEXUS.

Summarize uses each collection element identifier literally as `clone_id` in a
job-local TSV manifest, constructed with Python's CSV writer. Blank, duplicate,
control-character or surrounding-whitespace identifiers fail clearly. Dataset
paths and user parameters travel in JSON to `os.execve`; user text is never
interpolated into a shell command. The adapter checks that both the executable
and import come from the active installed Conda prefix and logs those paths.

## IQ-TREE and Galaxy versions

The primary workflow is Filter -> IUC IQ-TREE -> Clones -> mapped Ancestry ->
paired mapped Plasticity -> Summarize. It does not call `spice phylogeny`.

Pinned Main Tool Shed dependency:

- owner: `iuc`; repository: `iqtree`
- changeset: `e727e82945af`
- tool: `toolshed.g2.bx.psu.edu/repos/iuc/iqtree/iqtree/2.4.0+galaxy2`
- executable requirement: `iqtree=2.4.0`; minimum Galaxy/profile: 25.0

The runner checks the Tool Shed's downloadable metadata before testing, and
Planemo installs the exact revision. IQ-TREE uses DNA, 1,000 SH-aLRT replicates,
1,000 UFBoot replicates and the supported `treefile` output, whose labels retain
SH-aLRT/UFBoot order. Model defaults to TEST; the small synthetic job explicitly
uses JC, a seed and one thread. The workflow explicitly sets model-selection
criterion BIC, matching the SPICE IQ-TREE 2.4.0 invocation; the IUC form otherwise
defaults to AIC. This follows IQ-TREE 2.4.0 `-h` and its
[model-selection reference](https://www.iqtree.org/doc/Command-Reference#automatic-model-selection).
IQ-TREE 3 has not been scientifically validated for SPICE and is deliberately
excluded.

The selected Galaxy release_25.0 source is pinned to
`ec10c792f94c6da0bc97b177f73be2a9287637dd` (version `25.0.5.dev0`).
Planemo is pinned to 0.75.47, gxformat2 to 0.27.0 and Mercurial to 7.2.4.
Galaxy bootstrap pip is pinned to 26.2.1. A build-only setuptools constraint
supplies `pkg_resources` for Galaxy's pinned rucio-clients dependency; it changes
no SPICE runtime dependency.

## BayesTraits administration

BayesTraits is external: an administrator must install a licensed executable
accessible to the Galaxy job runner through `BAYESTRAITS_BIN` or PATH. The tools
provide no executable-upload parameter. The SPICE Conda package, wheel, source
archive and OCI image do not include BayesTraits. A remote/container job runner
must explicitly propagate or mount the administrator's executable and its runtime
libraries; the local validation runner configures BAYESTRAITS_BIN explicitly on
its local Galaxy job destination; the server need not inherit its launcher
environment. A missing administrator executable is a hard test failure.

Manual tests acquire V4.1.3 only from the University of Reading URL already used
by the real integration suite. Archive SHA-256:
`cf0f5d9afa6ab74ae5aa6f386d1b3a4bc20d25643878aecddab459259b030674`.
Executable SHA-256:
`711024887c5484d5f6e768313b1aafea01c83705234e9a1172d5ed8e8f33bb4d`.
Hashes are verified before execution; temporary files are removed even on test
failure. Only explicitly named text/HTML/JSON/XML reports are uploaded.

## Local validation before Bioconda publication

Use Linux x86_64 with Git, network access, sufficient disk and the locked
[Phase 5 distribution toolchain](distribution.md). Create a separate Planemo
venv with that toolchain's Python 3.11, outside the source checkout:

```bash
python3 -m venv /tmp/spice-planemo
/tmp/spice-planemo/bin/python -m pip install -r ci/requirements-galaxy.txt
python3 scripts/check_galaxy.py --planemo /tmp/spice-planemo/bin/planemo \
  --work-dir /tmp/spice-galaxy-validation
```

The final command must use the distribution toolchain Python (or pass its prefix
with `--conda-prefix`). It builds the existing Phase 5 recipe, indexes an external
local channel, validates a fresh installation, checks package payload hashes
against this checkout, and resolves Galaxy requirements from
`file://<local-channel>,conda-forge,bioconda`. Nothing is uploaded. A matching
existing `check_distribution.py --conda-only` result may be passed through
`--distribution-result /path/result.json`; the package hash and production
payload are checked again. `--galaxy-root` accepts only the exact pinned commit.

The runner stages wrapper/workflow files outside Git, removes PYTHONPATH and
Python user-site leakage, prints versions/pins and runs:

```bash
planemo lint galaxy/tools
planemo shed_lint galaxy/tools
planemo workflow_lint galaxy/workflows/spice_lineage_analysis.ga
planemo test galaxy/tools
planemo test galaxy/workflows/spice_lineage_analysis.ga --extra_tools galaxy/tools
```

The runner supplies the required Galaxy and Conda options omitted from this
short command inventory. All six wrapper cases and the workflow must succeed;
missing tests, failures and skips are errors. `--lint-only` explicitly returns
an incomplete result. Retained `result.json` records exact commands, versions,
package identity, zero-skip counts and BayesTraits removal. It also records the
actual IQ-TREE 2.4.0 command and checks dataset IDs through each paired clone
job and into Summarize. Report files contain job stdout/stderr and runtime provenance for diagnosis. Never commit Galaxy's
database, histories, environments, caches, credentials or executable downloads.

The existing **SPICE Phase 3 Integration** Actions workflow remains manual-only
and non-required. Its `package_source` choice defaults to `local`; select
`public` for a fresh public Bioconda Galaxy installation on Ubuntu 24.04. It retains the real scientific integration job and adds an
independent Galaxy job. Normal PR CI only runs inexpensive static/default/
collection-manifest regressions and existing checks; its required status remains
**Phase 1 required checks**. See [engineering handoff](engineering-handoff.md)
for observed results and any outstanding acceptance gates.

## Public Bioconda validation

The default local regression path above is preserved. Select the separate public
path explicitly, using the same pinned Planemo/Galaxy toolchain:

```bash
/path/to/distribution-tools/bin/python scripts/check_galaxy.py \
  --package-source public \
  --planemo /path/to/planemo/bin/planemo \
  --conda-prefix /path/to/distribution-tools \
  --galaxy-root /path/to/pinned-galaxy \
  --work-dir /tmp/spice-public-galaxy-new
```

The work directory must be new. Public mode refuses `--distribution-result`,
downloads and checks the official Bioconda index/artifact and the immutable
release archive, bootstraps a fresh Conda root, and gives Galaxy an empty package
cache. Only `conda-forge,bioconda` are configured. Galaxy itself installs SPICE;
after each test suite the runner checks its actual Conda records, public URL,
SHA-256, downloaded cache archive, installed Python/R payload and IQ-TREE 2.4.0.
No package is built by this path. All six wrapper cases and the full workflow
must pass with zero skips; the existing scientific and collection checks remain.
BayesTraits is acquired temporarily, hash checked, and configured on the job
destination exactly as in local mode. The [dated validation record](public-distribution-validation-2026-10-19.md)
separates public Conda, container, Galaxy and Tool Shed outcomes.

## Test settings versus analysis settings

The XML defaults match the CLI's production defaults, checked by required tests.
The committed jobs explicitly use smaller synthetic integration settings:
2 chains, 50,000 iterations, 10,000 burn-in, sampling every 100, no observed
stepping stones and 3 permutations. Tests use relaxed explicit QC thresholds to
exercise orchestration on tiny synthetic trees. The small fixture also uses
manual clone cutoff 0.10, as in the existing real integration suite; it does not
meet the unchanged automatic stability criteria. Workflow/tool defaults remain
automatic selection with no manual cutoff. These demonstrate execution,
identity, provenance and failure gating, not biological validity or convergence
adequacy for real data. Production defaults are 3 chains, 1,000,000 iterations,
200,000 burn-in, sampling every 1,000 and 1,000 permutations; assess diagnostics
and scientific suitability for each study.

## Tool Shed readiness and later publication

`galaxy/tools/.shed.yml` defines `spice_lineage` under the intended Tool Shed
owner `diazlab`, with Phylogenetics metadata. SPICE **v0.2.0** is released with
version-specific DOI [10.5281/zenodo.22821665](https://doi.org/10.5281/zenodo.22821665).
The Galaxy wrappers are prepared for publication, but public Tool Shed deployment
has not occurred. Metadata, linting and local tarball generation do not publish
the tools. The tutorial remains a repository-local GTN-style draft, not an
official GTN contribution.

The Galaxy requirement remains `spice-lineage=0.2.0`.
[Bioconda PR #69381](https://github.com/bioconda/bioconda-recipes/pull/69381) merged
on 2026-10-18 Pacific. Public build `pyhdfd78af_0` passed an isolated Linux
installation with an empty cache on 2026-10-19. See the [public validation
record](public-distribution-validation-2026-10-19.md) for exact artifact identity,
Galaxy results and remaining gates. BayesTraits V4.1.3 remains external,
administrator-provided and not redistributed.

The [Test Tool Shed runbook](test-toolshed-publication.md) contains proposed
publication and validation commands. Do not execute its remote-write commands
until the remaining gates are resolved and the maintainer separately authorizes
publication. Tool Shed and GTN publication cannot be inferred from local tests.
