# SPICE engineering handoff - Phase 4

## Starting state and mandatory gate

Checkout `/home/aaron/SPICE`, remote
`https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.git`.
Work started on clean `codex/phase4-clones-command` at fetched `origin/main`
**d93a164ea0250c5f8985753d9205f3e0ef34b64a**. Phase 3 is present and both hosted
checks were observed successful on that exact commit before any Phase 4 edits:

- [SPICE Phase 3 Integration, 34584742908](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34584742908).
- [SPICE CI, 34584009844](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34584009844).

No applicable AGENTS.md was found. No reset, stash, rebase, discarded local work,
main-branch commit, force push or merge is part of this phase. The Windows sandbox
helper failed to initialize; approved WSL commands performed the same scoped work.
The Phase 3 handoff remains available in Git at the starting main commit.

## Architecture and compatibility

`add_clone_options` registers the same thirteen reviewed options/defaults for
`phylogeny` and `clones`. `run_clone_classification` holds the single authoritative
Python validation, outgroup precedence and R dispatch path. `run_clones` checks
that its explicit tree is a readable file, then calls that function.
`run_phylogeny` retains filtering, alignment creation, model/replicate/thread
settings, IQ-TREE execution and its script output, then passes the actual
`<fasta_path>.treefile` from IQ-TREE's `-s` alignment to the same function.
The historical output/prefix FASTA layout remains supported; external FASTA
paths now follow the actual IQ-TREE output location.

```bash
spice clones --tree "/path/to/supported tree.treefile" \
  --output_directory /path/to/output --prefix SAMPLE
# Both entry points use the same main/parser:
python SPICE.py clones --tree "/path/to/supported tree.treefile" \
  --output_directory /path/to/output --prefix SAMPLE
```

The input contract is supported IQ-TREE Newick with **SH-aLRT/UFBoot** labels.
No NEXUS input converter or inference options are added. Missing/unreadable files
fail before R; scientific rooting/support/selection errors remain R's existing
errors. See [clones.md](clones.md) for every option/default and the full output
inventory traced before refactoring.

The R interface appends explicit tree path as **argument 16**. Arguments 1-15
retain their positions and default handling. Direct old invocations still derive
`<output_directory><sample_id>.fasta.treefile` if argument 16 is absent. Both
Python routes always provide the explicit path. The only executable R change is
that treefile assignment, plus two explanatory comments. All remaining bytes of
`BranchSupportCut.R` are unchanged, including support parsing, rooting, sweep,
ARI, stable-window and trusted-cluster definitions, automatic selection, minimum
size, clone membership/IDs, tree exports, plots and table schemas.

Provenance uses existing runtime JSON and source/environment hashing. Executable
paths/hashes describe discovery, not an executed-tool ledger. `clones` alone
omits the IQ-TREE version probe so it does not execute IQ-TREE even for metadata.
Other commands retain their provenance behavior. Success/failure, supplied tree
and clone parameters, installed source hashes and R metadata are tested.

## Validation design and pre-edit results

Mandatory baselines passed before edits:

- Phase 1: **21 tests**, zero skips/failures/errors; all real R QC/filter and CLI
  checks pass. Log `/tmp/spice-phase4-baseline-ci.log`.
- Phase 2: exact wheel/sdist content checks and **five** external installed-wheel
  tests pass. Evidence `/tmp/spice-phase4-baseline-package`.
- Real integration: **pass, zero skips, 121.10 seconds**, including real IQ-TREE
  2.4.0 / R / BayesTraits V4.1.3, ancestry, all three permutations, summary and
  expected failure paths. Evidence `/tmp/spice-phase4-baseline-integration`.

The new fast regressions cover registration and legacy help, required arguments,
prefix safety, unreadable/missing inputs, forbidden inference options, every
Phase 3 clone default, invalid selection/rooting values, outgroup precedence,
R argument order and paths with spaces, inference-first shared delegation, and
IQ-TREE failure isolation. A full `main()` subprocess whitelist includes runtime
capture and forbids any IQ-TREE invocation, including `--version`, for both
successful and failed clone analyses. Mocked routing tests do not establish
external-tool correctness.

