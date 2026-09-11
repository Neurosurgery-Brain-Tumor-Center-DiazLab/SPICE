# Citation and release

[Home](Home.md)

## Current status

The repository version is **0.2.0, unreleased**, after the merged Phase 6 implementation. The Python distribution is `spice-lineage`; its executable is `spice`. A version string or a successful integration test does not itself establish a release or public distribution.

Conda/Bioconda-style recipes, an OCI build definition, Galaxy tools/workflows and a repository-local GTN-style tutorial are staged. No public PyPI, Bioconda, container-registry, SPICE Tool Shed or GTN publication is claimed. The pinned IUC IQ-TREE dependency is separate from publication of SPICE itself.

See [distribution staging](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/distribution.md), [Galaxy staging](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/galaxy.md) and the [changelog](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/CHANGELOG.md) for the existing release preparation record.

## Cite the software used

Follow the existing [CITATION.cff](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/CITATION.cff), which requests the SPICE software version and commit used in an analysis. Its current metadata identifies Bohyeon Yu and version 0.2.0. This documentation redesign does not change that metadata or establish a software-paper citation.

Record the exact SPICE version/commit, relevant dependency versions and analysis settings with your methods. Preserve runtime records and source hashes, especially when an installed package runs outside a Git checkout. See [Outputs and provenance](Outputs-and-Provenance.md).

No DOI is listed in the current citation metadata. Do not invent a DOI, publication date, release tag or software-paper reference.

## Human maintainer decisions before v0.2.0 release

The following decisions require explicit human review:

- Software authorship and contributor attribution.
- Software-note/manuscript authorship and author order.
- Corresponding author/contact for the release or software note.
- Whether and how to archive the release and obtain a DOI.
- Final release metadata and authorization for each publication destination.

Repository metadata is a record to review, not automatic resolution of these decisions. `CITATION.cff` remains unchanged in this documentation PR.

## License

SPICE is licensed under [GPL-3.0-only](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/LICENSE). BayesTraits is separately acquired under its own terms and is not redistributed with SPICE. Retain appropriate citations for upstream methods and software used in your study.
