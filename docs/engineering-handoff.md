# SPICE engineering handoff — Phase 6 Galaxy

## Starting gate

Started from clean `codex/phase6-galaxy`, based on lab `origin/main`
`72e114e71c412fbec9c6ba97aabb90a7a64f38c4`. The remote is
Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE. No applicable AGENTS.md was found.

[PR #5](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/pull/5)
was merged. [Main CI](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34634893093),
[final Phase 5 real integration](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34634760903),
and [final Phase 5 distribution](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34634700269)
were successful. The distribution artifact records complete=true, published=false,
zero skipped Conda/container checks, package SHA-256
`033a31651f2dd3d15847232cd4a3694e44e01454396185ad22cace87a06b9452`
and image ID
`sha256:707931749650d1ff7c5314be2ad1c687cd336b27d15c805c8b13fccddd58e3a4`.
No release/tag existed; public PyPI/Bioconda/Tool Shed package lookups were absent.
Authenticated GitHub package inventory was unavailable (read:packages permission),
so it is not claimed as an additional successful check. No publishing action was
performed. [Prior Phase 5 engineering details](engineering-handoff-phase5.md)
remain available as historical context.

All four unchanged pre-edit baselines passed: required source checks, five
installed-wheel checks, real IQ-TREE/BayesTraits integration (zero skips,
116.48 seconds), and the Phase 5 Conda-only distribution checks. Local WSL1 has
no Docker; the complete hosted Phase 5 run above supplies the existing OCI gate.
Local baseline evidence is under `/tmp/spice-phase6-baseline-*`.
The local Conda package is `spice-lineage-0.2.0-py_0.conda`, SHA-256
`a83bdba808921e35d2e16e584b5d934be9cb5dff5169c82437cfbcec8dd21dc3`,
at `/tmp/spice-phase6-baseline-distribution/channel/noarch/`.

## Implementation

Five wrappers in `galaxy/tools/` expose Filter, Clones, Ancestry, Plasticity and
Summarize, with shared version `0.2.0+galaxy0`, profile 25.0 and requirement
`spice-lineage=0.2.0`. `run_spice.py` only stages inputs, creates a collection
manifest and invokes installed `spice`; it checks executable/import identity.
User text and dataset paths are passed through JSON and an exec argument list.

The native `.ga` workflow is generated from its adjacent Format 2 YAML with
pinned gxformat2. It uses owner iuc / repository iqtree / changeset e727e82945af /
tool 2.4.0+galaxy2 (executable 2.4.0). DNA, SH-aLRT=1000 and UFBoot=1000 retain
the validated support contract. Model defaults to TEST; model-selection criterion
is explicitly BIC, preserving the SPICE IQ-TREE 2.4.0 invocation rather than the
IUC form's AIC default. Required static checks and actual workflow-command checks
guard that setting. The synthetic test explicitly selects JC, one thread and
manual clone cutoff 0.10, as in the real integration fixture. Its tiny tree has no stable automatic-selection region;
automatic defaults/criteria are unchanged. IQ-TREE 3 is excluded.

Three ordinary input datasets are staged under exact standard bundle filenames.
Clones discovers unchanged `Clone_N.nwk` files as a list. Ancestry maps over that
list with the full state table; Plasticity maps aligned original trees and
ancestry results; Summarize uses unchanged list identifiers in its manifest and
calls the existing BH implementation. Production defaults are checked against
the CLI. A reproduced BayesTraits parser defect required one small production
engineering fix in spice_ancestry_utils.R: omit internal support-label metadata
only in the temporary NEXUS copy passed to V4. Original input/supports and tree
fingerprints remain intact. Fast invariance tests cover both formats; real
installed-wheel tests require exact seeded-result equivalence to an unlabeled
tree. Scientific methods/defaults, topology, branch lengths and node IDs remain
unchanged.

`check_galaxy.py` stages tests outside Git, checks the local Conda artifact and
its exact production payload, pins Galaxy release_25.0 commit
`ec10c792f94c6da0bc97b177f73be2a9287637dd` (25.0.5.dev0), Planemo 0.75.47,
gxformat2 0.27.0 and Mercurial 7.2.4, and requires all six wrapper cases plus
the full workflow. Every missing/failed/skipped required test is an error.
Official checksum-verified BayesTraits V4.1.3 is temporary and removed on exit.

Galaxy's pinned rucio-clients build initially failed because current isolated
setuptools omitted pkg_resources. A build-only setuptools=79.0.1 constraint
with explicit pip=26.2.1 fixed that setup dependency; no scientific package
or Galaxy source change was required.

The existing manual-only integration workflow retains its real scientific job
and adds an independent Galaxy job. Only named text/report artifacts are retained.
Normal required CI remains **Phase 1 required checks** and does not launch Galaxy.
The source archive includes the small wrappers/workflow/tests/tutorial; the wheel
includes the tested serialization fix. The Conda source pin identifies that
exact production payload: source commit `d0570d923d7880139a3f4c0a7a2b2e7ce65bc307`,
archive SHA-256 `47ab47321d96bb09c5c2089a0155a029e415610929fef43aa8522f51d6fb703b`.
The complete fixed installed-wheel integration passed (155.52 seconds, zero
skips), including exact labeled/unlabeled seeded ancestry equivalence for both
Newick and NEXUS. Required source checks pass with the new R regressions.

## Validation status

Required source checks (47 tests), all five installed-wheel tests and Planemo
tool/shed/workflow lint pass locally. The final fixed real IQ-TREE/BayesTraits
integration passed with zero skips (155.52 seconds); its temporary executable
was removed. actionlint 1.7.7 and git diff --check pass.

Local Galaxy startup succeeded after the build constraint, but its upload
worker failed in Python forkserver with an AF_UNIX invalid-argument error on
WSL1. The attempt was stopped and BayesTraits removal verified. No local
Galaxy functional pass is claimed; native hosted Linux supplies that gate.
The complete hosted implementation run on `72361bc999d5a3c4b729f260d1a641a2997e3aeb`
passed all six wrapper cases and the full end-to-end workflow, with zero skips:
[manual integration/Galaxy 34643919901](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34643919901).
The Galaxy report records complete=true, published=false, bayestraits_removed=true
and 716.20 seconds total. Native workflow evidence shows one filter, one IUC
IQ-TREE, one clones, three ancestry, three plasticity and one summary job, all
successful. Clone_1, Clone_2 and Clone_3 retain their corresponding trees,
ancestry outputs and plasticity outputs. Dataset IDs were inspected across each
paired job and into Summarize. Per-clone QC passed; all three requested
permutations succeeded for every clone; probability bounds and the three-row
BH summary passed the committed assertions.

The actual IQ-TREE job identifies
`toolshed.g2.bx.psu.edu/repos/iuc/iqtree/iqtree/2.4.0+galaxy2`, reports executable
2.4.0 and runs DNA, JC, seed 12345, one thread, SH-aLRT=1000 and UFBoot=1000.
Final command inspection additionally found the IUC default criterion AIC;
the workflow now explicitly selects BIC to preserve SPICE's existing TEST
behavior. JC has no model-selection choice, so the earlier synthetic pass did
not expose this default mismatch. A regression rejects the recorded AIC command,
and the final-head rerun must verify the actual BIC command as well as collection
alignment. No IQ-TREE 3 executable or tool is used.

The hosted Galaxy package was the unpublished local
`spice-lineage-0.2.0-py_0.conda`, SHA-256
`c993bcc1b6b6a495400ba4ba033ee598ba9b3b2e1bf4008309b9835fbfc2b46c`,
resolved from `file:///home/runner/work/_temp/spice-galaxy/distribution/channel`.
Its installed Conda record has the identical SHA and local URL, under
`/home/runner/micromamba/envs/spice-galaxy-build/envs/__spice-lineage@0.2.0`.
Every SPICE job checks the executable and site-packages import in that prefix.
Both wrapper cases and mapped workflow jobs used real officially provisioned
BayesTraits V4.1.3; the runner verified both pinned hashes and removal on exit.

[Required CI 34643925768](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34643925768)
and the independent real scientific job passed on the same implementation head.
The real job includes exact labeled/unlabeled seeded ancestry equivalence for
both Newick and NEXUS and reports zero skips (48.35 seconds).
[Full Conda/OCI regression 34643923728](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/actions/runs/34643923728)
also passed: complete=true, published=false and zero skipped Conda/container
checks. Its separately built local package SHA-256 is
`9d59727a02c30e4d6bd7b9e2ca2266216adf7039b2557c4e2b5731f1ee1bcf63`.
The local fixed-package Conda-only rerun passed with zero skips, SHA-256
`11afb29f0c2265ff56f56b0ebb32aefff6a0c408bf15e052bfa8e6d395686175`;
its container status is explicitly pending because this host lacks Docker.
Separate build timestamps explain the different package hashes; each tested
installation is checked against its own exact artifact and the checkout payload.

The final-head required CI, real integration/Galaxy and distribution reruns are
linked with their immutable commit in [lab PR #7](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/pull/7).
That PR is the final-head acceptance record; this file preserves the detailed
implementation-run evidence above. Phase 6 completion requires every final-head
gate to pass. No local WSL1 Galaxy functional pass is claimed.

## Publication boundary

Version stays **0.2.0 unreleased**. Tool Shed `.shed.yml` is staging metadata,
with no invented owner. The GTN-style tutorial is a repository-local draft.
No Tool Shed/GTN/Bioconda/PyPI/OCI publication, release/tag or upstream PR is
created. The Phase 6 lab PR remains for review, not merging by this task.

The exact separate publication sequence is in [the Galaxy guide](galaxy.md):
authorize/finalize the release and immutable source; publish approved package
artifacts and submit Bioconda; validate public package/BioContainer; establish
Tool Shed ownership and administrator BayesTraits deployment; retest and submit
wrappers, update workflow pins, validate the target server; then submit a reviewed
GTN adaptation. None of these publication actions is authorized by Phase 6.
