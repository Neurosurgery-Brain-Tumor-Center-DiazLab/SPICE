# Add required Linux regression CI and reproducible Phase 1 checks

The prior Conda target could not resolve R 4.2 with posterior >= 1.6, and Python
tests could appear green while skipping R integration. This change adds a
SHA-256-locked Linux CI environment and a shared required check command that
fails on missing dependencies, skipped/empty suites, or any failed check.
The general target moves to R 4.3.3 with posterior 1.6.0.

CI runs the existing Python regressions, actual R QC suite, help/version for
all commands, and the checked-in synthetic example through real R filtering
and FASTA conversion. The example test asserts its complete count matrix,
ordered IDs and sequences, sidecars, plot presence, and runtime success.
Production/scientific source and the pre-existing tests are unchanged.

Validation: two fresh isolated Ubuntu/WSL prefixes, including recreation from
the checked-in lock, each ran 17 Python tests with zero skips/failures/errors,
the R QC suite, and every CLI smoke check successfully. Actionlint 1.7.7 and
git diff --check passed. Injected skip/failure/empty/missing-R probes were rejected.
The revised general environment solved; full plotting installation was not run.

IQ-TREE/clone route checks and MCMC retries remain explicitly mocked. No real
IQ-TREE or BayesTraits inference or biological validation is claimed.
Hosted CI has not run; maintainers should observe it and then require
**Phase 1 required checks**. Branch protections are not changed.

Phase 1 only. Please review before authorizing packaging or later Galaxy phases.
See docs/engineering-handoff.md for commands, versions, limitations, and roadmap.