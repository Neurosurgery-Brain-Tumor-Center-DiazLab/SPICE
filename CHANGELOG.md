# Changelog

## Unreleased

- Add `spice clones --tree TREE --output_directory DIR --prefix SAMPLE` and
  equivalent legacy-wrapper support. It classifies an existing IQ-TREE Newick
  tree without executing IQ-TREE, including no provenance-only version probe.
- Share clone/rooting option registration and the authoritative R execution path
  with `phylogeny`. Pass the actual inferred tree path or supplied tree as R
  argument 16; preserve the old 15-argument R form and all scientific parameters,
  methods, defaults, output names and schemas.
- Add required fast routing/default/validation/provenance regressions and real
  installed-wheel combined-versus-standalone equivalence checks using an
  arbitrary external tree path containing spaces. Reuse the manual-only
  **SPICE Phase 3 Integration** workflow; required CI is unchanged.
- Keep 0.2.0 unreleased. No Galaxy wrappers or package/container publication.

- Add real IQ-TREE 2.4.0 / BayesTraits V4.1.3 integration through an external,
  non-editable wheel install, committed synthetic fixtures, strict output/QC/
  provenance assertions, and a dedicated SHA-256-pinned Linux dependency lock.
- Add **SPICE Phase 3 Integration**, triggered only by workflow_dispatch and
  not required for PR merge. The runner verifies the official BayesTraits
  archive/binary hashes, deletes downloaded executables after the run, and
  retains only text evidence in the workflow artifact.
- Fix two reproduced BayesTraits subprocess integration defects: convert accepted
  Newick input to full-precision NEXUS for V4; use a chain-local LogFile basename
  to support output directories with spaces. Original tree fingerprints,
  node identities, log locations and scientific tables are preserved.
  Scientific algorithms/defaults, QC/retry policies and overwrite guards are
  unchanged. Version remains 0.2.0 (unreleased); no publication.


- Add the local `spice-lineage` wheel/sdist and `spice` console command;
  `SPICE.py` delegates to the same `spice_lineage.cli.main`. No publication.
- Move the active Python helpers and seven unchanged R files into the package;
  resolve R resources relative to the installed package. Scientific algorithms,
  defaults, output tables and overwrite behavior are unchanged.
- Use `spice_lineage/VERSION` for package metadata and runtime version; CI verifies
  agreement with the checkout `VERSION` and `CITATION.cff`.
- Runtime JSON retains its existing version/tool/package/status fields.
  `source_sha256` keys now identify `spice_lineage/*.py`,
  `spice_lineage/VERSION` and `spice_lineage/resources/r/*.R`; a verified checkout
  also retains `SPICE.py` and `VERSION` hashes. New `source_root` identifies the
  running package directory. Unrelated parent repositories and ambient `GIT_*`
  overrides are ignored; installed wheels explicitly report Git unavailable.
- Extend **Phase 1 required checks** with artifact inspection, fresh non-editable
  installation, all-command help/version, real standard-input filtering,
  legacy equivalence and provenance outside Git.

- Add locked Linux Phase 1 CI with mandatory Python/R dependencies, zero-skip
  regression checks, all-command CLI smoke checks, and exact real-filter example
  assertions; document scope and reproducible local execution.
- Reconcile the Conda target to R 4.3.3 / posterior 1.6.0 after the prior
  R 4.2 / posterior >= 1.6 combination failed dependency resolution.

- Add schema-v1 cell × variant count/metadata TSV bundles, strict validation,
  and an optional `import-monopogen` adapter preserving sites and annotations.
- Route Monopogen convenience and direct input through the existing count filter;
  `phylogeny --input_format standard|monopogen` continues through clone cutting.
- Remove the unused composition-test inclusion CLI flag.
- Preserve metadata QC defaults, support ordering, clone selection, rooting and
  IQ-TREE resource handling; fix FASTA metadata-name collisions and normalize
  combined-workflow output paths.
- Add real-R import/filter equivalence and schema/forwarding regression tests.

## 0.2.0 — unreleased

- Execute IQ-TREE with argument lists and quote generated shell scripts.
- Identify posterior columns by unique state codes (`posterior_state_0`, etc.).
- Validate tree branch lengths and finite state-order values.
- Record QC policy and enforce observed/permutation compatibility.
- Remove the unused `btw` dependency from the main CLI.
- Add runtime provenance, environment definition, installation helper and version command.
- Add clone-result aggregation with BH-adjusted p-values.
- Resolve BayesTraits in the legacy runner from environment/PATH.

Results without the new QC policy metadata require a new ancestry run before use
with the updated plasticity command. Posterior column names now use state codes;
join `.state_mapping.tsv` to recover original state labels.

## Previous main snapshots

- `ac652e8`: allow identical constant node probabilities across all chains while
  retaining explicit diagnostic status and strict model QC.
- `c83f588`: modern convergence diagnostics, fresh retries, downstream gating,
  deterministic MCMC seeds and confidence-cutoff recalculation.
