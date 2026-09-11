# spice-lineage recipe

Classic Bioconda/conda-build recipe, version 0.2.0, build 0, staged only.

Source archive:
https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/archive/e6c23ca39f44a47a8351e49d642e977ad8a7f87b.tar.gz

SHA-256: 0102b4896cdb8bcaa4a1bcda22cf373d195b462863c01c0d8408b74c2a00257f

Only Python modules, the version file, seven R resources, distribution metadata,
license and the Conda-generated console entry point are installed. The package
is noarch: python because its payload is interpreted source; R and IQ-TREE
remain platform dependencies resolved by Conda. Phase 5 validates Linux x86_64
only. No native Windows or macOS support is claimed.

BayesTraits is neither a dependency nor a build download. Users supply the
official V4.1.3 executable through --bayestraits_bin, BAYESTRAITS_BIN or PATH.

Before public submission, obtain maintainer release approval and preferably
replace the commit archive with a real reviewed release archive and its
calculated SHA-256. Confirm a recipe maintainer separately. Do not upload this
unreleased staging build. See the repository's docs/distribution.md.
