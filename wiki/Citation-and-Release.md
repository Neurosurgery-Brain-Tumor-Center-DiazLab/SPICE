# Citation and release

[Home](Home.md)

## Current status

SPICE **v0.2.0 has been tagged, released and archived on Zenodo**. The Python distribution is `spice-lineage`; its executable is `spice`.

Bioconda, BioContainer, Galaxy Tool Shed, GTN, PyPI and other public distribution channels are published separately and should only be documented as available after verification. The repository supplies Conda/OCI staging definitions, native Galaxy tools/workflows and a GTN-style tutorial draft. The pinned IUC IQ-TREE dependency is separate from publication of SPICE itself.

See the [release notes](../docs/releases/v0.2.0.md), [changelog](../CHANGELOG.md), [distribution staging](../docs/distribution.md) and [Galaxy staging](../docs/galaxy.md).

## Cite the software used

Follow [CITATION.cff](../CITATION.cff), which records version 0.2.0 and the maintainer-approved SPICE software authors, in order:

1. Bohyeon Yu — [ORCID 0000-0002-1892-7790](https://orcid.org/0000-0002-1892-7790).
2. Aaron Diaz — [ORCID 0000-0001-9059-9501](https://orcid.org/0000-0001-9059-9501).

Record the exact SPICE version/commit, relevant dependency versions and analysis settings with your methods. Preserve runtime records and source hashes, especially when an installed package runs outside a Git checkout. See [Outputs and provenance](Outputs-and-Provenance.md).

- **v0.2.0 version-specific DOI:** [10.5281/zenodo.22821665](https://doi.org/10.5281/zenodo.22821665). Use this DOI for the software note and reproducible citation of the exact v0.2.0 software artifact; it is recorded in `CITATION.cff`.
- **Concept/repository DOI:** [10.5281/zenodo.22821664](https://doi.org/10.5281/zenodo.22821664). This DOI covers the SPICE release series and is not a substitute for the version-specific DOI when citing v0.2.0.

Software-note/manuscript authorship, corresponding contact and authorization for each publication destination remain human maintainer decisions.

## Release and separate publication channels

The [v0.2.0 GitHub Release](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/releases/tag/v0.2.0) is published. The immutable `v0.2.0` tag points to `5ebc4aec5df7df6c2e9cdb60c1259a2898e3e19f` and must not be altered. The Bioconda recipe now uses that released tag archive with its finalized SHA-256 and is ready for external submission to `bioconda/bioconda-recipes`. Bioconda acceptance and publication have not occurred; see [distribution guidance](../docs/distribution.md).

## License

SPICE is licensed under [GPL-3.0-only](../LICENSE). BayesTraits is separately acquired under its own terms and is not redistributed with SPICE. Retain appropriate citations for upstream methods and software used in your study.
