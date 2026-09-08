# Tiny standard-input example

From the repository root:

```bash
python3 SPICE.py filter examples/standard results/example example --input_format standard \
  --min_alt_cells_per_snv 2 --min_snvs_per_cell 1
```

Expected: three sites and three cells. The first two distinct SNVs have identical
count patterns and both remain. Sequences are `Ref: GGC`, `cell-2: RRT`, and
`cell_3: AAT`. The fourth site and cell fail the count cutoffs. No Monopogen
quality fields are present, so auto QC applies only the shared count filters.
This deliberately tiny fixture is for filtering, not biological tree validation.
