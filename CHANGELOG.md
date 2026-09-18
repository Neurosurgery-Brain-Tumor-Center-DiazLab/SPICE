# Changelog

## 0.2.0

### Standard input and filtering

- Add schema-v1 cell × variant count bundles (`matrix.tsv`, `variants.tsv`,
  `cells.tsv`), strict validation and an optional `import-monopogen` adapter
  that preserves sites and annotations.
- Route direct and Monopogen inputs through the same count filter;
  `phylogeny --input_format standard|monopogen` continues through clone cutting.
  Preserve metadata QC, cell selection and filtering defaults.
- Fix FASTA metadata-name collisions and normalize combined-workflow output
  paths. Remove the unused composition-test inclusion CLI flag.

### Packaging and CLI

- Provide the `spice-lineage` wheel/sdist, `spice_lineage` import namespace and
  seven-command `spice` CLI. The legacy `SPICE.py` wrapper delegates to the same
  entry point. Package active Python helpers and seven R resources, resolving
  resources relative to the installed package.
- Use `spice_lineage/VERSION` for package/runtime version and check agreement
  with `VERSION` and `CITATION.cff`. Align citation and package authorship with
  the approved software authors Bohyeon Yu and Aaron Diaz, including ORCIDs.
- Include the repository-local user guide and release notes in the sdist;
  inspect artifact contents and test fresh non-editable installation, all
  command help/version routes, real filtering and legacy equivalence.
- Remove the unused `btw` dependency from the main CLI.

### Phylogeny and clone classification

- Run IQ-TREE with argument lists and quote generated shell scripts. Validate
  lineage inference with **IQ-TREE 2.4.0**; retain support ordering, rooting,
  clone-selection methods/defaults and resource handling.
- Add standalone `spice clones --tree TREE --output_directory DIR --prefix SAMPLE`
  and legacy-wrapper support for an existing supported IQ-TREE Newick tree.
  It never executes IQ-TREE, including for a version probe.
- Share clone/rooting options and the authoritative R execution path with
  `phylogeny`; pass the actual tree path explicitly while preserving the legacy
  15-argument R form. Verify combined-versus-standalone equivalence with real
  installed-wheel tests, including external paths containing spaces.

### Ancestral-state inference and QC

- Add modern convergence diagnostics, deterministic MCMC seeds, fresh retries
  with retained evidence, downstream QC gating and confidence-cutoff recalculation.
  Allow identical constant node probabilities across chains while retaining
  explicit diagnostic status and strict model QC.
- Identify posterior columns by unique state codes (`posterior_state_0`, etc.).
  Validate tree branch lengths and finite state-order values. Record QC policy
  and enforce observed/permutation compatibility.
- Serialize accepted Newick input as full-precision temporary NEXUS for
  BayesTraits V4. Omit internal support-label metadata only from that subprocess
  copy; preserve original trees/supports, node identities, rooted topology,
  branch lengths, fingerprints and scientific calculations. Cover this with
  format invariance and real seeded ancestry equivalence checks.
- Use chain-local BayesTraits LogFile basenames so output paths containing
  spaces work. Resolve BayesTraits in the legacy runner from environment/PATH.
  **BayesTraits V4.1.3 remains external and is not redistributed.**

### Plasticity and clone-level summary

- Quantify ordered-state lineage transitions and dedifferentiation-based
  plasticity, with tip-state permutation testing and QC-compatible ancestry.
- Add clone-result aggregation with Benjamini–Hochberg adjusted p-values over
  the planned family of clone tests, retaining incomplete/failed-test status.

### Reproducibility and provenance

- Record software/tool/package versions, settings, executable identity,
  completion status and source hashes in runtime JSON.
- Package source hashes identify `spice_lineage/*.py`, `spice_lineage/VERSION`
  and `spice_lineage/resources/r/*.R`; `source_root` identifies the running
  package. Verified checkouts also retain `SPICE.py` and root `VERSION` hashes.
  Ignore unrelated parent repositories and ambient `GIT_*` overrides;
  installed wheels explicitly report Git unavailable.
- Add locked Linux CI with mandatory Python/R dependencies, zero-skip checks,
  CLI smoke tests and exact synthetic filtering assertions. Use R 4.3.3 and
  posterior 1.6.0 after the earlier R 4.2 combination failed to resolve.

### Distribution and external-tool validation

- Stage a classic Bioconda-style recipe with an immutable checksum-pinned
  source and an OCI image consuming the locally built Conda artifact. Include
  compatible R runtime dependencies and IQ-TREE 2.x; distribution builds do
  not download or bundle BayesTraits.
- Add a locked Linux packaging toolchain and separate manual full Conda/OCI
  validation with clean external installs, artifact/source hashes, real
  filtering, clones/IQ-TREE checks and text-only evidence.
- Add real **IQ-TREE 2.4.0 / BayesTraits V4.1.3** integration through an external
  non-editable wheel, synthetic fixtures and strict output/QC/provenance checks.
  Verify official BayesTraits archive/binary checksums, remove downloaded
  executables after testing and retain only text evidence.
- Public distribution channels require separate publication and verification.
  The `v0.2.0` tag now exists; finalizing the public Bioconda recipe with its
  tag archive and calculated SHA-256 remains a separate publication step.

### Galaxy integration

- Provide five native Galaxy 25.0 wrappers (`0.2.0+galaxy0`), shared metadata,
  synthetic Planemo tests and a clone-collection workflow using pinned IUC
  IQ-TREE **2.4.0+galaxy2**, changeset `e727e82945af`. Pin BIC explicitly to
  preserve SPICE model selection. Retain aligned clone identifiers through
  ancestry/plasticity and the existing BH summary.
- Add external local-Conda Galaxy validation as a separate job in the manual
  integration workflow. Acquire BayesTraits from its official source, verify
  checksums and remove it after validation; server deployment requires an
  administrator-provided executable. Required PR CI retains fast static,
  default and manifest checks.
- Supply Tool Shed staging metadata and a repository-local GTN-style tutorial
  draft; public Tool Shed/GTN availability requires separate verification.

### Documentation and cold-start validation

- Make the repository-local wiki the canonical user guide, with a concise
  README, installation instructions and a discoverable end-to-end CLI exercise.
- Document the independently validated Conda/micromamba installation after
  unpinned CRAN/BiocManager resolution failed in a fresh R 4.3.3 environment.
- Independent cold-start validation passed non-editable installation, `pip check`,
  all seven commands, tiny filtering and a 13-cell × 696-site synthetic pipeline:
  IQ-TREE 2.4.0, three expected clone partitions, standalone clone equivalence,
  ancestry QC for all clones, 9/9 requested permutations, summarize and provenance.
  A fresh locked real-tool integration also passed with zero skips.
- Validation scope is **Linux x86_64** and synthetic software checks; it does not
  establish biological accuracy or native Windows/macOS support.

### Compatibility notes

Results without the new QC-policy metadata require a new ancestry run before
use with the updated plasticity command. Posterior columns use state codes;
join `.state_mapping.tsv` to recover original state labels. BayesTraits V4
NEXUS serialization affects only the temporary subprocess tree copy. BayesTraits
remains separately supplied; IQ-TREE 2.4.0 is the validated inference version.

## Previous main snapshots

- `ac652e8`: allow identical constant node probabilities across all chains while
  retaining explicit diagnostic status and strict model QC.
- `c83f588`: modern convergence diagnostics, fresh retries, downstream gating,
  deterministic MCMC seeds and confidence-cutoff recalculation.
