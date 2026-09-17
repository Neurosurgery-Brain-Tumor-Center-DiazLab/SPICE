# Bioconda staging area

Copy the entire **spice-lineage/** directory into
**bioconda-recipes/recipes/spice-lineage/** only during a separately authorized
public submission. The package-named directory follows Bioconda's folder-name
lint rule. The recipe is classic **meta.yaml**, not an experimental format.

This stages **0.2.0, build 0** for local validation. The source is an immutable
tested serialization-fix commit archive, verified with SHA-256; it does not
follow main. After the actual `v0.2.0` tag exists, finalize the public recipe
with that tag archive and its calculated SHA-256. Public package and
BioContainer availability must be verified separately.

See [distribution.md](../../docs/distribution.md) for local build commands,
dependency policy, validation, evidence and the eventual submission checklist.
No recipe-maintainer account is invented: the repository author metadata does
not establish a consenting Bioconda maintainer's GitHub handle.
