"""Run outside the checkout with only a Conda-installed Python and spice."""
import argparse
from collections import defaultdict
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import unittest

from standard_example import assert_standard_example

R_PACKAGES = ("ape", "coda", "janitor", "posterior", "dplyr", "progress",
              "phangorn", "phytools", "ggplot2", "ggtree", "ggsci")
CLONE_OPTIONS = ["--clone_cut_mode", "manual", "--clone_cut_threshold", "0.10",
                 "--min_tips", "2", "--outgroup", "Ref"]
COMMANDS = []


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command, output, name, error=None):
    command = list(map(str, command))
    start = time.monotonic()
    print("+ " + " ".join(command), flush=True)
    proc = subprocess.run(command, cwd=output, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=900)
    (output / (name + ".log")).write_text(proc.stdout)
    COMMANDS.append({"command": command, "returncode": proc.returncode,
                     "seconds": round(time.monotonic() - start, 2)})
    if error:
        require(proc.returncode != 0 and error in proc.stdout, proc.stdout)
    else:
        require(proc.returncode == 0, proc.stdout[-16000:])
    return proc.stdout


def rows(path, delimiter="\t"):
    with path.open(newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        result = list(reader)
    require(result and all(None not in row and None not in row.values() for row in result),
            f"Empty or malformed table: {path}")
    return result


def partition(out):
    assignments = rows(out / "Clone/synthetic.clone_assignment.tsv")
    require(len(assignments) == 13, "Clone assignments do not cover 13 synthetic tips")
    groups = defaultdict(set)
    seen = set()
    for row in assignments:
        require(row["cell_id"] not in seen, "Duplicate assigned cell")
        seen.add(row["cell_id"])
        if row["cell_id"] == "Ref":
            require(row["clone_id"] == "NA" and row["in_trusted_cluster"] == "FALSE",
                    "Outgroup assigned to trusted clone")
        else:
            require(row["clone_id"] != "NA" and row["in_trusted_cluster"] == "TRUE"
                    and row["clone_status"] == row["clone_id"], "Ingroup trust/status mismatch")
            groups[row["clone_id"]].add(row["cell_id"])
    actual = {frozenset(group) for group in groups.values()}
    require(actual == {frozenset(f"{g}{i}" for i in range(1, 5)) for g in "ABC"},
            "Synthetic three-clone partition not recovered")
    require(rows(out / "Phylo/synthetic.rooting_info.tsv") ==
            [{"sample_id": "synthetic", "root_method": "outgroup", "outgroup": "Ref"}],
            "Incorrect rooting metadata")
    selected = rows(out / "Phylo/synthetic.clone_cut_selection.tsv")
    require(len(selected) == 1 and selected[0]["mode"] == "manual" and
            float(selected[0]["selected_threshold"]) == 0.1, "Incorrect clone cutoff")
    for clone in groups:
        for suffix in ("nwk", "nex"):
            require((out / "Clone" / clone / (clone + "." + suffix)).stat().st_size > 0,
                    "Missing clone export")
    return actual


def provenance(path, expected, package, iqtree, command, success=True):
    record = json.loads(path.read_text())
    require(record["success"] is success and record["command"] == command, "Runtime status")
    require(record["spice_version"] == expected["version"], "Runtime version")
    require(record["source_root"] == str(package), "Source checkout leaked into runtime")
    require(record["source_sha256"] == expected["source_sha256"], "Installed source hashes")
    require(all("unavailable" in record[k] for k in ("git_commit", "git_status")),
            "Installed package associated with a Git checkout")
    require(record["R"]["returncode"] == 0, "R provenance missing")
    require(record["executables"]["BayesTraits"]["path"] is None, "Bundled BayesTraits")
    iq = record["executables"]["IQ-TREE"]
    require(iq["path"] == str(iqtree) and iq["sha256"] == digest(iqtree),
            "IQ-TREE provenance is outside the installed environment")
    if command == "clones":
        require("version_probe" not in iq, "Standalone clones executed IQ-TREE probe")
    else:
        require(iq["version_probe"]["returncode"] == 0 and
                re.search(r"version 2\.", iq["version_probe"]["output"]), "IQ-TREE version")
    return record


def check(inputs, output, prefix):
    from spice_lineage import __version__, cli
    from spice_lineage.paths import PACKAGE_DIR, R_DIR
    expected = json.loads((inputs / "expected.json").read_text())
    require(Path(sys.prefix).resolve() == prefix, "Wrong Python interpreter prefix")
    require(PACKAGE_DIR.is_relative_to(prefix) and "site-packages" in PACKAGE_DIR.parts,
            "SPICE was not imported from the clean Conda environment")
    require(not PACKAGE_DIR.is_relative_to(Path(expected["source_root"])), "Source import")
    spice = Path(shutil.which("spice") or "/missing")
    require(spice == prefix / "bin/spice", "Wrong spice executable on PATH")
    require(importlib.metadata.version("spice-lineage") == __version__ == expected["version"],
            "Version metadata disagreement")
    records = [json.loads(p.read_text()) for p in (prefix / "conda-meta").glob("*.json")]
    require(len([r for r in records if r["name"] == "spice-lineage"]) == 1,
            "SPICE is not a Conda-managed package")
    actual = {"spice_lineage/" + p.relative_to(PACKAGE_DIR).as_posix(): digest(p)
              for p in PACKAGE_DIR.rglob("*") if p.is_file() and
              (p.suffix in (".py", ".R") or p.name == "VERSION")}
    require(actual == expected["source_sha256"], "Python/R resources differ from pinned source")
    require({p.name for p in R_DIR.glob("*.R")} == set(expected["r_files"]),
            "Packaged R resources missing")
    require(not os.environ.get("BAYESTRAITS_BIN"), "Unexpected BayesTraits override")
    for name in ("BayesTraitsV4", "BayesTraitsV4.1.3", "BayesTraits"):
        require(shutil.which(name) is None, "BayesTraits must be externally supplied")
    require(not any("bayestraits" in p.name.lower() for p in (prefix / "bin").iterdir()),
            "BayesTraits executable found in package environment")
    iqtree = Path(shutil.which("iqtree2") or "/missing").resolve()
    require(iqtree.is_relative_to(prefix), "IQ-TREE is outside the clean environment")
    iq_version = run([iqtree, "--version"], output, "iqtree-version")
    require(re.search(r"version 2\.", iq_version), "IQ-TREE 2.x required")
    r_code = ('p <- c(' + ",".join(json.dumps(p) for p in R_PACKAGES) + '); '
              'stopifnot(all(vapply(p,requireNamespace,logical(1),quietly=TRUE))); '
              'cat(R.version.string,"\\n"); '
              'print(sapply(p,function(x) as.character(packageVersion(x))))')
    r_versions = run(["Rscript", "--vanilla", "-e", r_code], output, "r-versions")
    require("R version 4.3." in r_versions, "Untested R major/minor")
    require(run([spice, "--version"], output, "version").strip() == "SPICE " + __version__,
            "Console version")
    run([spice, "--help"], output, "help")
    commands = next(a.choices for a in cli.build_parser()._actions
                    if isinstance(a, argparse._SubParsersAction))
    require(set(commands) == set(expected["subcommands"]), "Commands missing")
    for command in commands:
        run([spice, command, "--help"], output, command + "-help")

    filtered = output / "filter with spaces"
    run([spice, "filter", inputs / "standard", filtered, "example", "--input_format",
         "standard", "--min_alt_cells_per_snv", "2", "--min_snvs_per_cell", "1",
         "--threads", "1"], output, "filter")
    assert_standard_example(unittest.TestCase(), filtered, __version__)
    provenance(filtered / "example.runtime.json", expected, PACKAGE_DIR, iqtree, "filter")

    fixed = output / "fixed clones with spaces"
    tree = inputs / "supported tree.nwk"
    before = digest(tree)
    run([spice, "clones", "--tree", tree, "--output_directory", fixed,
         "--prefix", "synthetic", *CLONE_OPTIONS], output, "fixed-clones")
    partition(fixed)
    require(digest(tree) == before, "Clones modified the read-only input tree")
    provenance(fixed / "synthetic.runtime.json", expected, PACKAGE_DIR, iqtree, "clones")

    combined = output / "phylogeny with spaces"
    run([spice, "phylogeny", inputs / "phylogeny", combined, "synthetic",
         "--input_format", "standard", "--min_alt_cells_per_snv", "1",
         "--min_snvs_per_cell", "1", "--threads", "1", "--model", "JC",
         "--uf_bootstrap_replicates", "1000", "--sh_alrt_replicates", "1000",
         *CLONE_OPTIONS], output, "phylogeny")
    partition(combined)
    require(len(rows(combined / "synthetic.SNV_mat.filter.csv", ",")) == 696,
            "Incorrect retained site count")
    run(["Rscript", "--vanilla", Path(__file__).parent / "verify_trees.R", combined],
        output, "tree-exports")
    provenance(combined / "synthetic.runtime.json", expected, PACKAGE_DIR, iqtree, "phylogeny")
    inferred = combined / "synthetic.fasta.treefile"
    standalone = output / "inferred clones with spaces"
    before = digest(inferred)
    run([spice, "clones", "--tree", inferred, "--output_directory", standalone,
         "--prefix", "synthetic", *CLONE_OPTIONS], output, "inferred-clones")
    require(partition(standalone) == partition(combined), "Combined/standalone partition")
    require(digest(inferred) == before, "Clones modified inferred tree")
    run(["Rscript", "--vanilla", Path(__file__).parent / "verify_clone_equivalence.R",
         combined, standalone], output, "clone-equivalence")
    provenance(standalone / "synthetic.runtime.json", expected, PACKAGE_DIR, iqtree, "clones")

    ancestry = inputs / "ancestry"
    absent = output / "missing BayesTraits"
    error = run([spice, "ancestry", ancestry / "tree.nwk", ancestry / "states.tsv",
                 absent, "missing"], output, "missing-bayestraits",
                error="BayesTraits executable not found")
    require("--bayestraits_bin" in error and "BAYESTRAITS_BIN" in error and "PATH" in error,
            "Missing-tool error lost its recovery instructions")
    provenance(absent / "missing.runtime.json", expected, PACKAGE_DIR, iqtree, "ancestry", False)
    require(not list(absent.rglob("MCMC*")), "Missing-tool path attempted inference")
    return {"status": "pass", "skipped": 0, "spice_version": __version__,
            "spice": str(spice), "import": str(PACKAGE_DIR), "prefix": str(prefix),
            "iqtree_version": iq_version, "r_versions": r_versions,
            "bayestraits": "absent; explicit path/environment/PATH remains external",
            "commands": COMMANDS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--prefix", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        result = check(args.inputs.resolve(), args.output.resolve(), args.prefix.resolve())
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
    finally:
        (args.output / "commands.json").write_text(json.dumps(COMMANDS, indent=2) + "\n")


if __name__ == "__main__":
    main()
