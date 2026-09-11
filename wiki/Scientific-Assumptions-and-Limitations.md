# Scientific assumptions and limitations

[Home](Home.md) · [Ancestry and plasticity](Ancestry-and-Plasticity.md)

SPICE links variant-based phylogenetic inference, subclone classification, ancestral-state reconstruction and an edge-based plasticity measure. Each stage depends on assumptions and upstream data quality. Interpret the complete chain of evidence, including uncertainty and excluded cells/edges.

## Inferred lineages are not observed cell divisions

A phylogeny inferred from somatic SNV read counts represents relationships supported by the sampled data and chosen model. It is not a direct observation of every cell division, a complete history of the tissue, or a guarantee of the true lineage. Coverage, sequencing error, missingness, variant ascertainment and sampling can influence the tree. REF/ALT counts alone do not establish that a variant is somatic.

An externally reconstructed or static-barcode lineage requires its own scientific validation. SPICE's ability to analyze a prepared rooted tree does not establish the accuracy of that reconstruction, and barcode membership alone does not supply all internal branching events.

## Clone calls depend on analysis choices

Clone assignments depend on input cells/sites, inferred topology and branch lengths, rooting, support labels/cutoffs, branch-cut selection and minimum size. A stable automatic threshold is a computational selection criterion, not proof of a biologically optimal clone definition. Evaluate sensitivity to justified changes and preserve assignments for excluded or untrusted cells.

The current clone cutter assumes bifurcation and IQ-TREE support semantics. Do not interpret arbitrary labels as SH-aLRT/UFBoot or use an unvalidated tree representation as equivalent evidence. IQ-TREE 2.x, tested 2.4.0, is the validated major version.

## Ancestral states are probabilistic

BayesTraits estimates ancestral-state probabilities conditional on the supplied rooted tree, observed tip states, transition model and hyperprior. The most probable label is an inference, not a directly measured ancestor. Different trees, annotations or modeling assumptions can change its posterior.

## Convergence is distinct from confidence

MCMC diagnostics assess sampling behavior under the fitted model. Passing R-hat/ESS checks does not prove that the model or tree is correct, nor that one ancestral state has high posterior probability. Conversely, a high posterior value does not excuse failed convergence diagnostics. SPICE checks model/node QC and posterior confidence separately. Its explicitly flagged constant-probability exception is not an estimated convergence statistic.

## State order is supplied by the investigator

`state_order.tsv` encodes the study's differentiation ordering; SPICE does not learn or validate this biological order. Numeric BayesTraits codes are separate bookkeeping labels. Higher order is interpreted as more differentiated, and equal order as self-renewal even for distinct labels. Document the rationale and assess sensitivity when plausible orderings differ or states do not naturally form a single ordering.

## Plasticity has a specific operational definition

SPICE reports 100 times the number of dedifferentiation edges divided by all informative self-renewal, differentiation and dedifferentiation edges. It measures this feature of the supplied tree and inferred states. It is not a universal measure of cell plasticity, a direct transition observation, a rate per unit time, or an estimate of every cell's potential.

## Uncertain edges are excluded

An edge with an unusable internal endpoint remains uncertain and is excluded from the plasticity denominator. Inspect uncertain counts together with the informative count and percentage: changing uncertainty can change the denominator and comparability across clones. Zero informative edges yield `NA`; failed or unavailable output must not be interpreted as zero plasticity. Tip-state assignments are treated as observed, so uncertainty in those annotations is not automatically propagated as measurement error.

## Permutation P-values address a particular null

The null shuffles tip-state labels without replacement on a fixed tree, preserves label counts, reruns ancestry and recomputes plasticity. Its interpretation depends on whether exchanging those labels is scientifically appropriate. It does not account for all uncertainty in topology, variant calling, state annotation or investigator choices. A significant result does not establish a causal mechanism, and a nonsignificant result does not establish absence of plasticity.

All requested replicates must succeed for a valid test. Choose a suitable permutation count, inspect diagnostics, and summarize the complete predeclared clone family for multiple-testing correction. Three-permutation tutorial results test execution and offer no useful claim of statistical power for a study.

## Engineering validation is not biological benchmarking

The CI, real-tool integration and Galaxy fixtures are synthetic engineering checks. They test schemas, orchestration, invariance, QC, provenance and failure handling. They do not demonstrate biological reconstruction accuracy, clinical performance, generalization, runtime/memory performance on representative studies, or a completed biological benchmark.

Scientist-led validation decisions remain documented in [maintainer decisions](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/maintainer-decisions.md). Keep those decisions distinct from successful software tests and [release status](Citation-and-Release.md).
