# Synthetic ancestry and plasticity integration fixture

All labels and states are invented. This is software integration coverage,
not evidence of biological ancestral states or statistical power.

`tree.nwk` has twelve tips, eleven internal nodes and 22 positive-length edges.
Four-tip clades a1-a4 and b1-b4 are sisters; c1-c4 forms the other side of the
root. Each group contains the cherries (1,2) and (3,4). Root-to-tip length is
0.6 throughout. The committed Newick is independent of IQ-TREE output.

`states.tsv` has two replicated states, six tips each: a1-a4 are Progenitor,
b1-b4 are Differentiated, and c1/c3 are Progenitor while c2/c4 are
Differentiated. Rows are reversed relative to tree order to exercise tip/state
reconciliation. `state_order.tsv` puts Progenitor at 1 and Differentiated at 2.
Alphabetical BayesTraits coding therefore runs opposite to biological order;
tests check labels and order, not an assumed numeric code direction.

Two chains use 50,000 iterations, 10,000 burn-in, sampling every 100 (400
retained draws each); one retry may double iterations and burn-in. Stepping
stones are disabled. Fixture-only modern QC cutoffs are R-hat < 1.2 and bulk
and tail ESS >= 20; recorded legacy ESS/PSRF cutoffs are 20/1.2. The posterior
cutoff is 0.5 so a finite two-state posterior supplies informative transitions.
The existing exponential hyperprior, seed derivation, retry policy and QC
implementation are unchanged.

Plasticity uses matching settings for **three** real BayesTraits-backed
permutations. It must finish all three, retain chain evidence, classify observed
edges, and report a valid empirical P-value with the requested greater
alternative. Three permutations are an execution smoke test, not a calibrated
significance or power benchmark. No particular ancestral-state calls or P-value
are required. The same Newick input is supplied to ancestry and plasticity.
