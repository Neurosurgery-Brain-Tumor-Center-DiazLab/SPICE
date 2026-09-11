# SPICE engineering handoff

## Scope and review status

Phase 1 implementation and local required checks are complete. STOP for review.
Hosted GitHub CI has **not** run. No claim is made that main is protected.

Starting checkout: `/home/aaron/SPICE`, remote
`https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE.git`,
commit `ed92967ce7d016997e15efd04a0917960c25e926`, branch `add-ci`,
clean working tree. Remote HEAD/main matched that commit via
`git ls-remote origin HEAD refs/heads/main`; no pull/reset/stash was performed.
Work is on `codex/phase1-ci`. No applicable AGENTS.md was found in the checkout
or its filesystem ancestors. Commit identity was supplied by the user:
Aaron Diaz <aaron.diaz@ucsf.edu>, applied per commit only.

Actual execution: Ubuntu 20.04 LTS, WSL1 distribution Ubuntu, user aaron,
Linux kernel 4.4.0-22621-Microsoft, x86_64, glibc 2.31. Commands entered through
Windows PowerShell explicitly invoked `wsl.exe -d Ubuntu --cd /home/aaron/SPICE`.
The Windows sandbox helper failed before process launch; approved WSL commands
were used. All Python/R checks ran inside Linux, not Windows.

## Baseline before code changes

System Python was 3.8.2; pandas and Rscript were absent. No Conda, micromamba,
or gh executable was on PATH. Exact requested baseline commands:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
Rscript tests/test_mcmc_qc.R
python3 SPICE.py --help
python3 SPICE.py --version
```

Python discovery failed with three module-import errors (not three real tests):
test_cli_qc and test_standard_input lacked pandas; test_release hit Python 3.8's
unsupported `int | None` annotation. Rscript was not found. Help/version failed
at the pandas import. Each of the six subcommand help commands was attempted and
failed at the same import. Those failures are preserved as environment failures;
they were not used to weaken tests or change source compatibility.

The user approved an isolated dependency download. Micromamba 2.3.2 was downloaded
from `https://micro.mamba.pm/api/micromamba/linux-64/2.3.2` and extracted below
`.local-ci/bootstrap`. The first solve with Python 3.11, pandas 2.2.3,
R 4.2.3, posterior 1.6.0, ape/coda/janitor/dplyr/progress failed: conda-forge's
posterior 1.6.0 builds require R 4.3 or 4.4. The R 4.3.3 solve then installed
162 packages (387 MB download) under `.local-ci/env`; no system packages changed.

## Implemented changes

- `.github/workflows/ci.yml`: PR/main/manual Linux job, pinned supported actions,
  read-only permission, no checkout credentials, cache, secrets, or artifact upload.
- `ci/environment.yml` and `ci/linux-64.lock`: scoped test dependency intent and
  complete Linux x86_64 package URLs/SHA-256 hashes.
- `scripts/check_ci.py`, `scripts/check_ci_dependencies.R`: shared required
  command; fail on missing dependencies, zero tests, skipped tests, failures,
  R assertion errors, or CLI failures; print counts and versions.
- `tests/test_ci_example.py`: checked-in synthetic bundle through real CLI/R
  filtering/FASTA; exact count matrix, site/cell ordering, sequences, outputs
  and runtime assertions. Fixture cutoffs 2/1; production cutoffs untouched.
- `environment.yml`: R 4.3.3 / posterior 1.6.0 resolves the demonstrated conflict.
  Full environment dry-run passed; full plotting install was not performed.
- `.gitignore`: ignores the isolated local environments.
- README, CHANGELOG, computing-environment and CI documentation: reproducible
  commands, precise scope, dependency relationship, and required status-check name.
- `docs/maintainer-decisions.md`: scientist-owned release validation checklist.
  `docs/phase1-pr.md`: ready-to-use draft PR description.

## Actual validation

Bootstrap path below abbreviates to `MM=.local-ci/bootstrap/bin/micromamba`.
All commands were run from the repository root.

