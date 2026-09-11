SPICE currently requires a source checkout to run its CLI and locate R scripts.
This change adds an installable local wheel/sdist and a `spice` executable that
works from an external analysis directory while preserving `python SPICE.py ...`.

## Architecture

- Flat `spice_lineage` package; distribution `spice-lineage`; console entry
  `spice_lineage.cli:main`. `SPICE.py` is a thin wrapper importing that same main.
- Move six Python helpers and the CLI into the package. Move all seven active
  R scripts into `spice_lineage/resources/r/` with no R content changes.
  Resolve resources relative to the installed package, including sibling R sources.
- Keep one implementation of active code. Unreached legacy files stay in the
  checkout; no generic `scripts` package is installed.
- Package VERSION drives CLI/build version; tests enforce agreement with root
  VERSION, CITATION.cff and installed distribution metadata.
- Preserve runtime JSON fields and add source_root. Hash actual installed
  Python/R resources; Git commit/status are recorded only for the verified SPICE
  checkout. Missing/unrelated Git and GIT environment overrides are handled safely.

## Scientific boundary

Seven R files and four Python helpers (standard_input, convert_matrix_to_fasta,
IQTREE2 and summarize_clones) are byte-for-byte identical to the Phase 1 base.
The importer changes only its bridge resource path/import. CLI changes only
package imports, resource lookup, help program name, missing-resource wording and
removal of the checkout working-directory assumption for R. Five inherited CLI
trailing-whitespace lines were trimmed for diff-check with an identical AST.
The remaining changes are packaging, provenance, tests and documentation.
Scientific algorithms, defaults, schemas and overwrite protections are unchanged.

## Validation

Linux WSL, Python 3.11.16 and R 4.3.3 using the existing locked Phase 1 environment:

- `python3 scripts/check_ci.py`: baseline 17 tests; after refactor 21 tests;
  zero skips/failures/errors. Real R QC and all six CLI help checks pass.
- `python -m pip install -r ci/requirements-build.txt`, then
  `python3 scripts/check_package.py --work-dir /tmp/spice-phase2-final-r1`:
  isolated `python -m build`, sdist and wheel inspection, fresh external
  non-editable pip install, `pip check`, and five installed-package tests.
- `spice --version` reports SPICE 0.2.0; help works for every parser subcommand.
  Imports are verified under the fresh venv's site-packages, with no source
  PYTHONPATH, editable install or installed generic scripts package.
- Actual wheel/R standard-input filter with cutoffs 2/1 and one thread: ordered
  cells/sites, full matrix, GGC/RRT/AAT FASTA, sidecars and provenance pass.
  Filter and summary outputs match the legacy wrapper; overwrite protection passes.
- Runtime JSON outside Git succeeds, includes package resource SHA-256 hashes,
  and explicitly reports unavailable Git even in an unrelated working directory.
- `actionlint .github/workflows/ci.yml` and `git diff --check` pass.
  Full environment/commands/evidence are in docs/engineering-handoff.md.

Artifacts are `spice_lineage-0.2.0-py3-none-any.whl` and
`spice_lineage-0.2.0.tar.gz`. The wheel contains 24 files: the package, VERSION,
seven active R resources and distribution/license/citation metadata. The sdist
includes bounded docs, synthetic tests/examples and required development helpers.
Explicit content and byte comparisons exclude environments, Git, logs, caches,
credentials, patient data and unrelated legacy scripts.

## CI and limitations

Keep the required job name **Phase 1 required checks** and its original checks;
append build/non-editable-install checks in that same job. No new ruleset status
name, repository secrets, publication or merge is required by this change.
Hosted results must be observed on this PR; local checks do not assert hosted success.

R/R packages, IQ-TREE and BayesTraits remain external. Real IQ-TREE/BayesTraits
inference was not part of Phase 2. Plotting/clone integration, biological validation,
Phase 3 fixtures, standalone clones, Bioconda/containers and Galaxy are unvalidated
and outside scope. No registry publication or distribution-name reservation.
