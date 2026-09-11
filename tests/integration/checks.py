"""Copied outside Git and executed only by the freshly installed wheel's Python."""
import argparse
import csv
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
EXPECTED = json.loads((HERE / "expected.json").read_text())
SPICE = Path(shutil.which("spice"))
FIXTURES = HERE / "fixtures"
COMMANDS = []
QC = ["--rhat_threshold", "1.2", "--bulk_ess_threshold", "20",
      "--tail_ess_threshold", "20", "--effective_size_threshold", "20",
      "--psrf_threshold", "1.2", "--min_ancestral_probability", "0.5",
      "--max_retries", "1", "--stepping_stones", "0"]
ANCESTRY = ["--mcmc_chains", "2", "--iterations", "50000", "--burnin", "10000",
            "--log_sample_period", "100", "--threads", "1", *QC]
PERM = ["--perm_replicates", "3", "--perm_chains", "2", "--perm_iterations", "50000",
        "--perm_burnin", "10000", "--perm_sample_period", "100", "--threads", "1",
        "--sig_direction", "greater", "--seed", "12345", *QC]


# The same explicit fixture options are used for inference + clones and clones alone.
CLONE_OPTIONS = ["--clone_cut_mode", "manual", "--clone_cut_threshold", "0.10",
                 "--min_tips", "2", "--outgroup", "Ref"]


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def table(path, delimiter="\t"):
    with Path(path).open(newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        require(reader.fieldnames and len(set(reader.fieldnames)) == len(reader.fieldnames),
                f"Missing/duplicate header: {path}")
        rows = list(reader)
        require(all(None not in row and None not in row.values() for row in rows), f"Ragged table: {path}")
        return rows


def one(path):
    rows = table(path)
    require(len(rows) == 1, f"Expected one row: {path}")
    return rows[0]


def settings(path):
    rows = table(path)
    require(all(set(r) == {"parameter", "value"} for r in rows), f"Invalid setting schema: {path}")
    require(len({r["parameter"] for r in rows}) == len(rows), f"Repeated setting: {path}")
    return {r["parameter"]: r["value"] for r in rows}


def number(x, lo=-math.inf, hi=math.inf):
    value = float(x)
    require(math.isfinite(value) and lo <= value <= hi, f"Invalid numeric value: {x}")
    return value


def flag(x):
    require(x in ("TRUE", "FALSE"), f"Invalid logical field: {x}")
    return x == "TRUE"


def run(args, log, *, failed=None, env=None):
    cmd = [str(x) for x in args]
    start = time.monotonic()
    print("+ " + " ".join(cmd), flush=True)
    with log.open("w") as f:
        proc = subprocess.run(cmd, cwd=HERE, env=env, text=True,
                              stdout=f, stderr=subprocess.STDOUT, timeout=900)
    output = log.read_text(errors="replace")
    COMMANDS.append({"command": cmd, "exit_code": proc.returncode,
                     "seconds": round(time.monotonic()-start, 2), "log": str(log)})
    if failed:
        require(proc.returncode != 0 and failed in output,
                f"Expected failure containing {failed!r}: {log}\n{output[-12000:]}")
    else:
        require(proc.returncode == 0, f"Command failed: {log}\n{output[-16000:]}")
    return output


def provenance(path, command, success=True):
    record = json.loads(path.read_text())
    require(record["success"] is success and record["command"] == command, f"Runtime status: {path}")
    require(record["spice_version"] == EXPECTED["version"], "Wrong runtime version")
    require(record["source_sha256"] == EXPECTED["source_sha256"], "Wheel source hash mismatch")
    require("site-packages" in Path(record["source_root"]).parts, "Runtime source not installed")
    for field in ("git_commit", "git_status"):
        require("unavailable" in record[field], "Installed runtime associated with source Git")
    if success:
        require(record["R"]["returncode"] == 0, "Missing R provenance")
    for name in ("IQ-TREE", "BayesTraits"):
        for field in ("path", "sha256"):
            require(record["executables"][name][field] == EXPECTED[name][field],
                    f"Wrong executable provenance: {name} {field}")
    if command == "clones":
        require("version_probe" not in record["executables"]["IQ-TREE"],
                "Standalone clones must not execute even an IQ-TREE version probe")
    else:
        require("version 2.4.0" in record["executables"]["IQ-TREE"]["version_probe"]["output"],
                "Wrong IQ-TREE provenance version")
    if success and command in ("ancestry", "plasticity"):
        require(record["executables"]["BayesTraits"].get("recorded_banner") ==
                EXPECTED["BayesTraits"]["banner"], "BayesTraits banner not retained")
    return record


def phylogeny(out):
    out.mkdir()
    prefix = "synthetic"
    text = run([SPICE, "phylogeny", FIXTURES / "phylogeny/standard", out, prefix,
                "--input_format", "standard", "--min_alt_cells_per_snv", "1",
                "--min_snvs_per_cell", "1", "--threads", "1", "--model", "JC",
                "--uf_bootstrap_replicates", "1000", "--sh_alrt_replicates", "1000",
                *CLONE_OPTIONS], out / "command.log")
    require("IQ-TREE2 finished successfully." in text and
            "BranchSupportCut.R finished successfully." in text, "External steps did not complete")
    original = table(FIXTURES / "phylogeny/standard/matrix.tsv")
    variants = table(FIXTURES / "phylogeny/standard/variants.tsv")
    ids = [r["variant_id"] for r in variants if r["synthetic_block"] != "no_alt_filtered"]
    cells = ["Ref"] + [f"{g}{i}" for g in "ABC" for i in range(1, 5)]
    require(len(original) == 15 and len(variants) == 700, "Fixture dimensions changed")
    filtered = table(out / "synthetic.SNV_mat.filter.csv", ",")
    require([r["Variant_ID"] for r in filtered] == ids and len(ids) == 696, "Incorrect filtered site order")
    require(list(filtered[0]) == ["Variant_ID", *cells], "Incorrect filtered cell order")
    by_cell = {r["cell_id"]: r for r in original}
    require(all(r[c] == by_cell[c][r["Variant_ID"]] for r in filtered for c in cells),
            "Filtering changed REF/ALT counts")
    sequence = {c: "".join(v["alt"] if by_cell[c][v["variant_id"]] == "0/12" else v["ref"]
                           for v in variants if v["variant_id"] in set(ids)) for c in cells}
    expected_fasta = "".join(f">{c}\n{sequence[c]}\n" for c in cells)
    require([s for s in (out / "synthetic.SNV_mat.filter.fasta").read_text().splitlines() if s] ==
            expected_fasta.splitlines(), "Incorrect FASTA")
    require((out / "synthetic.fasta").read_bytes() ==
            (out / "synthetic.SNV_mat.filter.fasta").read_bytes(), "IQ-TREE used wrong alignment")
    for suffix in (".SNV_mat.RDS", ".SNV_mat.input.tsv", ".SNVs.filter.csv", ".selected_cells.tsv"):
        require((out / (prefix + suffix)).stat().st_size > 0, f"Missing filtering evidence: {suffix}")
    require((out / "CellMutationDist.pdf").read_bytes().startswith(b"%PDF"), "R filter plot missing")
    report = (out / "synthetic.fasta.iqtree").read_text()
    require("SH-aLRT" in report and "ultrafast bootstrap" in report.lower(), "Real support report absent")
    root = one(out / "Phylo/synthetic.rooting_info.tsv")
    require(root == {"sample_id": prefix, "root_method": "outgroup", "outgroup": "Ref"}, "Wrong rooting")
    selection = one(out / "Phylo/synthetic.clone_cut_selection.tsv")
    require(selection["mode"] == "manual" and float(selection["selected_threshold"]) == .1,
            "Wrong manual selection")
    sweep = table(out / "Phylo/branch_length_cut_analysis.tsv")
    chosen = [r for r in sweep if flag(r["selected"])]
    require(len(chosen) == 1 and abs(float(chosen[0]["threshold"]) - .1) < 1e-12, "Inconsistent selection")
    for r in sweep:
        require(int(r["n_clusters"]) == int(r["n_trusted"]) + int(r["n_untrusted"]), "Invalid cluster counts")
        require(abs(float(r["pass_ratio"]) - int(r["n_trusted"])/int(r["n_clusters"])) < 1e-12,
                "Invalid trusted fraction")
    assignments = table(out / "Clone/synthetic.clone_assignment.tsv")
    require(len(assignments) == len(cells) and {r["cell_id"] for r in assignments} == set(cells),
            "Clone assignments do not cover retained cells")
    groups = defaultdict(set)
    for row in assignments:
        require(set(row) == {"cell_id", "clone_id", "clone_status", "in_trusted_cluster"}, "Clone schema")
        if row["cell_id"] == "Ref":
            require(row["clone_id"] == "NA" and row["clone_status"] == "untrusted" and
                    not flag(row["in_trusted_cluster"]), "Outgroup assigned a trusted clone")
        else:
            require(flag(row["in_trusted_cluster"]) and row["clone_id"] == row["clone_status"],
                    "Synthetic ingroup not assigned")
            groups[row["clone_id"]].add(row["cell_id"])
    require({frozenset(g) for g in groups.values()} ==
            {frozenset(f"{g}{i}" for i in range(1, 5)) for g in "ABC"}, "Synthetic partition not recovered")
    require(int(chosen[0]["n_exportable"]) == len(groups) == 3, "Export/selection disagreement")
    run(["Rscript", "--vanilla", HERE / "verify_trees.R", out], out / "tree-validation.log")
    provenance(out / "synthetic.runtime.json", "phylogeny")
    return groups


def clone_partition(path):
    rows = table(path)
    require(len({r["cell_id"] for r in rows}) == len(rows), "Duplicate clone assignment tips")
    groups = defaultdict(set)
    for row in rows:
        require(set(row) == {"cell_id", "clone_id", "clone_status", "in_trusted_cluster"},
                "Clone assignment schema changed")
        if flag(row["in_trusted_cluster"]):
            require(row["clone_id"] != "NA" and row["clone_status"] == row["clone_id"],
                    "Trusted clone ID/status disagree")
            groups[row["clone_id"]].add(row["cell_id"])
        else:
            require(row["clone_id"] == "NA" and row["clone_status"] in ("small", "untrusted", "none"),
                    "Unassigned tip status changed")
    # Canonical membership identifies a clone regardless of its arbitrary label.
    return {r["cell_id"]: (frozenset(groups[r["clone_id"]]), "assigned", True)
            if flag(r["in_trusted_cluster"]) else (None, r["clone_status"], False) for r in rows}


def clones(out, combined):
    from spice_lineage.cli import add_clone_options
    out.mkdir()
    external = out.parent / "external IQ-TREE input"
    external.mkdir()
    tree = external / "renamed supported tree.nwk"
    shutil.copyfile(combined / "synthetic.fasta.treefile", tree)
    before = tree.read_bytes()
    # An invalid inference configuration would make iqtree2_command fail. The
    # standalone path must ignore it. Available executables remain discoverable
    # for provenance; no real inference executable is mocked or substituted.
    env = dict(os.environ, IQTREE2_BIN=str(out / "not installed IQ-TREE"))
    text = run([SPICE, "clones", "--tree", tree, "--output_directory", out,
                "--prefix", "synthetic", *CLONE_OPTIONS], out / "command.log", env=env)
    require("BranchSupportCut.R finished successfully." in text, "Standalone R step incomplete")
    require(tree.read_bytes() == before, "Standalone command modified input tree")
    require(not list(out.glob("*.treefile")) and not list(out.glob("*_iqtree2.sh")) and
            not list(out.glob("*.iqtree")) and not list(out.glob("*.fasta")),
            "Standalone clones generated inference artifacts")
    for name in ("synthetic.rooting_info.tsv", "synthetic.clone_cut_selection.tsv",
                 "branch_length_cut_analysis.tsv"):
        require(table(out / "Phylo" / name) == table(combined / "Phylo" / name),
                f"Combined/standalone table mismatch: {name}")
    assignment = "Clone/synthetic.clone_assignment.tsv"
    require(clone_partition(out / assignment) == clone_partition(combined / assignment),
            "Combined/standalone partition or per-tip trust/status mismatch")
    require({p.name for p in (out / "Phylo").iterdir()} ==
            {p.name for p in (combined / "Phylo").iterdir()}, "Phylo output layout changed")
    for path in (out / "Phylo").glob("*.pdf"):
        require(path.read_bytes().startswith(b"%PDF"), f"Missing PDF output: {path}")
    run(["Rscript", "--vanilla", HERE / "verify_clone_equivalence.R", combined, out],
        out / "clone-equivalence.log")
    record = provenance(out / "synthetic.runtime.json", "clones")
    require(record["parameters"]["tree"] == str(tree), "Explicit tree absent from provenance")
    original = provenance(combined / "synthetic.runtime.json", "phylogeny")
    parser = argparse.ArgumentParser()
    add_clone_options(parser)
    for name in vars(parser.parse_args([])):
        require(record["parameters"][name] == original["parameters"][name],
                f"Combined/standalone clone setting differs: {name}")
    # Exercise the existing scientific rooting error and a missing file through
    # the installed command, including failed runtime records.
    bad = out / "missing-outgroup"
    run([SPICE, "clones", "--tree", tree, "--output_directory", bad, "--prefix", "bad",
         "--clone_cut_mode", "manual", "--clone_cut_threshold", "0.10", "--outgroup", "AbsentTip"],
        out / "missing-outgroup.log", failed="outgroup tip(s) were not found in the tree", env=env)
    provenance(bad / "bad.runtime.json", "clones", False)
    missing = out / "missing-tree"
    run([SPICE, "clones", "--tree", external / "absent.nwk", "--output_directory", missing,
         "--prefix", "bad"], out / "missing-tree.log", failed="IQ-TREE tree not found", env=env)
    provenance(missing / "bad.runtime.json", "clones", False)
    print("PASS: standalone arbitrary tree path; complete tables, partitions, tip trust, "
          "clone exports and provenance equivalent", flush=True)


def chains(out, prefix):
    attempts = table(out / f"{prefix}.qc_attempts.tsv")
    final = attempts[-1]
    require(final["status"] == "pass" and flag(final["model_qc_pass"]) and
            int(final["failed_nodes"]) == 0, "Final ancestry QC did not pass")
    qc = settings(out / f"{prefix}.qc_status.tsv")
    require(qc["status"] == "passed" and flag(qc["run_qc_pass"]) and int(qc["chains"]) == 2, "QC status")
    attempt = out / f"{prefix}.attempts" / f"attempt_{int(final['attempt']):02d}"
    require({p.name for p in attempt.glob("MCMC*") if p.is_dir()} == {"MCMC1", "MCMC2"}, "Missing chains")
    for i in (1, 2):
        directory = attempt / f"MCMC{i}"
        stdout = (directory / f"MCMC{i}.stdout.txt").read_text()
        require(stdout.splitlines()[0] == EXPECTED["BayesTraits"]["banner"], "Wrong chain executable")
        commands = (directory / f"MCMC{i}_cmd.txt").read_text().splitlines()
        require(commands[:2] == ["1", "2"] and
                f"Seed {int(final['seed_base']) + i-1}" in commands and
                f"Iterations {final['iterations']}" in commands and
                "Sample 100" in commands and f"LogFile MCMC{i}" in commands and
                not any(x.startswith("Stones") for x in commands),
                "Unexpected chain settings")
        lines = (directory / f"MCMC{i}.Log.txt").read_text().splitlines()
        headers = [n for n, line in enumerate(lines) if line.startswith("Iteration\t")]
        require(len(headers) == 1, "Missing/duplicate BayesTraits log header")
        rows = list(csv.DictReader(lines[headers[0]:], delimiter="\t"))
        iterations = [int(r["Iteration"]) for r in rows if int(r["Iteration"]) > int(final["burnin"])]
        require(iterations == list(range(int(final["burnin"])+100, int(final["iterations"])+1, 100)),
                "Incomplete retained chain grid")
    diag = table(out / f"{prefix}.mcmc_diagnostics.tsv")
    require(diag and all(flag(r["qc_pass"]) and int(r["chains"]) == 2 and
                        int(r["draws_per_chain"]) >= 400 for r in diag), "Incomplete/passing diagnostics")
    require(any(r["scope"] == "model" for r in diag) and any(r["scope"] == "node" for r in diag), "QC scope")
    for row in diag:
        if row["diagnostic_status"] == "constant_consistent":
            require(row["scope"] == "node" and not flag(row["diagnostic_available"]), "Invalid constant exception")
            number(row["constant_value"], 0, 1)
        else:
            require(row["diagnostic_status"] == "pass" and number(row["Rhat"], 0) < 1.2, "Rhat")
            number(row["ESS_bulk"], 20); number(row["ESS_tail"], 20); number(row["MCSE_mean"], 0)
    return attempt


def ancestry(out, seed, tree=None):
    out.mkdir()
    fixture = FIXTURES / "ancestry"
    tree = tree or fixture / "tree.nwk"
    original_tree = tree.read_bytes()
    run([SPICE, "ancestry", tree, fixture / "states.tsv", out, "synthetic",
         "--mcmc_seed", seed, *ANCESTRY], out / "command.log")
    attempt = chains(out, "synthetic")
    mapping = table(out / "synthetic.state_mapping.tsv")
    require(mapping == [{"state": "Differentiated", "state_code": "0"},
                        {"state": "Progenitor", "state_code": "1"}], "State coding changed")
    states = {r["cell_id"]: r["state"] for r in table(fixture / "states.tsv")}
    with (out / "synthetic.bayestraits_traits.tsv").open() as f:
        traits = list(csv.reader(f, delimiter="\t"))
    require([r[0] for r in traits] == [f"{g}{i}" for g in "abc" for i in range(1,5)], "Tip reconciliation order")
    require({c: {"0": "Differentiated", "1": "Progenitor"}[s] for c,s in traits} == states,
            "Trait reconciliation changed states")
    rows = table(out / "synthetic.ancestral_states.tsv")
    require(len(rows) == 11 and {r["node_id"] for r in rows} == {f"T{i}" for i in range(1,12)}, "Internal nodes")
    require(tree.read_bytes() == original_tree, "Ancestry modified the supplied tree")
    for row in rows:
        require(row["tree_md5"] == hashlib.md5(original_tree).hexdigest(), "Original tree fingerprint lost")
        require(row["node_id"] == "T" + row["node_number"] and
                row["qc_policy"] == "constant-probabilities-v1", "Ancestry identifiers/policy")
        probs = [number(row["posterior_state_" + s], 0, 1) for s in ("0", "1")]
        require(abs(sum(probs)-1) < 5e-6, "Posterior probabilities do not sum to one")
        p = number(row["posterior_probability"], 0, 1)
        require(abs(p-max(probs)) < 1e-12 and p == float(row["posterior_state_" + row["inferred_state_code"]]),
                "Posterior call inconsistent")
        require(row["inferred_state"] == {"0":"Differentiated","1":"Progenitor"}[row["inferred_state_code"]],
                "Called state/code mismatch")
        number(row["posterior_q025"], 0, p); number(row["posterior_q975"], p, 1)
        require(flag(row["confident"]) == (p >= .5) and flag(row["run_qc_pass"]) and
                flag(row["node_qc_pass"]) and flag(row["usable"]) == flag(row["confident"]), "Confidence/QC gating")
    run(["Rscript", "--vanilla", HERE / "verify_trees.R", out, tree,
         attempt / "synthetic.bayestraits_tree.nex"], out / "nexus-validation.log")
    provenance(out / "synthetic.runtime.json", "ancestry")
    return out / "synthetic.ancestral_states.tsv"



def labeled_tree_ancestry(out, reference):
    """Real V4 regression: support metadata must not become taxa in its parser."""
    out.mkdir()
    nwk = out / "dual supports.nwk"
    nwk.write_text((FIXTURES / "ancestry/tree.nwk").read_text().replace(")", ")95.6/99"))
    nex = out / "dual supports.nex"
    run(["Rscript", "--vanilla", "-e",
         "a<-commandArgs(TRUE); ape::write.nexus(ape::read.tree(a[1]),file=a[2],digits=17)",
         nwk, nex], out / "fixture-nexus.log")
    expected = [{k:v for k,v in row.items() if k != "tree_md5"} for row in table(reference)]
    for fmt, tree in [("newick", nwk), ("nexus", nex)]:
        result = ancestry(out / fmt, 12345, tree)
        actual = [{k:v for k,v in row.items() if k != "tree_md5"} for row in table(result)]
        require(actual == expected, "Support-label serialization changed seeded ancestry results")


def plasticity(out, anc, seed):
    out.mkdir()
    fixture = FIXTURES / "ancestry"
    args = [SPICE, "plasticity", fixture / "tree.nwk", fixture / "states.tsv", anc,
            fixture / "state_order.tsv", out, "synthetic", "--mcmc_seed", seed, *PERM]
    run(args, out / "command.log")
    transitions = table(out / "synthetic.transitions.tsv")
    require(len(transitions) == 22 and {int(r["edge_id"]) for r in transitions} == set(range(1,23)),
            "Incomplete transition table")
    order = {"Progenitor": 1, "Differentiated": 2}
    for row in transitions:
        require(set(row) == {"edge_id", "parent_node", "child_node", "parent_state", "child_state",
                             "parent_probability", "child_probability", "transition"}, "Transition schema")
        parent = number(row["parent_probability"], 0, 1)
        child = number(row["child_probability"], 0, 1)
        direction = order[row["child_state"]] - order[row["parent_state"]]
        expected = "uncertain" if min(parent,child) < .5 else (
            "differentiation" if direction > 0 else "dedifferentiation" if direction < 0 else "self-renewal")
        require(row["transition"] == expected, "Incorrect transition classification")
    summary = one(out / "synthetic.plasticity.tsv")
    counts = Counter(r["transition"] for r in transitions)
    for label in ("self-renewal","differentiation","dedifferentiation","uncertain"):
        require(int(summary[label.replace("-","_")]) == counts[label], "Summary transition count")
    informative = 22 - counts["uncertain"]
    require(int(summary["informative_transitions"]) == informative and int(summary["total_edges"]) == 22,
            "Summary denominator")
    observed = number(summary["cellular_plasticity"], 0, 100)
    require(abs(observed - 100*counts["dedifferentiation"]/informative) < 1e-10, "Plasticity score")
    test = one(out / "synthetic.plasticity_test.tsv")
    require(test["test_status"] == "pass" and test["alternative"] == "greater" and
            test["n_permutations_requested"] == test["n_permutations_successful"] == "3", "Permutation summary")
    perms = table(out / "synthetic.permutation_plasticity.tsv")
    require(len(perms) == 3 and {r["permutation"] for r in perms} == {"1","2","3"} and
            all(r["status"] == "ok" for r in perms), "Incomplete permutations")
    null = [number(r["plasticity"], 0, 100) for r in perms]
    p = number(test["empirical_p"], 0, 1)
    require(abs(p - (1 + sum(v >= observed for v in null))/4) < 1e-12, "Empirical P-value contract")
    info = settings(out / "synthetic.plasticity_run_info.tsv")
    require(info["permutation_replicates"] == "3" and info["alternative"] == "greater", "Run settings")
    for i in (1,2,3):
        chains(out / "synthetic.permutations" / f"perm_{i:04d}", f"Perm_{i}")
    provenance(out / "synthetic.runtime.json", "plasticity")
    manifest = out / "summary-manifest.tsv"
    manifest.write_text("clone_id\tplasticity_test\nsynthetic\tsynthetic.plasticity_test.tsv\n")
    run([SPICE, "summarize", manifest, out / "summary.tsv"], out / "summary-command.log")
    summary = one(out / "summary.tsv")
    require(summary["test_status"] == "pass" and float(summary["q_value"]) == p, "Installed summary bridge")
    provenance(out / "summary.tsv.runtime.json", "summarize")
    return args


def negative(out, anc):
    out.mkdir()
    fixture = FIXTURES / "ancestry"
    mismatch = out / "missing-tip.tsv"
    rows = (fixture / "states.tsv").read_text().splitlines()
    mismatch.write_text("\n".join(rows[:-1]) + "\n")
    mismatch_out = out / "mismatch"
    run([SPICE,"ancestry",fixture / "tree.nwk",mismatch,mismatch_out,"bad",*ANCESTRY],
        out / "mismatch.log", failed="Missing state annotation")
    require(not list(mismatch_out.rglob("MCMC*.stdout.txt")), "Tip mismatch reached BayesTraits")
    provenance(mismatch_out / "bad.runtime.json", "ancestry", False)
    failed_anc = out / "failed-qc.tsv"
    rows = table(anc)
    for row in rows:
        row["run_qc_pass"] = "FALSE"
    with failed_anc.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    run([SPICE,"plasticity",fixture / "tree.nwk",fixture / "states.tsv",failed_anc,
         fixture / "state_order.tsv",out / "failed-qc","bad","--perm_replicates","0",*QC],
        out / "failed-qc.log", failed="Ancestry model QC failed")
    require(not (out / "failed-qc/bad.plasticity_test.tsv").exists(), "Failed QC published significance")
    # Real invalid executable path, rejected before inference. No substitute executable.
    env = dict(os.environ, IQTREE2_BIN=str(out / "absent-iqtree"))
    fasta = out / "input.fasta"
    fasta.write_text(">a\nACGT\n>b\nACGA\n>c\nTCGA\n>d\nTCGT\n")
    run([SPICE,"phylogeny",fasta,out / "missing-tool","bad"],out / "missing-tool.log",
        failed="IQTREE2_BIN is set but is not a valid executable",env=env)


def main():
    from spice_lineage.paths import PACKAGE_DIR
    require(PACKAGE_DIR.is_relative_to(Path(sys.prefix)) and "site-packages" in PACKAGE_DIR.parts and
            not PACKAGE_DIR.is_relative_to(Path(EXPECTED["source_root"])), "Source import leaked into integration")
    require(SPICE == Path(sys.prefix) / "bin/spice", "Wrong spice console executable")
    dist = importlib.metadata.distribution("spice-lineage")
    direct = json.loads(dist.read_text("direct_url.json"))
    require("dir_info" not in direct and unquote(urlparse(direct["url"]).path) == EXPECTED["wheel"],
            "Installation is not the newly built non-editable wheel")
    require(direct["archive_info"]["hashes"]["sha256"] == EXPECTED["wheel_sha256"], "Installed wheel hash")
    print(f"Wheel import: {PACKAGE_DIR}; spice: {SPICE}", flush=True)
    for i in range(1,EXPECTED["repeats"]+1):
        out = HERE / f"run_{i:02d}"
        out.mkdir()
        phylogeny(out / "phylogeny with spaces")
        clones(out / "clones with spaces", out / "phylogeny with spaces")
        anc = ancestry(out / "ancestry with spaces", 12345 + (i-1)*1000)
        plasticity(out / "plasticity with spaces", anc, 12345 + (i-1)*1000)
        if i == 1:
            labeled_tree_ancestry(out / "labeled tree ancestry", anc)
            negative(out / "negative", anc)
    report = {"status": "pass", "skipped": 0, "repeats": EXPECTED["repeats"],
              "spice": str(SPICE), "import": str(PACKAGE_DIR),
              "clone_equivalence": "pass", "arbitrary_tree_path": "pass",
              "labeled_tree_ancestry": "pass",
              "IQ-TREE": EXPECTED["IQ-TREE"], "BayesTraits": EXPECTED["BayesTraits"], "commands": COMMANDS}
    (HERE / "results.json").write_text(json.dumps(report,indent=2))
    print("PASS: IQ-TREE / standalone clone equivalence / ancestry / 3 permutations / summary / failure paths",flush=True)


if __name__ == "__main__":
    try:
        main()
    finally:
        (HERE / "commands.json").write_text(json.dumps(COMMANDS,indent=2))
