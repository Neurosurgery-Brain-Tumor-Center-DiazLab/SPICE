# SPICE user guide

<img src="https://raw.githubusercontent.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/main/SPICE.png" alt="SPICE" width="300">

**SPICE: Single-cell Plasticity Inference and Clonal Evolution** combines somatic SNV filtering, phylogenetic inference and subclone classification, ancestral cell-state reconstruction, and cellular plasticity analysis. It uses IQ-TREE for lineage inference and BayesTraits MultiState MCMC to estimate ancestral states. Ordered cell states then define self-renewal, differentiation, and dedifferentiation along lineage edges.

This repository-local wiki is the canonical, version-controlled user documentation. It describes the post-Phase-6 implementation, version **0.2.0 (unreleased)**. It may later be mirrored to the GitHub Wiki; no mirror or publication is implied.

## Start here

| Task | Guide |
| --- | --- |
| Install SPICE and its external tools | [Installation](Installation.md) |
| Prepare counts, metadata, trees and cell states | [Input data](Input-Data.md) |
| Choose an entry point and run the pipeline | [Workflow](Workflow.md) |
| Understand rooting, support and clone selection | [Clone inference](Clone-Inference.md) |
| Reconstruct states and quantify plasticity | [Ancestry and plasticity](Ancestry-and-Plasticity.md) |
| Run the staged Galaxy tools | [Galaxy](Galaxy.md) |
| Interpret files, diagnostics and provenance | [Outputs and provenance](Outputs-and-Provenance.md) |
| Assess what an analysis can establish | [Scientific assumptions and limitations](Scientific-Assumptions-and-Limitations.md) |
| Try a synthetic exercise | [Tutorial](Tutorial.md) |
| Cite an analysis and check release status | [Citation and release](Citation-and-Release.md) |

## Choose an input route

Start from a standard count bundle or import prepared Monopogen results, then run `filter` and `phylogeny`. Alternatively, use `clones` on an existing supported IQ-TREE tree. Prepared external lineage/clone trees enter directly at `ancestry`.

Analyze one rooted clone tree at a time, supplying cell-state annotations for ancestry and an investigator-defined state order for plasticity. Summarize the planned family of clone tests together. Read the [workflow](Workflow.md) and [scientific limitations](Scientific-Assumptions-and-Limitations.md) before interpreting inferred ancestors or plasticity values.

Detailed engineering, packaging and validation records remain in the repository's [docs directory](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/tree/main/docs). The [source repository](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE) contains the code, examples and staged Galaxy workflow.
