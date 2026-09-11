# Galaxy

[Home](Home.md) · [Tutorial](Tutorial.md)

SPICE provides five staged native Galaxy tools for Galaxy 25.0+: Filter, Clones, Ancestry, Plasticity and Summarize, each versioned `0.2.0+galaxy0`. They invoke the installed SPICE CLI. Tool Shed and GTN publication remain separate maintainer decisions; this repository does not establish a public SPICE installation on a Galaxy server.

## Workflow and version pin

```text
Filter -> IUC IQ-TREE -> Clones -> mapped Ancestry
                           |           |
                           +-> paired mapped Plasticity -> Summarize
```

The workflow uses the IUC IQ-TREE tool followed by standalone `spice clones`; it does not run `spice phylogeny`.

| Dependency | Pin |
| --- | --- |
| Tool Shed owner/repository | `iuc/iqtree` |
| Revision | `e727e82945af` |
| Tool version | `2.4.0+galaxy2` |
| Tool ID | `toolshed.g2.bx.psu.edu/repos/iuc/iqtree/iqtree/2.4.0+galaxy2` |
| Executable | IQ-TREE 2.4.0 |

The workflow uses DNA, 1,000 SH-aLRT replicates, 1,000 UFBoot replicates and supported `treefile` output, preserving **SH-aLRT / UFBoot** label order. Model defaults to TEST; the workflow explicitly uses BIC to match SPICE's normal invocation. The IUC form initially selects AIC, so check that setting when running modules manually. IQ-TREE 3 is not validated for SPICE.

## Inputs and collection identity

Upload `matrix.tsv`, `variants.tsv` and `cells.tsv` as separate tabular datasets for Filter. Supply a sample-wide states table and an investigator-defined state-order table for downstream steps. See [Input data](Input-Data.md).

Clones exports a list of rooted clone trees with `Clone_N` identifiers. Map Ancestry over that list, sharing the full states table. Map Plasticity over the paired original-tree and ancestry-result lists with identical order and element identifiers. Do not flatten or reorder the lists; tree/state fingerprints and QC are checked for each pair. Every clone tip requires a state, while extra sample cells are ignored.

Summarize uses each plasticity-test collection identifier as the clone ID in its temporary manifest and applies the existing BH correction. Preserve the complete planned family and inspect status/P/q values.

## BayesTraits and installation

A Galaxy administrator must supply BayesTraits on the job execution host through `BAYESTRAITS_BIN` or PATH, including appropriate runtime libraries and job/container propagation. There is no executable-upload parameter. BayesTraits is not redistributed with SPICE.

The current validation setup uses the unpublished local Conda package. Follow the existing [Galaxy administration and validation guide](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/blob/main/docs/galaxy.md) for package channels, exact server/toolchain pins and job configuration. The [workflow files](https://github.com/Neurosurgery-Brain-Tumor-Center-DiazLab/SPICE/tree/main/galaxy/workflows) remain in the main repository.

## Test settings versus study analyses

Tool and workflow defaults match the CLI's production settings: three chains, 1,000,000 iterations, 200,000 burn-in, sampling every 1,000; ancestry uses ten stepping stones, and plasticity requests 1,000 permutations. Automatic clone-cut selection remains the default with no manual threshold.

The committed synthetic exercise explicitly reduces MCMC to two chains, 50,000 iterations, 10,000 burn-in and sampling every 100, with no observed stepping stones and three permutations. It uses manual clone cutoff 0.10, minimum two tips, R-hat < 1.2, bulk/tail ESS ≥ 20 and posterior cutoff 0.5. **These are test-only settings, not recommended settings for a biological study.** Follow the [Tutorial](Tutorial.md) for their exact source and interpretation.
