# Proposed Test Tool Shed publication and validation

**NOT EXECUTED. Stop before remote writes.** This runbook is prepared for a
separate, explicit maintainer authorization. The [dated gate report](public-distribution-validation-2026-10-19.md)
records current blockers. It does not authorize Main Tool Shed, Bioconda, Zenodo,
Git tag, workflow-release or GTN changes.

Planemo 0.75.47 `--help` was checked for every command below. There is no
`planemo shed_install` command in that version; `shed_test` installs published
repositories into a disposable Galaxy and tests them. `shed_create` normally
uploads too, so the initial creation below explicitly uses `--skip_upload`.

## Reviewed inputs and preflight

Review and merge the validation/documentation branch before publication so the
new README evidence links under `main` resolve publicly. This task did not push
or merge that branch.

Publication commands below are proposed only after authorization. The observed
review paths are on WSL. Full Galaxy validation requires a full Linux host such
as Ubuntu 24.04: the pinned Galaxy Celery forkserver failed during uploads on
WSL1. Transfer the inspected archive/evidence to that host, provision the pinned
Conda/Planemo/Galaxy toolchains from the Galaxy guide, and set the path variables
to their actual locations. Preserve the reviewed archive hash. These paths identify the reviewed
local artifact, not a freshly generated archive with unreviewed changes:

```bash
REPO=/home/aaron/SPICE
EVIDENCE=/tmp/spice-public-validation-20261019
PLANEMO=/tmp/spice-phase6-planemo-env/bin/planemo
CONDA_TOOLS=/tmp/spice-phase5-toolchain
GALAXY_ROOT=/tmp/spice-phase6-galaxy-source
TOOLS="$EVIDENCE/shed-review/galaxy/tools"
ARCHIVE="$EVIDENCE/shed-review/galaxy/tools.tar.gz"
TESTSHED=https://testtoolshed.g2.bx.psu.edu
printf '%s  %s\n' \
  125a5180889a14186117a5e89235b8288da67e95abef3a0cb2d9804c952d19bc \
  "$ARCHIVE" | sha256sum --check -
test "$(git -C "$GALAXY_ROOT" rev-parse HEAD)" = \
  ec10c792f94c6da0bc97b177f73be2a9287637dd
git -C "$GALAXY_ROOT" diff --exit-code HEAD
"$PLANEMO" --version
curl --fail --silent --show-error \
  "$TESTSHED/api/repositories?owner=diazlab&name=spice_lineage"
```

On 2026-10-19 the repository query returned `[]`. Repeat it immediately before
publication, and confirm the logged-in **Test** Tool Shed account is `diazlab`
and owns/can update the intended repository. Account identity was not verified
in this session because browser sandbox initialization failed. Main Tool Shed
credentials and ownership must not be assumed to apply to Test Tool Shed.
Acquire a Test Tool Shed API key through its normal account UI; provide it only
as environment variable `TEST_TOOL_SHED_API_KEY`. Never put it in arguments,
repository files, shell tracing, logs or this document.

## Remote-write commands: only after separate explicit authorization

For a still-absent repository, create metadata without uploading content:

```bash
"$PLANEMO" shed_create "$TOOLS" \
  --shed_target "$TESTSHED" --owner diazlab --name spice_lineage \
  --shed_key_from_env TEST_TOOL_SHED_API_KEY --skip_upload
```

For an existing `diazlab/spice_lineage` repository, update only reviewed metadata
instead of creating a duplicate:

```bash
"$PLANEMO" shed_update "$TOOLS" \
  --shed_target "$TESTSHED" --owner diazlab --name spice_lineage \
  --shed_key_from_env TEST_TOOL_SHED_API_KEY --skip_upload
```

Choose exactly one of those branches. Then upload the **inspected archive**:

```bash
"$PLANEMO" shed_upload "$TOOLS" \
  --shed_target "$TESTSHED" --owner diazlab --name spice_lineage \
  --shed_key_from_env TEST_TOOL_SHED_API_KEY --check_diff \
  --tar "$ARCHIVE" --message 'SPICE 0.2.0+galaxy0; public Bioconda validation'
```

None of these three commands was executed during preparation. `--check_diff`
does not make an upload command read-only. Do not omit `--shed_target`.

## Capture published IDs and changeset

After an authorized upload, save repository and downloadable metadata responses
using the repository ID returned by the query above:

```bash
# Set REPOSITORY_ID to the actual returned ID; never invent it.
curl --fail --silent --show-error \
  "$TESTSHED/api/repositories/$REPOSITORY_ID/metadata?downloadable_only=true" \
  > "$EVIDENCE/test-toolshed-published-metadata.json"
```

Select the newly uploaded downloadable, non-malicious changeset. Require exactly
`spice_filter`, `spice_clones`, `spice_ancestry`, `spice_plasticity`,
`spice_summarize`, each version `0.2.0+galaxy0`, profile `25.0`, and requirement
`spice-lineage=0.2.0`. Record its actual changeset and each full Test Tool Shed
tool GUID, its citation and repository metadata. Re-download that changeset and
compare member content hashes with `shed-archive-inspection.json`; Tool Shed
may add metadata, so compare intended file contents rather than tarball bytes.

## Fresh Galaxy installation and six wrapper tests

Create a new disposable work directory. Use the pinned Galaxy checkout and a
fresh Conda root/cache, with only public channels. The administrator must supply
a real externally installed BayesTraits V4.1.3. The binary is not uploaded or
bundled with the tools:

