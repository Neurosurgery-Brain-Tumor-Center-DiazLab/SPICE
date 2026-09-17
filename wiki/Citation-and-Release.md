# Citation and release

[Home](Home.md)

## Current status

Current software version: **0.2.0**. The Python distribution is `spice-lineage`; its executable is `spice`. A version string or a successful integration test does not itself establish a release or public distribution.

Bioconda, BioContainer, Galaxy Tool Shed, GTN, PyPI and other public distribution channels are published separately and should only be documented as available after verification. The repository supplies Conda/OCI staging definitions, native Galaxy tools/workflows and a GTN-style tutorial draft. The pinned IUC IQ-TREE dependency is separate from publication of SPICE itself.

See the [release notes](../docs/releases/v0.2.0.md), [changelog](../CHANGELOG.md), [distribution staging](../docs/distribution.md) and [Galaxy staging](../docs/galaxy.md).

## Cite the software used

Follow [CITATION.cff](../CITATION.cff), which records version 0.2.0 and the maintainer-approved SPICE software authors, in order:

1. Bohyeon Yu — [ORCID 0000-0002-1892-7790](https://orcid.org/0000-0002-1892-7790).
2. Aaron Diaz — [ORCID 0000-0001-9059-9501](https://orcid.org/0000-0001-9059-9501).

Record the exact SPICE version/commit, relevant dependency versions and analysis settings with your methods. Preserve runtime records and source hashes, especially when an installed package runs outside a Git checkout. See [Outputs and provenance](Outputs-and-Provenance.md).

No DOI or release date is recorded in the current citation metadata. Software-note/manuscript authorship, corresponding contact, archival DOI and authorization for each publication destination remain human maintainer decisions.

## Release review and publication

The release-candidate PR must be reviewed and merged by a maintainer before a separate tagging step is authorized. A release candidate is not frozen by passing validation alone. After the actual `v0.2.0` tag exists, the public Bioconda recipe must use that tag archive and its calculated SHA-256; the current immutable staging source remains for local validation until then.

## License

SPICE is licensed under [GPL-3.0-only](../LICENSE). BayesTraits is separately acquired under its own terms and is not redistributed with SPICE. Retain appropriate citations for upstream methods and software used in your study.