The real installed-wheel runner now copies the inferred tree to
`external IQ-TREE input/renamed supported tree.nwk`, runs standalone clones in
`clones with spaces` with identical clone settings, then compares full parsed
rooting/selection/sweep tables and per-tip membership/trust/status. Clone names
are canonicalized by membership. Independent real R compares export counts,
tip sets, rooted topology, branch lengths and root edges in both Newick and
NEXUS. The input must be unmodified and the standalone output must lack inference
artifacts. PDF headers/layout are checked, not PDF bytes. An invalid IQTREE2_BIN
setting is ignored by clones; installed missing-file and scientific outgroup
failures produce failed provenance. All original ancestry/plasticity checks remain.

## Final local results

- Required source/R/CLI checks: **35 discovered/run, zero skips/failures/errors**.
  This includes fourteen new focused clone regressions and all prior tests.
  Evidence `/tmp/spice-phase4-reviewed-ci.log`.
- Package: **23 wheel files, 84 sdist files**, exact content checks and **five
  installed-wheel tests passed**. Evidence `/tmp/spice-phase4-reviewed-package`.
  Parser discovery exercised installed `spice clones --help` as well as every
  existing command; source checks exercised legacy `python SPICE.py clones` help.
- Full real integration: **pass, zero skips, 199.95 seconds**.
  Combined-versus-standalone complete tables, partition/trust/status, both tree
  formats, arbitrary filename/spaces, runtime success/failure, ancestry,
  plasticity, all three permutations and summary passed. Evidence
  `/tmp/spice-phase4-reviewed-integration/result.json`. Downloaded BayesTraits
  was verified removed after the run.
- Installed integration executable:
  `/tmp/spice-phase4-reviewed-integration/venv/bin/spice`.
  Import:
  `/tmp/spice-phase4-reviewed-integration/venv/lib/python3.11/site-packages/spice_lineage`.
  Wheel SHA-256: `91fa16d668368ba73203eb5093b7c31a80560e4bf85a94da934b793124c31870`.
- `git diff --check` and actionlint passed for both unchanged workflows. A direct
  parser comparison against the starting Phase 3 source confirmed all existing
  command flags, defaults, types, choices, help and requiredness are unchanged.
  An AST comparison confirmed the filtering/IQ-TREE body before clone dispatch
  is unchanged. Evidence `/tmp/spice-phase4-compatibility.json`.
- Byte comparison of the production R file confirms that only the explicit-tree
  assignment and its two comments differ from Phase 3. No scientific code change.

## Reproduce and delivery

From the checkout, using the existing locked environments:

```bash
.local-ci/bootstrap/bin/micromamba run -p "$PWD/.local-ci/locked-env" python3 scripts/check_ci.py
.local-ci/bootstrap/bin/micromamba run -p "$PWD/.local-ci/locked-env" python -m pip install -r ci/requirements-build.txt
.local-ci/bootstrap/bin/micromamba run -p "$PWD/.local-ci/locked-env" python3 scripts/check_package.py --work-dir /tmp/spice-phase4-reviewed-package
.local-ci/bootstrap/bin/micromamba run -p "$PWD/.local-ci/integration-locked-env" python3 scripts/check_integration.py --work-dir /tmp/spice-phase4-reviewed-integration
.local-ci/bootstrap/actionlint .github/workflows/ci.yml .github/workflows/integration.yml
git diff --check
```

Use new work-directory names on reruns. Generated artifacts and logs remain in
external temporary directories or ignored `.local-ci`; no binaries, environments,
IQ-TREE outputs, caches or PDFs should be staged. Package modules/resources stay
unchanged in count; test/docs glob allowlists include the new files without a
generic top-level scripts package.

The final PR records observed local/hosted results and commit IDs. The existing
**Phase 1 required checks** job name and normal PR workflow are unchanged.
**SPICE Phase 3 Integration** remains workflow_dispatch only and non-required.
Dispatch `integration.yml` on `codex/phase4-clones-command` after opening the PR,
and report only observed hosted results. Do not merge the PR.

Version remains **0.2.0 unreleased**, following the established changelog policy.
Scientific algorithms, defaults and output names/schemas are unchanged. Phase 4
includes no Galaxy XML, Planemo workflow, Tool Shed work, Bioconda/container/PyPI
publication or Phase 5 work. Review the Phase 4 PR and its real equivalence
results before separately authorizing later publication and Galaxy phases.
