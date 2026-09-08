# Standard-input architecture validation

Base: DiazLab/SPICE commit `34a1d4c` (SPICE 0.2.0).

## Executed checks

- Python unittest discovery: **16 tests passed**, including existing CLI QC and
  release tests and new schema/import/filter/forwarding tests.
- Real base-R RDS import/export and existing `mutation_filter.R` execution.
- Imported Monopogen and direct standard bundles produce byte-identical filtered
  CSV and FASTA for equivalent count/metadata fixtures (including shared site
  patterns, reordered chromosome cells, and one/two-worker runs).
- The legacy `monopogen_merge.R` + `mutation_filter.R` route produces the same
  retained CSV for the equivalent fixture.
- Metadata QC, cell eligibility/selection, inconsistent duplicates, missing
  companions, malformed/empty inputs, and safe identical-input reruns exercised.
- Both combined phylogeny routes pass identical alignments and the requested
  threads, outgroup, and manual clone threshold to the downstream commands.
- The checked-in direct-input example ran through the actual CLI, produced
  `GGC`, `RRT`, `AAT` for the three retained cells, and recorded runtime success.
- `git diff --check` passed.

## Preserved scientific code

`scripts/mutation_filter.R`, `scripts/BranchSupportCut.R`, and
`scripts/IQTREE2.py` are unchanged from the base commit. This preserves the existing
one-pass count filter, SH-aLRT/UFBoot interpretation, auto/manual clone selection,
rooting options, executable resolution, and IQ-TREE threading.

The FASTA converter now takes cell columns directly instead of joining temporary
metadata columns: a real cell named `Ref` is no longer confused with reference
allele metadata. Cell order follows the filtered matrix; allele mapping is unchanged.

## Scope of evidence

IQ-TREE inference and `BranchSupportCut.R` computation were **not executed** in
this environment. The combined-route test runs real upstream filtering and mocks
only those two external computations to check command/alignment forwarding.
Thus equivalence is established through the alignment boundary; numerical tree
and clone equivalence across real stochastic IQ-TREE runs is not claimed.
The full biological/MCMC pipeline was not rerun for this input-layer change.

Tests used Python 3.12.14 with pandas 2.2.3 and the local R installation. The missing
R `progress` dependency was installed into a separate local test library; it is
not part of the repository. Standard installations need the R filter dependencies
listed in the README.
