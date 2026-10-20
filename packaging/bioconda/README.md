# Bioconda staging area

The upstream **bioconda-recipes/recipes/spice-lineage/** recipe has merged.
Keep this **spice-lineage/** directory as the local-build regression reference;
any future upstream recipe change requires separate authorization. The
package-named directory follows Bioconda's folder-name lint rule. The recipe
is classic **meta.yaml**, not an experimental format.

The **spice-lineage 0.2.0, build 0** recipe now targets the released immutable
`v0.2.0` tag at commit `5ebc4aec5df7df6c2e9cdb60c1259a2898e3e19f`.
The tag archive's SHA-256 is finalized in
[the recipe README](spice-lineage/README.md). [Bioconda PR #69381](https://github.com/bioconda/bioconda-recipes/pull/69381)
merged on 2026-10-18 Pacific. Public build `pyhdfd78af_0` passed fresh Linux
installation and release-payload validation on 2026-10-19. See the [evidence](../../docs/public-distribution-validation-2026-10-19.md);
public BioContainer verification remains incomplete. The recipe is unchanged.

See [distribution.md](../../docs/distribution.md) for local build commands,
dependency policy, validation, evidence and the eventual submission checklist.
No recipe-maintainer account is invented: the repository author metadata does
not establish a consenting Bioconda maintainer's GitHub handle.
