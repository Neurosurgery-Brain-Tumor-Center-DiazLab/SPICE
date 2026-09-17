# spice-lineage recipe

Classic Bioconda/conda-build recipe, version 0.2.0, build 0, staged only.

Source archive:
https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/archive/d0570d923d7880139a3f4c0a7a2b2e7ce65bc307.tar.gz

SHA-256: 47ab47321d96bb09c5c2089a0155a029e415610929fef43aa8522f51d6fb703b

Only Python modules, the version file, seven R resources, distribution metadata,
license and the Conda-generated console entry point are installed. The package
is noarch: python because its payload is interpreted source; R and IQ-TREE
remain platform dependencies resolved by Conda. Distribution validation covers Linux x86_64
only. No native Windows or macOS support is claimed.

BayesTraits is neither a dependency nor a build download. Users supply the
official V4.1.3 executable through --bayestraits_bin, BAYESTRAITS_BIN or PATH.

After the maintainer-authorized `v0.2.0` tag exists, replace this older staging
source in the public recipe with the actual tag archive and its calculated
SHA-256. Preserve the current valid source/checksum until then. Confirm a
recipe maintainer and submission authorization separately. Do not upload the
staging build. See [distribution guidance](../../../docs/distribution.md).
