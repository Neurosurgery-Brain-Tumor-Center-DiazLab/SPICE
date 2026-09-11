# Maintainer decisions and scientific release gates

Phase 1 changes installation/test infrastructure only. No scientific correction
has been made or newly established by these tests. A suspected scientific defect
must first receive a minimal reproducer and a maintainer decision; an existing
behavior assertion alone does not establish biological correctness.

Pending scientist-led validation (Aaron/Bohyeon; no results claimed):

- Approve redistributable barcode-based clone/phylogeny validation data and protocol.
- Independently evaluate the stability-based clone selector; stable thresholds
  do not establish biologically optimal thresholds.
- Evaluate rooting sensitivity while retaining current defaults until reviewed.
- Define runtime/memory benchmark datasets, resource limits, and measurements.
- Review variant-calling claims: REF/ALT read counts do not independently
  establish somatic status.
- Arrange reproducibility testing outside the development environment.

No STICR/DAISY fixtures, biological ground truth, benchmark measurements,
clinical-performance conclusions, or release/publication claims are supplied.
Later phases require separate approval as recorded in engineering-handoff.md.