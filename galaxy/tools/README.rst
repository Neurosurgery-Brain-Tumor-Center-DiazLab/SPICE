SPICE Galaxy tools
==================

SPICE (Single-cell Plasticity Inference and Clonal Evolution) provides five
Galaxy tools around the installed SPICE CLI:

* **Filter**: filter standard-input single-cell variant data.
* **Clones**: discover clones from a supported phylogenetic tree.
* **Ancestry**: infer ancestral states for rooted clone trees.
* **Plasticity**: test plasticity using matching trees, states and ancestry.
* **Summarize**: combine clone-level results with BH/FDR correction.

The wrapper version is ``0.2.0+galaxy0``; the released SPICE software version is
``0.2.0``. The minimum Galaxy version and wrapper profile are ``25.0``.
SPICE is licensed under ``GPL-3.0-only``.

Homepage: https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE

Release citation: Bohyeon Yu and Aaron Diaz, SPICE v0.2.0,
`doi:10.5281/zenodo.22821665 <https://doi.org/10.5281/zenodo.22821665>`_.

Installation and publication status
-----------------------------------

The Galaxy Conda requirement is ``spice-lineage=0.2.0``. It is expected from
Bioconda after `PR #69381
<https://github.com/bioconda/bioconda-recipes/pull/69381>`_ is accepted and
published. Verify public package availability before final Tool Shed deployment.

SPICE is validated with **IQ-TREE 2.4.0**; the canonical Galaxy workflow pins the
corresponding IUC tool. **BayesTraits V4.1.3** must be externally acquired and
administrator-provided on the job execution host through ``BAYESTRAITS_BIN`` or
``PATH``. BayesTraits is not bundled and is not redistributed.

These wrappers are prepared for the intended Tool Shed repository
``diazlab/spice_lineage``. Public Tool Shed deployment and GTN publication remain
pending; this repository state does not establish Tool Shed publication.

See the `Galaxy administration and validation guide
<https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/galaxy.md>`_
and `Galaxy wiki
<https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/wiki/Galaxy>`_
for installation, workflow pins, inputs and interpretation.
