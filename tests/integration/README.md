# Real-tool integration suite

Run `python3 scripts/check_integration.py` from the checkout in the dedicated
Linux environment. Do not run `checks.py` against source or an editable install;
the runner copies it outside Git and supplies the new wheel's executable and
expected provenance.

See [integration testing](../../docs/integration-testing.md) for installation,
official binary checksums, test-only settings, logs and manual GitHub dispatch.
Fixture READMEs document every synthetic group and the intended invariants.
Nothing here is patient data or biological validation.

Files:
- `fixtures/phylogeny/standard/`: explicit 15 x 700 count bundle.
- `fixtures/ancestry/`: explicit rooted twelve-tip tree and two-state annotations.
- `checks.py`: installed CLI, actual output/schema/QC/provenance assertions and
  fast failure checks. It contains no mocked IQ-TREE or BayesTraits execution.
- `verify_trees.R`: independent tree reading/support/export/conversion checks.
- `verify_clone_equivalence.R`: clone export count, tip sets, rooted topology and
  branch lengths compared across combined and standalone paths in both formats.
  `checks.py` also compares complete tables, per-tip status, partitions and
  provenance after moving the inferred tree to an arbitrary name with spaces.

This directory intentionally has no `__init__.py`: the expensive real suite
runs only through its explicit runner, separate from normal unittest discovery.
