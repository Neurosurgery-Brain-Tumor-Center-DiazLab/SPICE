# Ancestry and plasticity

[Home](Home.md) · [Input requirements](Input-Data.md) · [Outputs](Outputs-and-Provenance.md)

## Reconstruct ancestral cell states

SPICE uses BayesTraits MultiState MCMC on one supplied rooted tree. Every tip needs a cell-state annotation; extra cells in a sample-wide annotation table are ignored. Ancestral states are probabilistic estimates conditional on the tree, labels and model.

```bash
spice ancestry inputs/clone.nwk inputs/cell_states.tsv results/clone-ancestry clone
```

BayesTraits must be installed separately. SPICE records its deterministic state-code mapping; those codes do not define differentiation direction. The original tree is retained for node identity and fingerprints. When needed, a temporary NEXUS copy omits internal support labels for BayesTraits compatibility without altering original topology or branch lengths.

## Production defaults

| Setting | Ancestry | Plasticity permutations |
| --- | --- | --- |
| Chains | `--mcmc_chains 3` | `--perm_chains 3` |
| Iterations per chain | `--iterations 1000000` | `--perm_iterations 1000000` |
| Burn-in | `--burnin 200000` | `--perm_burnin 200000` |
| Sampling period | `--log_sample_period 1000` | `--perm_sample_period 1000` |
| Stepping stones | `--stepping_stones 10` | `--stepping_stones 0` |
| Iterations per stone | `--stone_iterations 1000` | `--stone_iterations 1000` |
| Hyperprior | `--hyperprior "exp 0 10"` | Same |
| Posterior cutoff | `--min_ancestral_probability 0.90` | Same |
| Parallelism | `--threads 3`: chains | `--threads 1`: permutation replicates |
| MCMC seed | `--mcmc_seed 12345` | Same base, with derived replicate/chain/retry seeds |

Plasticity additionally defaults to `--perm_replicates 1000`, `--sig_direction greater` and shuffle `--seed 12345`. These defaults are starting settings, not a guarantee of adequate convergence or statistical power for every dataset.

## Convergence and posterior confidence

Modern QC requires rank-normalized R-hat **strictly below 1.01**, bulk ESS **at least 400** and tail ESS **at least 400**, with available finite diagnostics. At least two independent chains are required; the default is three. The legacy `--effective_size_threshold 200` and `--psrf_threshold 1.1` remain recorded diagnostics; their pass flags do not replace the modern QC gate.

SPICE allows two fresh retries (`--max_retries 2`), multiplying iterations and burn-in by two each time (`--retry_multiplier 2`). It retains separate attempt evidence and does not pool chains across attempts. Process, parser and input errors stop without automatic retry. Only the selected final attempt supplies exported ancestry.

A model-QC failure blocks downstream analysis. Node-QC failures remaining after the retry budget yield uncertain nodes when model QC passes. A usable node needs both run/node QC and posterior probability at or above the cutoff. **Convergence is not posterior confidence:** well-mixed chains can support an ambiguous ancestral state.

The recorded `constant-probabilities-v1` policy has a narrow exception for derived node probabilities identical across all chains at output precision, within [0, 1]. These are explicitly labeled `constant_consistent`, with unavailable convergence diagnostics, rather than assigned fabricated R-hat/ESS values. Constant model parameters and disagreeing constant chains do not receive that exception.

## Classify transitions and quantify plasticity

```bash
spice plasticity inputs/clone.nwk inputs/cell_states.tsv \
  results/clone-ancestry/clone.ancestral_states.tsv inputs/state_order.tsv \
  results/clone-plasticity clone
```

Use the exact same tree file and matching annotations as ancestry. SPICE checks tree/state fingerprints, QC policy and run QC. Positive permutation runs also require matching observed/permutation modern QC thresholds and hyperprior.

For each directed parent-to-child edge, compare investigator-supplied state order:

| Child order relative to parent | Classification |
| --- | --- |
| Higher | Differentiation |
| Lower | Dedifferentiation |
| Equal, including different labels at the same order | Self-renewal |
| An internal endpoint is unusable or an endpoint cannot be classified | Uncertain |

SPICE's operational definition is:

```text
cellular_plasticity = 100 × dedifferentiation edges
                     / (self-renewal + differentiation + dedifferentiation edges)
```

Uncertain edges are excluded from the denominator and reported separately. If no informative edges remain, plasticity is `NA`, not zero. This is an edge-count percentage; it is not weighted by branch length and is not a per-cell transition rate. Tip labels are treated as observed states, so annotation uncertainty requires scientific consideration outside that assignment.

## Permutation significance

Each replicate shuffles state labels among tips without replacement on the fixed tree, preserving state counts, reruns ancestry, and recomputes plasticity using the same state order. This tests the association of observed labels with positions on that tree under that particular exchangeability null.

For the default `greater` alternative, the empirical P-value is `(b + 1) / (B + 1)`, where `b` counts null values at least as large as observed and `B` is the number of requested successful replicates. `less` reverses the comparison; `two-sided` compares absolute deviations from the null median.

All requested replicates must succeed with finite plasticity. Otherwise the test is `incomplete`, its P-value is `NA`, and the command exits unsuccessfully while retaining diagnostic evidence. Do not calculate significance using only successful replicates.

For observed transitions only:

```bash
spice plasticity inputs/clone.nwk inputs/cell_states.tsv \
  results/clone-ancestry/clone.ancestral_states.tsv inputs/state_order.tsv \
  results/clone-observed clone --perm_replicates 0
```

This does not need BayesTraits execution for plasticity, but still requires valid QC-bearing ancestry. Its test status is `not_requested` and P-value is `NA`. Use [Workflow](Workflow.md) to summarize a planned family of clone tests with BH correction, and read the [scientific limitations](Scientific-Assumptions-and-Limitations.md) before interpreting significance.
