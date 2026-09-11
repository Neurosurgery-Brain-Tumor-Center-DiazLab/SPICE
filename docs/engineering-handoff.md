# SPICE engineering handoff

## Phase 2 scope and starting state

Phase 2 implements an installable local distribution and preserves scientific
behavior. Stop after this phase; Phase 3 inference/integration fixtures have not
been started. The earlier Phase 1 handoff remains in Git history at `fddbe03`.

Working checkout: `/home/aaron/SPICE`, branch `codex/phase2-package`, remote
`https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.git`.
Before editing, pwd, status, branch and remotes were checked and origin fetched.
HEAD and current origin/main both resolved to
`fddbe03344359bec3385f7ffcde23ad20e420824`; the working tree was clean.
No reset, stash, discarded work or main-branch commit was used.
No applicable AGENTS.md was found.

## Architecture and changed files

- `pyproject.toml`: setuptools PEP 517/518/621 build, distribution
  `spice-lineage`, Python >=3.10, runtime dependency `pandas>=1.5,<3`,
  GPL-3.0-only and original citation/author metadata, `spice` console entry.
- `SPICE.py`: thin wrapper importing the same `spice_lineage.cli.main` used by
  the installed console entry; legacy source-checkout commands still work.
- Move CLI and six Python helpers into `spice_lineage/`. Add `__init__.py`,
  `paths.py` and packaged `VERSION`. Package version, checkout VERSION,
  citation version, distribution metadata and CLI output are checked for agreement.
- Move seven active R files to `spice_lineage/resources/r/`, with no byte changes:
  matrix_bridge.R, mutation_filter.R, BranchSupportCut.R, ancestry_core.R,
  plasticity_core.R, spice_ancestry_utils.R, spice_plasticity_utils.R.
- `runtime_info.py`: hash installed package files, report their source root,
  verify the SPICE checkout before probing Git, and ignore unrelated Git
  environment overrides. Missing Git is explicitly unavailable.
- `MANIFEST.in`: constrained source distribution with tests, synthetic example,
  docs and required development helpers. The wheel contains only the package,
  active R resources, version, license/citation and distribution metadata.
  Other legacy analysis scripts remain unchanged in the Git checkout.
- `scripts/check_package.py`, `tests/installed_checks.py`,
  `tests/test_package.py`, and `tests/standard_example.py`: build/artifact,
  installation, metadata/resource, provenance and scientific equivalence checks.
  Existing test imports/resource paths were migrated; behavioral assertions
  were retained. The Phase 1 example assertions are shared with the wheel test.
- `.github/workflows/ci.yml`: keep **Phase 1 required checks**, then add build
  tooling and the package checker. `ci/requirements-build.txt` pins build 1.4.0.
  The existing Phase 1 lock and check script are unchanged.
- README, CHANGELOG, docs/ci.md, docs/packaging.md and this handoff describe local
  installation, external dependencies, observed tests and scope. `.gitignore`
  excludes local build/venv metadata.

## Scientific code review

All seven moved R files and four moved Python scientific helpers
(standard_input.py, convert_matrix_to_fasta.py, IQTREE2.py, summarize_clones.py)
were compared against the starting commit and are byte-for-byte identical.
The Monopogen importer only changes the R bridge resource lookup/import.
The CLI changes package imports/resource resolution, the usage program name,
the missing-resource message, and stops forcing R subprocesses into the source
directory; its input/output paths are already absolute. Five inherited trailing
whitespace lines in the moved CLI were trimmed to satisfy diff-check; its AST
was verified unchanged by that whitespace-only edit. Provenance changes are
limited to version/source/Git metadata handling.

No filtering order, count interpretation, FASTA mapping, site multiplicity,
IQ-TREE model/support defaults, clone algorithm/rooting, MCMC settings/QC,
state-order semantics, transitions, permutations, empirical P values, BH
correction, scientific tables or overwrite policies were changed.
No new scientific defect or maintainer decision was identified.

## Observed local validation

Executed on Ubuntu 20.04 LTS under WSL1, Linux x86_64, glibc 2.31.
Windows PowerShell invoked WSL explicitly because the native Windows workspace
process helper could not launch reliably. No system environment was modified.