```bash
$MM create -y -r "$PWD/.local-ci/mamba" -p "$PWD/.local-ci/env" \
  -c conda-forge --strict-channel-priority python=3.11 pandas=2.2.3 \
  r-base=4.3.3 r-ape r-coda r-janitor r-posterior=1.6.0 r-dplyr r-progress
$MM run -p "$PWD/.local-ci/env" python3 scripts/check_ci.py
$MM list -p "$PWD/.local-ci/env" --explicit --sha256
# Package URLs were placed below @EXPLICIT in ci/linux-64.lock.
$MM create -y -r "$PWD/.local-ci/mamba" -p "$PWD/.local-ci/locked-env" -f ci/linux-64.lock
$MM run -p "$PWD/.local-ci/locked-env" python3 scripts/check_ci.py
$MM create --dry-run -r "$PWD/.local-ci/mamba" -p "$PWD/.local-ci/full-env" \
  -f environment.yml --strict-channel-priority
.local-ci/bootstrap/actionlint .github/workflows/ci.yml
git diff --check
```

Both full check runs passed: Python discovered 17, ran 17, skipped 0, failures 0,
errors 0 (58.253 s and 68.409 s respectively). The second environment was created
from the hash-pinned lock into a previously absent prefix, using cached package
archives. Actual R QC script assertions all passed. Help/version and all six
subcommand help checks passed. VERSION output was SPICE 0.2.0.
Actionlint 1.7.7 passed. The full environment dry-run passed; this is only a solve.

Resolved test versions: Python 3.11.16, pandas 2.2.3, NumPy 2.4.6, R 4.3.3,
ape 5.8.1, coda 0.19-4.1, janitor 2.2.1, posterior 1.6.0, dplyr 1.1.4,
progress 1.2.3. Full resolution is recorded in the lock, not a fabricated version
inventory. R 4.3 / Bioconductor 3.18 compatibility is documented in docs/ci.md.

Additional guard probes ran with
`$MM run -p "$PWD/.local-ci/env" python3 .local-ci/verify_guards.py`:
injected skipped-test, failed-test, empty-discovery, and missing-Rscript cases
all raised the required error. These were deliberately mocked infrastructure
failure probes, separate from the 17-test result. Local logs and probe scripts
remain in ignored `.local-ci/` (checks.log, locked-checks.log, locked-install.log,
full-solve.log). No patient/research data was read or uploaded.

## Behavior preservation and limitations

`git diff --exit-code` confirmed all existing scientific/CLI source files and
all four pre-existing test files were unchanged. Real R tests cover equivalent
standard/Monopogen/legacy count filtering, site multiplicity and order, and
synthetic diagnostic/QC calculations. IQ-TREE and clone cutting remain mocked
in route forwarding. Retry orchestration uses a replaced MCMC runner.
No real BayesTraits inference, IQ-TREE inference, clone computation, full
plotting integration, or biological validation ran. No scientific defect was
corrected and no scientific-default change is proposed.

The check maintainers should require is **Phase 1 required checks** in **SPICE CI**.
A hosted run must be observed before claiming CI success. An authorized maintainer
must enable branch protection separately.

## Delivery and next step

Local commits on `codex/phase1-ci` contain the bounded changes. Inspect with
`git log ed92967..HEAD` and `git diff ed92967..HEAD`.

A noninteractive `git push --dry-run origin HEAD:refs/heads/codex/phase1-ci`
failed because the WSL checkout has no HTTPS Git credentials (terminal prompts
disabled). The connected GitHub app can identify the account, but that does not
provide credentials to local Git. No credentials were requested or exposed.
No branch was pushed and no draft PR exists. After configuring Git authentication,
push only this branch and use docs/phase1-pr.md to open a draft against main.

Review Phase 1 now. Do not proceed automatically:

1. Phase 2: installable distribution/console entry point, packaged R resources,
   non-editable wheel checks outside the checkout, provenance without Git.
2. Phase 3: real fixed-tree and external-tool integration fixtures; real
   BayesTraits/IQ-TREE execution with bounded resources and honest failure scope.
3. Phase 4: standalone clones command sharing the preserved R algorithm;
   arbitrary IQ-TREE input/output path wiring and fixed-tree equivalence.
4. Phase 5: tested Conda/Bioconda/container distribution, immutable sources and
   checksums, executable redistribution terms reviewed; no publication yet.
5. Phase 6: thin Galaxy/Planemo tools, starting with filter/clones, followed by
   explicit datasets/collections, provenance/QC, resource bounds, tests, workflow
   and tutorial. No Tool Shed publication or public availability claim.

Scientist-led validation and release gates remain in maintainer-decisions.md.