# Changelog

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
