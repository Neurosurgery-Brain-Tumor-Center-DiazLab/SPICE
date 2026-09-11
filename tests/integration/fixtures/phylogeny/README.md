# Synthetic phylogeny integration fixture

All cells, counts and variants are invented. This tests software integration,
not biological accuracy, clone-selection optimality or somatic variant calling.

The standard schema-v1 bundle contains **15 cells x 700 variants**. Matrix rows
are Ref, A1-A4, B1-B4, C1-C4, LowSupport, Excluded. Every observed count is
`12/0` or `0/12` (REF/ALT); there is no random generation during a test.
`Excluded` has `pass_filter=false`. `LowSupport` has no ALT-supported sites.

Variant columns follow increasing coordinates on invented chromosome `syn1`.
At successive sites the REF/ALT pair cycles A/G, C/T, G/A, T/C.
The `synthetic_block` column documents every site's purpose:

- 240 constant sites: ALT in Ref and all twelve ingroup cells.
- 60 ingroup sites: ALT in all twelve ingroup cells.
- For each A, B and C group: 100 group-specific sites; eight sites for each
  sister pair (1,2) and (3,4); four private sites for each of the four cells.
- Four all-REF sites: removed by the ALT-count filter.

The test uses cutoffs one ALT-supporting cell per site and one retained
ALT-supported site per cell. It must retain **13 cells x 696 ordered sites**,
remove Excluded, LowSupport and the four all-REF sites, and preserve all counts
and FASTA bases exactly. Constant ALT sites keep Ref eligible for the existing
cell filter; the label Ref designates the explicit synthetic outgroup, not a
claim that all its calls are reference alleles.

The expected trusted partition is {A1,A2,A3,A4}, {B1,B2,B3,B4},
{C1,C2,C3,C4}, up to arbitrary clone names. Ref remains untrusted/unassigned.
Distinct private sites prevent IQ-TREE's identical-sequence removal from
collapsing tips. The strong group signal and short within-group branches allow
a fixed manual incoming-edge cutoff of 0.10.

The integration command uses JC to avoid model-selection cost, one thread,
1000 real UFBoot and 1000 real SH-aLRT replicates, standard support cutoffs
90/75, minimum clone size two, and explicit Ref rooting. These are fixture-only
choices; production defaults and scientific methods are unchanged.
No exact branch length, bootstrap value, clone numbering or tree bytes are
asserted. Repeated independent IQ-TREE invocations must recover the partition.
