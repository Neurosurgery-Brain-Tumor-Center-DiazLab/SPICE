# Local package development

The distribution is `spice-lineage`, the import package is `spice_lineage`, and
the console entry point is `spice_lineage.cli:main`. The flat package layout
supports source execution without an editable install. `SPICE.py` only imports
`main` and `build_parser` and invokes `main` when run as a script.

## Code and resource ownership

The CLI imports `standard_input`, `import_monopogen`,
`convert_matrix_to_fasta`, `IQTREE2`, `summarize_clones` and `runtime_info`
from `spice_lineage`. Active R resources are:

| CLI path | Packaged R files |
| --- | --- |
| import-monopogen | matrix_bridge.R |
| filter | matrix_bridge.R, mutation_filter.R |
| phylogeny | BranchSupportCut.R, plus filtering files for count input |
| ancestry | ancestry_core.R, spice_ancestry_utils.R |
| plasticity | plasticity_core.R, spice_ancestry_utils.R, spice_plasticity_utils.R |
| summarize | None |

The seven R files were moved byte-for-byte. Their sibling source relationships
already work with absolute script paths. `paths.py` resolves the shared R
directory relative to the package's file location; pip installs wheel resources
as real files. Running directly from a zipped archive is not supported.

Active implementations have no duplicate copies in `scripts/`. Import helpers
through `spice_lineage`, and access R through `spice_lineage.paths.R_DIR`.
Old internal `scripts.*` import paths are not a supported Python API.
Unreached legacy analysis scripts remain in the repository, excluded from the
wheel. The sdist includes the old `monopogen_merge.R` solely because the existing
regressions compare against that independent legacy path. No R compatibility
shims are needed by the documented Python entry points.

`spice_lineage/VERSION` supplies both build metadata and runtime version.
When changing it, update the compatibility `VERSION` and `CITATION.cff` in the
same change. Source and installed checks enforce agreement. License and citation
files ship in wheel `.dist-info/licenses/` and at the sdist root.

The build metadata follows the
[setuptools pyproject configuration](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)
and [package data configuration](https://setuptools.pypa.io/en/latest/userguide/datafiles.html).

## Build and install

Use an isolated Python 3.10+ environment. Build tooling is separate from runtime
dependencies; the build frontend creates an isolated backend environment.

```bash
python -m pip install -r ci/requirements-build.txt
python -m build
# dist/spice_lineage-0.2.0.tar.gz
# dist/spice_lineage-0.2.0-py3-none-any.whl

python3 -m venv /tmp/spice-user-env
/tmp/spice-user-env/bin/python -m pip install /absolute/path/to/SPICE/dist/spice_lineage-0.2.0-py3-none-any.whl
cd /tmp
/tmp/spice-user-env/bin/spice --version
/tmp/spice-user-env/bin/spice filter --help
```

The standard frontend builds the wheel from the sdist by default; this also
checks that the sdist is sufficient to build the package. `pip install .` is
another supported local, non-editable installation.

R/Rscript and R packages, IQ-TREE and BayesTraits remain external dependencies.
Their existing PATH, `IQTREE2_BIN`, `BAYESTRAITS_BIN` and `--bayestraits_bin`
mechanisms are unchanged. Nothing has been published to PyPI, Bioconda or a
container registry, and the distribution name has not been reserved.

## Required checks

Activate the locked Linux Python/R environment described in [ci.md](ci.md):

```bash
python3 scripts/check_ci.py
python -m pip install -r ci/requirements-build.txt
python3 scripts/check_package.py
# To retain artifacts, installed environment and synthetic outputs:
python3 scripts/check_package.py --work-dir /tmp/spice-package-review
```

`--work-dir` must be a new directory outside the checkout and outside Git.
The default creates and removes a temporary directory automatically. The checker
builds both artifacts, verifies an explicit content allowlist and metadata,
creates a fresh venv, installs the wheel non-editably with its Python dependencies,
and runs copied tests and synthetic fixtures from a neutral external directory.
It removes PYTHONPATH and disallows imports from the source checkout.

The installed checks cover entry-point identity, version, all parser-defined help
commands, exit codes, all packaged resources and SHA-256 hashes, exact retained
cell/site order/counts/FASTA/sidecars, filter and summary equivalence, summary
overwrite protection, and provenance with missing or unrelated Git state.
The real filter runs R; source/installed scientific tables must match exactly.
No real IQ-TREE or BayesTraits inference is run. Phase 3 integration fixtures
and scientific release decisions remain outside this phase.

See [engineering-handoff.md](engineering-handoff.md) for observed local results.
