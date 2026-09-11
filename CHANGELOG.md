# Changelog

## Unreleased

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
