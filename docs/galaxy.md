# Galaxy integration (Phase 6 staging)

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
Tree/state fingerprints and QC policy are checked by the existing CLI.

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
uses JC, a seed and one thread. IQ-TREE 3 has not been scientifically validated
for SPICE and is deliberately excluded.

The selected Galaxy release_25.0 source is pinned to
`ec10c792f94c6da0bc97b177f73be2a9287637dd` (version `25.0.5.dev0`).
Planemo is pinned to 0.75.47, gxformat2 to 0.27.0 and Mercurial to 7.2.4.
Galaxy bootstrap pip is pinned to 26.2.1. A build-only setuptools constraint supplies `pkg_resources` for Galaxy's pinned
rucio-clients dependency; it changes no SPICE runtime dependency.

## BayesTraits administration

BayesTraits is external: an administrator must install a licensed executable
accessible to the Galaxy job runner through `BAYESTRAITS_BIN` or PATH. The tools
provide no executable-upload parameter. The SPICE Conda package, wheel, source
archive and OCI image do not include BayesTraits. A remote/container job runner
must explicitly propagate or mount the administrator's executable and its runtime
libraries; the local validation runner uses local Galaxy jobs.

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
package identity, zero-skip counts and BayesTraits removal. Report files contain
job stdout/stderr and runtime provenance for diagnosis. Never commit Galaxy's
database, histories, environments, caches, credentials or executable downloads.

The existing **SPICE Phase 3 Integration** Actions workflow remains manual-only
and non-required. It retains the real scientific integration job and adds an
independent Galaxy job. Normal PR CI only runs inexpensive static/default/
collection-manifest regressions and existing checks; its required status remains
**Phase 1 required checks**. See [engineering handoff](engineering-handoff.md)
for observed results and any outstanding acceptance gates.

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

## Staging and later publication

`galaxy/tools/.shed.yml` defines `spice_lineage` with Phylogenetics metadata.
A Tool Shed owner remains unset until maintainers establish one. Linting this
file does not publish it. The tutorial is a repository-local GTN-style draft,
not an official GTN contribution. No Tool Shed/GTN/Bioconda/PyPI/container upload
or release/tag is part of Phase 6.

After review and separate maintainer authorization: finalize the SPICE release
and immutable source archive/checksums; publish the approved Python distribution
and submit the recipe to Bioconda; validate the public package and corresponding
BioContainer; establish a Tool Shed owner and retest wrappers against public
Bioconda plus administrator-provided BayesTraits; submit/publish the reviewed
wrappers, pin the resulting tool IDs/revisions in the workflow, and rerun the
complete workflow on the target server; then adapt and submit the tutorial to
GTN through its review process. Publication requires separate decisions and
cannot be inferred from successful local staging tests.
