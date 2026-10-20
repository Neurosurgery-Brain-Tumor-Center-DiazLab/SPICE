# spice-lineage recipe

Classic Bioconda/conda-build recipe, version 0.2.0, build 0.
[Bioconda PR #69381](https://github.com/bioconda/bioconda-recipes/pull/69381) merged.
Public build `pyhdfd78af_0` passed fresh Linux installation and release-payload
validation on 2026-10-19; see the [evidence](../../../docs/public-distribution-validation-2026-10-19.md).

Source archive:
https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/archive/refs/tags/v0.2.0.tar.gz

SHA-256: 48d67b1e5300203d5ce953f2bea25b958772d1887ed8ad1b83f31ce6ced71236

Only Python modules, the version file, seven R resources, distribution metadata,
license and the Conda-generated console entry point are installed. The package
is noarch: python because its payload is interpreted source; R and IQ-TREE
remain platform dependencies resolved by Conda. Distribution validation covers Linux x86_64
only. No native Windows or macOS support is claimed.

BayesTraits is neither a dependency nor a build download. Users supply the
official V4.1.3 executable through --bayestraits_bin, BAYESTRAITS_BIN or PATH.

The source is the released immutable `v0.2.0` tag, dereferencing to
`5ebc4aec5df7df6c2e9cdb60c1259a2898e3e19f`. The archive checksum above was
calculated from that tag archive and is finalized. Keep the tag unchanged.
The published upstream recipe lists `diazlab` as recipe maintainer. This
validation changes neither the recipe nor the public package. See
[distribution guidance](../../../docs/distribution.md).