The existing isolated `.local-ci/locked-env` supplies Python 3.11.16,
pandas 2.2.3, NumPy 2.4.6 and R 4.3.3; R packages include ape 5.8-1,
coda 0.19-4.1, janitor 2.2.1, posterior 1.6.0, dplyr 1.1.4 and progress 1.2.3.
Build 1.4.0 was added as development tooling. The fresh wheel venv independently
resolved pandas 2.3.3 and NumPy 2.4.6 within runtime metadata bounds.

Commands from the checkout (MM abbreviates the existing bootstrap executable):

```bash
MM=.local-ci/bootstrap/bin/micromamba
$MM run -p "$PWD/.local-ci/locked-env" python3 scripts/check_ci.py
$MM run -p "$PWD/.local-ci/locked-env" python -m pip install -r ci/requirements-build.txt
$MM run -p "$PWD/.local-ci/locked-env" python3 scripts/check_package.py --work-dir /tmp/spice-phase2-package-check
# Final artifact/documentation verification uses a second new external directory:
$MM run -p "$PWD/.local-ci/locked-env" python3 scripts/check_package.py --work-dir /tmp/spice-phase2-final-r1
.local-ci/bootstrap/actionlint .github/workflows/ci.yml
git diff --check
```

Before edits, Phase 1 passed: 17 discovered/run, 0 skipped, failures or errors;
all real R QC assertions and top-level/six-subcommand help/version checks passed.
After refactoring, source checks passed: 21 discovered/run, 0 skipped, failures
or errors, plus the same R QC and CLI checks. Five installed-wheel tests passed.
The exact generated build command is `python -m build --outdir EXTERNAL/dist ROOT`;
its default path builds an sdist and then a wheel from that sdist, using isolated
backend environments. The checker installs the wheel with ordinary pip in a
fresh non-editable venv, unsets PYTHONPATH, runs `pip check`, and executes copied
tests from a neutral directory. Artifact checks verify complete file allowlists
and source bytes, excluding Git, environments, caches, logs and unrelated data.

Artifacts: `spice_lineage-0.2.0-py3-none-any.whl` and
`spice_lineage-0.2.0.tar.gz`. The wheel has 24 files, including all seven active
R resources; the sdist includes the package and bounded development material.
Local artifacts and review evidence are retained under
`/tmp/spice-phase2-final-r1/` (initial validation: `/tmp/spice-phase2-package-check/`).
Builds/logs/environments are not committed.

The initial non-editable import was verified at
`/tmp/spice-phase2-package-check/venv/lib/python3.11/site-packages/spice_lineage/__init__.py`;
the final install uses the corresponding path under `/tmp/spice-phase2-final-r1/`.
No top-level `scripts` or `SPICE` module is installed. Console entry metadata
loads the exact same main function as the package CLI.

The real standard filter uses only copied synthetic examples, the wheel and the
external R runtime/packages, with cutoffs 2/1 and one thread. It retains ordered
cells Ref, cell-2, cell_3 and ordered sites chr1:10:A:G, chr1:20:A:G, chr2:30:C:T.
The complete filtered count matrix, FASTA sequences GGC/RRT/AAT, required sidecars,
PDF header and runtime success are asserted. Scientific filter files and summary
tables match the legacy wrapper; summary overwrite protection is retained.

Installed runtime JSON records version 0.2.0, SHA-256 for all packaged Python/R
sources and VERSION, successful R provenance and explicit Git unavailability.
Tests also run inside an unrelated Git directory with ambient Git overrides.
Source-checkout association is tested separately.

## Delivery and remaining scope

The feature branch is intended for a PR against main, without merging.
`docs/phase2-pr.md` is the ready-to-use PR description. Inspect focused commits
with `git log fddbe03..HEAD` and the complete change with `git diff fddbe03..HEAD`.
Hosted CI status must be read from the PR; local checks alone do not establish
hosted success. The exact required status-check name remains
**Phase 1 required checks**; no new ruleset check is needed.

R and R packages, IQ-TREE and BayesTraits remain external. No real IQ-TREE or
BayesTraits inference, plotting/clone integration, biological validation,
benchmarks, standalone clone command, registry/container publication or Galaxy
work was performed. No PyPI/Bioconda publication or name reservation is claimed.
Scientist-led gates remain in maintainer-decisions.md.

Recommended next step: review the Phase 2 PR and its hosted required check.
Phase 3 requires a separate instruction.
