# Synthetic Galaxy fixtures

No patient data. `standard/` is the committed `examples/standard` bundle;
The Filter test asserts the complete FASTA including blank lines, and
`filter.csv` is an exact output from the unchanged merged filtering baseline. `supported-tree.nwk` comes from the existing Phase 5
synthetic IQ-TREE 2.4.0 fixture. The clone assignment/Clone_N files are its
unchanged SPICE output with explicit outgroup Ref, manual cut 0.1 and min tips 2.

`ancestry/` reuses the 12-tip Phase 3 integration fixture. Its README documents
generation; `states-extra.tsv` appends an extra Progenitor cell to exercise the
full-state-table contract. `ancestral_states.tsv` is actual real BayesTraits
V4.1.3 output from the passing pre-edit Phase 6 baseline, using two chains,
50,000 iterations, 10,000 burn-in and sampling every 100 with the existing test
QC settings. It is a small text result, not a mocked ancestry calculation.

`workflow/` uses the Phase 3 synthetic 15-cell, 700-variant standard bundle.
States assign alternating A/B/C clone tips Progenitor/Differentiated, and the
state order is Progenitor=1, Differentiated=2. Extra metadata cells demonstrate
per-clone state filtering. No inferred membership is implemented in wrappers.

`summary/one.tsv` and `two.tsv` are deliberately constructed valid result rows
with P-values 0.01 and 0.2; existing SPICE BH must yield 0.02 and 0.2.
All reduced settings and relaxed QC thresholds are explicit in the tests and
must not replace production defaults.
