# SPICE lineage analysis in Galaxy — tutorial draft

**Repository-local GTN-style draft. Not submitted to or endorsed by GTN.**
All data in this exercise are synthetic; no patient information is included.
This lesson tests workflow operation, not biological conclusions.

## Preparation

Use a Galaxy 25.0+ server with the five staged SPICE 0.2.0+galaxy0 tools and
IUC IQ-TREE 2.4.0+galaxy2 from revision e727e82945af. Ask the administrator to
provide BayesTraits V4.1.3 on the job execution host. SPICE is not public on
Bioconda yet: use the [local validation setup](../../docs/galaxy.md).

Upload these five files from `galaxy/tools/test-data/workflow/` as tabular data:
`matrix.tsv`, `variants.tsv`, `cells.tsv`, `states.tsv`, `state_order.tsv`.
The matrix contains REF/ALT read counts, with cells in rows and variants in
columns. Metadata must match its identifiers exactly. State order encodes the
intended biological order; it is not inferred by SPICE.

## Run the modules

1. Open **SPICE Filter** and select matrix, variants and cells separately.
   For this synthetic exercise set minimum ALT-supporting cells and minimum
   SNVs per cell to 1. Leave metadata QC on auto. Inspect the resulting FASTA,
   filtered matrix and selection audit tables. The selection audit precedes
   count filtering, so use the final matrix/FASTA for final retained dimensions.
2. Open the pinned **IQ-TREE 2.4.0** tool. Select the filtered FASTA, DNA,
   outgroup `Ref`, model `JC`, seed 12345 and the short-alignment single-thread
   setting. Set SH-aLRT to 1000, ultrafast bootstrap to 1000 and model-selection
   criterion to BIC (the IUC form initially selects AIC). Model TEST with BIC
   matches the normal SPICE invocation; JC is explicit for this small exercise.
3. Run **SPICE Clones** on IQ-TREE's supported treefile output. Set outgroup
   `Ref`, minimum tips to 2, manual clone-cut mode and cutoff 0.10 for this
   fixture, matching the existing real integration test. Automatic selection
   remains the production default; this tiny fixture has no stable automatic
   region under the production criteria. Inspect assignment, rooting, branch-cut sweep and selection
   tables. Open the clone-tree list and inspect its `Clone_N` identifiers.
4. Run **SPICE Ancestry** in collection-mapping mode over that clone-tree list,
   sharing the uploaded full states.tsv. Cells outside each clone are ignored;
   every tip in that clone must have a state. For this exercise use the exact
   reduced settings in `../workflows/spice_lineage_analysis-job.yml`, including
   its explicit QC thresholds. Record diagnostics and QC status for every clone.
5. Run **SPICE Plasticity** with the original tree list and corresponding
   ancestry-result list in aligned mapping mode. Supply the same states and
   state_order datasets. Keep the observed/permutation QC policy consistent
   and use the paired job file's three-permutation settings. Do not reorder,
   flatten or combine the two mapped lists. SPICE checks fingerprints as well
   as QC before computing the result.
6. Run **SPICE Summarize** on the complete plasticity-test collection. The
   wrapper writes a temporary manifest using collection identifiers as clone
   IDs and invokes SPICE's existing BH summary. Inspect clone IDs, test status,
   successful/requested permutations, empirical P-values and adjusted values.

Alternatively, import `../workflows/spice_lineage_analysis.ga` and run it with
the same uploads and explicit test job settings. It wires the mapped collections
and summary automatically. Its parameter defaults remain production values.

## Inspect the evidence

Open ancestral probabilities, state mapping, MCMC diagnostics and QC attempts.
A failed model-QC gate blocks downstream scientific output; do not reinterpret
missing results as zero plasticity. Review the runtime JSON for executable paths,
package hashes, software versions, settings and completion status. Positive
permutation runs require all requested replicates to succeed. A zero-permutation
run is observed-only: its significance status is `not_requested` and P-value is
NA. Do not interpret a three-permutation exercise as adequate statistical power.

Each mapped ancestry/plasticity collection should retain the corresponding
`Clone_N` element identifiers. Summary clone IDs must match those identifiers.
Changing a tree or its state annotations requires a new matching ancestry run.

## Move to a real study

Production ancestry defaults are three chains, one million iterations,
200,000 burn-in, sampling every 1,000 and ten stepping stones. Plasticity defaults
to 1,000 permutations with the corresponding production MCMC settings. The
exercise's two chains, 50,000 iterations, 10,000 burn-in, no observed stepping
stones and relaxed explicit QC thresholds are test controls, not recommended
analysis settings. Restore production defaults and assess convergence, data
quality, clone size, support and biological ordering with the study team.

Continue with the [Galaxy guide](../../docs/galaxy.md) for administration,
version pins, provenance and the separate publication sequence.