```bash
RUN=$(mktemp -d /tmp/spice-testshed-validation-XXXXXX)
export HOME="$RUN/home" CONDA_PKGS_DIRS="$RUN/conda-pkgs"
export CONDA_ENVS_PATH="$RUN/conda/envs"
export CONDA_CHANNEL_PRIORITY=strict CONDA_SOLVER=libmamba
export PYTHONNOUSERSITE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
unset PYTHONPATH PYTHONHOME R_LIBS R_LIBS_USER R_PROFILE_USER R_ENVIRON_USER
mkdir -p "$HOME" "$CONDA_PKGS_DIRS"
"$CONDA_TOOLS/bin/conda" create --yes --prefix "$RUN/conda" \
  --override-channels --strict-channel-priority -c conda-forge -c bioconda \
  'conda=26.7.2' 'python=3.11'
"$CONDA_TOOLS/bin/python" -m venv "$RUN/galaxy-venv"
"$RUN/galaxy-venv/bin/python" -m pip install 'pip==26.2.1'
export GALAXY_VIRTUAL_ENV="$RUN/galaxy-venv"
export PIP_BUILD_CONSTRAINT="$REPO/ci/galaxy-build-constraints.txt"
export RUN REPO
# BAYESTRAITS_BIN must already name the administrator's executable.
"$CONDA_TOOLS/bin/python" - <<'PY'
import hashlib, json, os
from pathlib import Path
binary = Path(os.environ['BAYESTRAITS_BIN']).resolve(strict=True)
assert hashlib.sha256(binary.read_bytes()).hexdigest() == '711024887c5484d5f6e768313b1aafea01c83705234e9a1172d5ed8e8f33bb4d'
config = {'runners': {'local': {'load': 'galaxy.jobs.runners.local:LocalJobRunner', 'workers': 1}},
          'execution': {'default': 'local', 'environments': {'local': {
              'runner': 'local', 'tmp_dir': True, 'env': [
                  {'name': 'BAYESTRAITS_BIN', 'value': str(binary)},
                  {'name': 'OPENBLAS_NUM_THREADS', 'value': '1'},
                  {'name': 'OMP_NUM_THREADS', 'value': '1'}]}}},
          'tools': [{'class': 'local', 'environment': 'local'}]}
(Path(os.environ['RUN']) / 'job-conf.yml').write_text(json.dumps(config))
PY
COMMON=(--galaxy_root "$GALAXY_ROOT" --galaxy_python_version 3.11
  --galaxy_startup_timeout 1200 --conda_prefix "$RUN/conda"
  --conda_channels conda-forge,bioconda --conda_dependency_resolution
  --conda_auto_install --no_conda_auto_init --job_workers 1 --no_cleanup
  --job_config_file "$RUN/job-conf.yml")
"$PLANEMO" shed_test "$TOOLS" --shed_target "$TESTSHED" \
  --owner diazlab --name spice_lineage "${COMMON[@]}" \
  --shed_data_dir "$RUN/shed-state" \
  --test_output "$RUN/tools.html" --test_output_json "$RUN/tools.json" \
  --test_output_xunit "$RUN/tools.xml" --job_output_files "$RUN/outputs"
```

This installs the published tools into a fresh local Galaxy. Verify the installed
changeset is the captured one, not a concurrent later update. Require six
successful cases and zero skips. Recheck the actual Conda metadata, downloaded
artifact SHA-256 and installed Python/R payload with `verify_public_install` in
`scripts/check_public_distribution.py`, using the saved public `artifact.json`.
The public URL must be the exact Bioconda noarch URL in the gate report. Inspect
runtime provenance and confirm the jobs use that environment and the external
BayesTraits binary. Preserve logs, installation metadata and test reports.

## Full workflow against published Test Tool Shed tools

Copy `galaxy/workflows` to `$RUN/galaxy/workflows`. **Only in that disposable
copy**, replace the five SPICE step IDs with the observed full Test Tool Shed
GUIDs and add the observed SPICE `tool_shed_repository` owner/name/changeset to
each step. Add that exact Test Tool Shed repository to the copied `tools.yml`.
Preserve all parameters, connections, job fixtures, tests and the existing
Main Tool Shed IUC IQ-TREE revision `e727e82945af`, version `2.4.0+galaxy2`.
No unpublished revision is inserted into the release workflow.

```bash
"$PLANEMO" workflow_lint "$RUN/galaxy/workflows/spice_lineage_analysis.ga"
"$PLANEMO" test "$RUN/galaxy/workflows/spice_lineage_analysis.ga" \
  "${COMMON[@]}" --shed_data_dir "$RUN/shed-state" \
  --test_output "$RUN/workflow.html" --test_output_json "$RUN/workflow.json" \
  --test_output_xunit "$RUN/workflow.xml" --job_output_files "$RUN/workflow-outputs"
"$CONDA_TOOLS/bin/python" - <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(os.environ['REPO']) / 'scripts'))
from check_galaxy import validate_test_report, validate_workflow_execution
work = Path(os.environ['RUN'])
print(validate_test_report(work / 'tools.json', 6))
print(validate_test_report(work / 'workflow.json', 1))
print(validate_workflow_execution(work / 'workflow.json'))
PY
```

Do not add local SPICE wrappers through `--extra_tools` to this post-publication
run: it must exercise the published repository. Recheck public package origin
and all runtime/provenance, mapping, original-tree pairing, summary membership
and IQ-TREE command invariants. A failed or skipped case is a failed gate.
Archive evidence, stop the disposable Galaxy, and remove only temporary
BayesTraits copies created for testing; do not remove the administrator's
original installation. Main Tool Shed and GTN publication remain separately
authorized work even after a successful Test Tool Shed run.
