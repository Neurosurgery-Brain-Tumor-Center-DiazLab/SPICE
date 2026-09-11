# Installed distribution assertions

checks.py is copied to an external directory and executed by the freshly
Conda-installed Python, then by Python inside the OCI image. It never imports
SPICE from the checkout. The orchestrator supplies committed synthetic fixtures,
expected source hashes and copied independent assertion helpers.

supported tree.nwk is a fixed IQ-TREE 2.4.0 output generated from the committed
synthetic phylogeny fixture during Phase 5's successful real integration baseline.
It contains 13 invented tips with SH-aLRT/UFBoot labels. Generation used JC,
1000 UFBoot and 1000 SH-aLRT replicates and one thread; all source counts are in
tests/integration/fixtures/phylogeny/standard. Ref is the outgroup; A, B and C
each have four tips. The explicit test-only manual cutoff 0.10 recovers those
three groups. Its input SHA-256 is recorded by the validation run. This fixture
is not a biological observation or evidence about threshold calibration.

Required assertions cover all CLI commands, identity/resources, real standard
filtering and known IUPAC output, fixed-tree clones, real IQ-TREE phylogeny,
combined/standalone clone equivalence with independent R tree checks, readable
exports and provenance, and clear errors with BayesTraits absent. No PDF-byte
comparison or inference mock is used. Container execution adds read-only input
mounts, a read-only root filesystem, paths with spaces, no network and host
UID/GID output ownership. Every required command must succeed; no tests skip.
