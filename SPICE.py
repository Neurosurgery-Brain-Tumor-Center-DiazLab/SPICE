#!/usr/bin/env python3
"""
SPICE: Single-cell Plasticity Inference and Clonal Evolution

This module provides a command-line interface with four subcommands:
- filter
- phylogeny
- ancestry
- plasticity
"""

import os
import argparse
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import math
import shutil

PROJECT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"

from scripts.monopogen_filter import *
from scripts.convert_matrix_to_fasta import *
from scripts.IQTREE2 import *

# ------------------------- Subcommand Implementations -------------------------
def run_filter(args: argparse.Namespace) -> None:
    """
    Filter step entrypoint.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments containing input/output paths and thresholds.
    """
    print("[SPICE:filter] Starting filter with arguments:")
    for k, v in vars(args).items():
        print(f"  - {k}: {v}")

    input_directory = args.input_directory
    output_directory = args.output_directory
    sample_id = getattr(args, "sample_id", None) or getattr(args, "prefix", None)
    cell_barcode = args.cell_barcode
    threads = args.threads

    print("[SPICE:filter] Input directory :", input_directory)
    print("[SPICE:filter] Output directory:", output_directory)
    print("[SPICE:filter] Sample ID       :", sample_id)

    # Validate input directory
    if not os.path.isdir(input_directory):
        print(f"Error: The input directory '{input_directory}' does not exist.", file=sys.stderr)
        sys.exit(1)

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_directory):
        try:
            os.makedirs(output_directory, exist_ok=True)
            print(f"Created output directory: '{output_directory}'")
        except Exception as e:
            print(f"Error: Failed to create output directory '{output_directory}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Output directory '{output_directory}' already exists.")

    # Define thresholds with their comparison direction for clearer reporting
    thresholds = {
        "Depth_ref": (args.depth_ref, ">="),
        "Depth_alt": (args.depth_alt, ">="),
        "SVM_pos_score": (args.svm_pos_score, ">="),
        "LDrefine_merged_score": (args.ldrefine_merged_score, ">="),
        "BAF_alt": (args.baf_alt, "<="),
        "min_alt_cells_per_snv": (args.min_alt_cells_per_snv, ">="),
        "min_snvs_per_cell": (args.min_snvs_per_cell, ">="),
    }

    print("\nThresholds for filtering putative SNVs:")
    for key, (value, op) in thresholds.items():
        print(f"  {key}: {op} {value}")

    # ------------------------ Step 1: Check required files ---------------------
    print("\nChecking for required files...")
    try:
        missing = check_monopogen_variants_files(input_directory)
    except NameError:
        print("Error: 'check_monopogen_variants_files' is not implemented. Please provide this helper.", file=sys.stderr)
        sys.exit(2)

    if not missing:
        print("All required files are present for chromosomes 1 through 22.")
    else:
        print("Missing files detected:")
        for chr_key, files in missing.items():
            print(f"{chr_key}:")
            for file in files:
                print(f"  - {file}")
        print("\nPlease ensure all required files are present before proceeding.", file=sys.stderr)
        sys.exit(1)  # Exit if any files are missing

    # -------- Step 2: Load initial cell barcode and index information ----------
    print("\nLoading initial cell barcode and index information from chr1.cell_snv.cellID.csv...")
    try:
        cell_info_dict = load_initial_cell_info(input_directory)
    except NameError:
        print("Error: 'load_initial_cell_info' is not implemented. Please provide this helper.", file=sys.stderr)
        sys.exit(2)

    # --- Step 3: Load filtered cell barcodes from all chromosomes --------------
    print("\nLoading filtered cell barcodes from all chromosomes and identifying common cells...")
    try:
        common_cells = load_filtered_cells(input_directory)
    except NameError:
        print("Error: 'load_filtered_cells' is not implemented. Please provide this helper.", file=sys.stderr)
        sys.exit(2)

    # -------- Step 4: Filter initial info to retain only common cells ----------
    print("\nFiltering initial cell info to retain only common cells...")
    try:
        filtered_cell_info = filter_common_cells(cell_info_dict, common_cells)
    except NameError:
        print("Error: 'filter_common_cells' is not implemented. Please provide this helper.", file=sys.stderr)
        sys.exit(2)

    # --- Step 5: Save filtered common cell barcodes/index information ----------
    print("\nSaving filtered common cell barcodes and index information...")
    try:
        filtered_cells_df = save_filtered_cell_info(filtered_cell_info, sample_id, output_directory)
    except NameError:
        print("Error: 'save_filtered_cell_info' is not implemented. Please provide this helper.", file=sys.stderr)
        sys.exit(2)

    # ---------------- Step 6: Process putativeSNVs.csv files -------------------
    print("\nProcessing putativeSNVs.csv files for all chromosomes...")
    try:
        process_putative_snvs(input_directory, sample_id, output_directory, thresholds)
    except NameError:
        print("Error: 'process_putative_snvs' is not implemented. Please provide this helper.", file=sys.stderr)
        sys.exit(2)

    # ---------------- Step 7: Run R merging script --------------
    print("\nMerging results via R script (monopogen_merge.R)...")
    cmd = ["Rscript", str(SCRIPTS_DIR / "monopogen_merge.R"), input_directory, output_directory, str(sample_id)]
    try:
        subprocess.run(cmd, check=True)
        print("R merge script completed successfully.")
    except FileNotFoundError:
        print("Warning: 'Rscript' not found or 'scripts/monopogen_merge.R' missing. Skipping this step.", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error executing R script: {e}", file=sys.stderr)
        sys.exit(1)

    # ---------------- Step 8: Mutation filter --------------
    print("\nRunning mutation filter R script (mutation_filter.R)...")
    cmd = [
        "Rscript", str(SCRIPTS_DIR / "mutation_filter.R"),
        output_directory, str(sample_id), cell_barcode,
        str(thresholds["min_alt_cells_per_snv"][0]),
        str(thresholds["min_snvs_per_cell"][0]),
        str(threads)
        ]
    try:
        subprocess.run(cmd, check=True)
        print("Mutation filter R script completed successfully.")
    except FileNotFoundError:
        print("Warning: 'Rscript' not found or 'scripts/mutation_filter.R' missing. Skipping this step.", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error executing mutation_filter.R: {e}", file=sys.stderr)
        sys.exit(1)

    # ------------------------- Step 9: Convert to FASTA ------------------------
    print("\nConverting somatic SNV matrix to FASTA...")
    try:
        convert_snv_matrix_to_fasta(output_directory, sample_id)
    except NameError:
        print("Error: 'convert_snv_matrix_to_fasta' is not implemented. Please provide this helper.", file=sys.stderr)
        sys.exit(2)

    print("\nAll processes completed successfully.")


def run_phylogeny(args: argparse.Namespace) -> None:
    """
    Phylogeny step entrypoint.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments including IQ-TREE2 configuration and branch cutting grid.
    """
    print("[SPICE:phylogeny] Starting phylogeny with arguments:")
    for k, v in vars(args).items():
        print(f"  - {k}: {v}")

    # -------------------------------------------------------------------------
    # Validate inputs and derive paths
    # -------------------------------------------------------------------------
    fasta_path = args.fasta_path
    output_directory = args.output_directory
    sample_id = args.prefix

    #fasta_path = Path(output_directory) / f"{sample_id}.SNV_mat.filter.fasta"
    #if not fasta_path.exists():
    if not os.path.exists(fasta_path):
        print(f"Error: FASTA not found: {fasta_path}", file=sys.stderr)
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Build IQ-TREE2 command from CLI args
    #   --model → -m
    #   --uf_bootstrap_replicates → -B
    #   --sh_alrt_replicates → --alrt
    #   --threads → -T
    # -------------------------------------------------------------------------
    model = args.model  
    uf_bootstrap = args.uf_bootstrap_replicates
    sh_alrt = args.sh_alrt_replicates
    threads = args.threads

    cmd = iqtree2_command(
        fasta_path=fasta_path,
        output_directory=output_directory,
        sample_id=sample_id,
        model=model,
        uf_bootstrap=uf_bootstrap,
        sh_alrt=sh_alrt,
        threads=threads,
    )
   
    print("\n[SPICE:phylogeny] IQ-TREE2 command:")
    print("  " + cmd)

    # Also persist a runnable script for reproducibility
    script_path = generate_script(cmd, output_directory, sample_id)
    print(f"[SPICE:phylogeny] Wrote script: {script_path}")

    # -------------------------------------------------------------------------
    # Execute IQ-TREE2
    # -------------------------------------------------------------------------
    try:
        # Use shell=True to allow the command string to be executed as-is.
        # If you prefer list-form without shell, split properly and avoid shell=True.
        subprocess.run(cmd, shell=True, check=True)
        print("[SPICE:phylogeny] IQ-TREE2 finished successfully.")
    except FileNotFoundError:
        print("Error: IQ-TREE2 binary not found. Set IQTREE2_BIN or ensure iqtree2/iqtree is available on PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: IQ-TREE2 failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
   
    # -------------------------------------------------------------------------
    # Post-IQTREE: apply support thresholds and branch-length cut grid
    # -------------------------------------------------------------------------
    print("\n[SPICE:phylogeny] Running BranchSupportCut.R ...")

    # Pull values from CLI args
    uf_support = args.uf_support_threshold      
    sh_support = args.sh_support_threshold
    cut_min    = args.branch_cut_min
    cut_max    = args.branch_cut_max
    cut_step   = args.branch_cut_step
    tip_min    = args.min_tips
    clone_cut_mode = args.clone_cut_mode
    clone_cut_threshold = args.clone_cut_threshold
    min_trusted_ratio = args.min_trusted_ratio
    min_partition_stability = args.min_partition_stability
    stability_window = args.stability_window
    root_method = args.root_method
    outgroup = args.outgroup

    # Validate clone-cut selection options.
    if clone_cut_mode == "manual" and clone_cut_threshold is None:
        print(
            "Error: --clone_cut_mode manual requires --clone_cut_threshold.",
            file=sys.stderr,
        )
        sys.exit(1)

    if clone_cut_threshold is not None and clone_cut_threshold < 0:
        print("Error: --clone_cut_threshold must be >= 0.", file=sys.stderr)
        sys.exit(1)

    if not 0 <= min_trusted_ratio <= 1:
        print("Error: --min_trusted_ratio must be between 0 and 1.", file=sys.stderr)
        sys.exit(1)

    if not 0 <= min_partition_stability <= 1:
        print(
            "Error: --min_partition_stability must be between 0 and 1.",
            file=sys.stderr,
        )
        sys.exit(1)

    if stability_window < 2:
        print("Error: --stability_window must be >= 2.", file=sys.stderr)
        sys.exit(1)

    # Rooting configuration. If an outgroup is explicitly supplied,
    # outgroup rooting takes precedence over --root_method.
    if outgroup:
        root_method = "outgroup"
        outgroup_string = ",".join(outgroup)
        print("[SPICE:phylogeny] Rooting method: outgroup")
        print("[SPICE:phylogeny] Outgroup tip(s): " + ", ".join(outgroup))
    else:
        outgroup_string = "NA"
        if root_method == "outgroup":
            print(
                "Error: --root_method outgroup requires --outgroup.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"[SPICE:phylogeny] Rooting method: {root_method}")

    # Convert optional floats to strings safe for R (NA if None)
    def _num_or_na(x):
        return "NA" if x is None else str(x)

    rscript = "Rscript"
    rprog   = str(SCRIPTS_DIR / "BranchSupportCut.R")
    cmd = [
        rscript, rprog,
        output_directory,            # args[1]
        sample_id,                   # args[2]
        str(int(uf_support)),        # args[3] UF_SUPPORT_THRESHOLD (integer)
        str(int(sh_support)),        # args[4] SH_SUPPORT_THRESHOLD (integer)
        _num_or_na(cut_min),         # args[5] BRANCH_CUT_MIN (double or NA)
        _num_or_na(cut_max),         # args[6] BRANCH_CUT_MAX (double or NA)
        _num_or_na(cut_step),        # args[7] BRANCH_CUT_STEP (double or NA)
        str(int(tip_min)),           # args[8] TIP_THRESHOLD (integer)
        root_method,                 # args[9] ROOT_METHOD
        outgroup_string,             # args[10] OUTGROUP_STRING
        clone_cut_mode,              # args[11] CLONE_CUT_MODE
        _num_or_na(clone_cut_threshold),  # args[12] MANUAL_CLONE_CUT_THRESHOLD
        str(min_trusted_ratio),       # args[13] MIN_TRUSTED_RATIO
        str(min_partition_stability), # args[14] MIN_PARTITION_STABILITY
        str(int(stability_window)),   # args[15] STABILITY_WINDOW
    ]

    try:
        subprocess.run(cmd, check=True)
        print("[SPICE:phylogeny] BranchSupportCut.R finished successfully.")
    except FileNotFoundError:
        print("Error: 'Rscript' not found or 'scripts/BranchSupportCut.R' missing.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: BranchSupportCut.R failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)


def _require_file(path: str, label: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        print(f"Error: {label} not found: {p}", file=sys.stderr)
        sys.exit(1)
    return p


def _resolve_bayestraits_binary(explicit: Optional[str] = None) -> Optional[str]:
    """Resolve BayesTraits from CLI, environment, or PATH."""
    candidates = []
    if explicit:
        candidates.append(explicit)
    env_bin = os.environ.get("BAYESTRAITS_BIN")
    if env_bin:
        candidates.append(env_bin)

    for candidate in candidates:
        expanded = str(Path(candidate).expanduser())
        if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
            return str(Path(expanded).resolve())
        found = shutil.which(candidate)
        if found:
            return found

    for name in ("BayesTraitsV4", "BayesTraitsV4.1.3", "BayesTraits"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _add_qc_options(parser):
    parser.add_argument("--mcmc_seed", type=int, default=12345,
                        help="Base BayesTraits seed; distinct deterministic seeds per chain, retry and permutation")
    parser.add_argument("--rhat_threshold", type=float, default=1.01,
                        help="Modern rank-normalized R-hat must be strictly below this value")
    parser.add_argument("--bulk_ess_threshold", type=float, default=400,
                        help="Minimum bulk ESS for modern convergence QC")
    parser.add_argument("--tail_ess_threshold", type=float, default=400,
                        help="Minimum tail ESS for modern convergence QC")
    parser.add_argument("--max_retries", type=int, default=2,
                        help="Maximum fresh MCMC retries following QC failure; 0 disables retries")
    parser.add_argument("--retry_multiplier", type=float, default=2,
                        help="Multiply iterations and burn-in by this factor per retry")


def _qc_arguments(args):
    if not 1 <= args.mcmc_seed <= 2147483646:
        raise ValueError("--mcmc_seed must be between 1 and 2147483646")
    if args.command == "plasticity" and not 0 <= args.seed <= 2147483646 - args.perm_replicates:
        raise ValueError("--seed plus permutation count must fit a nonnegative R integer")
    if not args.prefix or Path(args.prefix).name != args.prefix or args.prefix in (".", ".."):
        raise ValueError("prefix must be a filename component")
    numeric = (args.rhat_threshold, args.bulk_ess_threshold, args.tail_ess_threshold,
               args.retry_multiplier, args.effective_size_threshold, args.psrf_threshold,
               args.min_ancestral_probability)
    if not all(math.isfinite(x) for x in numeric):
        raise ValueError("QC settings must be finite")
    if (args.rhat_threshold <= 1 or args.bulk_ess_threshold <= 0 or
        args.tail_ess_threshold <= 0 or args.max_retries < 0 or
        args.retry_multiplier <= 1 or args.threads < 1 or
        args.effective_size_threshold <= 0 or args.psrf_threshold <= 1 or
        not 0 <= args.min_ancestral_probability <= 1):
        raise ValueError("Invalid QC thresholds, retry limits, probability, or threads")
    if args.stepping_stones < 0 or args.stone_iterations < 1 or not args.hyperprior.strip():
        raise ValueError("Invalid stepping-stone settings or empty hyperprior")
    if args.command == "ancestry":
        chains, iterations, burnin, period = args.mcmc_chains, args.iterations, args.burnin, args.log_sample_period
    else:
        chains, iterations, burnin, period = args.perm_chains, args.perm_iterations, args.perm_burnin, args.perm_sample_period
    if args.command == "ancestry" or args.perm_replicates > 0:
        if chains < 2 or burnin < 0 or iterations <= burnin or period < 1:
            raise ValueError("QC needs at least two chains, nonnegative burn-in, iterations > burn-in, and positive sample period")
        if iterations // period - burnin // period < 4:
            raise ValueError("At least four retained draws per chain are required")
    return [str(args.rhat_threshold), str(args.bulk_ess_threshold),
            str(args.tail_ess_threshold), str(args.max_retries), str(args.retry_multiplier), str(args.mcmc_seed)]


def run_ancestry(args: argparse.Namespace) -> None:
    """Run BayesTraits MCMC ancestral-state reconstruction for one lineage tree."""
    print("[SPICE:ancestry] Starting ancestry with arguments:")
    for k, v in vars(args).items():
        print(f"  - {k}: {v}")

    tree = _require_file(args.tree, "Lineage tree")
    states = _require_file(args.states, "Cell-state table")
    output_directory = Path(args.output_directory).expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    if args.mcmc_chains < 1:
        print("Error: --mcmc_chains must be >= 1.", file=sys.stderr)
        sys.exit(1)
    if args.iterations <= args.burnin:
        print("Error: --iterations must be greater than --burnin.", file=sys.stderr)
        sys.exit(1)
    if args.log_sample_period < 1:
        print("Error: --log_sample_period must be >= 1.", file=sys.stderr)
        sys.exit(1)
    if not 0 <= args.min_ancestral_probability <= 1:
        print("Error: --min_ancestral_probability must be between 0 and 1.", file=sys.stderr)
        sys.exit(1)

    bayestraits = _resolve_bayestraits_binary(args.bayestraits_bin)
    if bayestraits is None:
        print(
            "Error: BayesTraits executable not found. Use --bayestraits_bin, set "
            "BAYESTRAITS_BIN, or place BayesTraitsV4 on PATH.",
            file=sys.stderr,
        )
        sys.exit(1)

    rprog = SCRIPTS_DIR / "ancestry_core.R"
    cmd = [
        "Rscript", str(rprog),
        str(tree), str(states), str(output_directory), args.prefix, bayestraits,
        str(args.mcmc_chains), str(args.iterations), str(args.burnin),
        str(args.log_sample_period), str(args.stepping_stones),
        str(args.stone_iterations), str(args.effective_size_threshold),
        str(args.psrf_threshold), str(args.min_ancestral_probability),
        str(args.threads),
    ]
    cmd.append(args.hyperprior)
    cmd.extend(_qc_arguments(args))

    print("[SPICE:ancestry] Running ancestry_core.R ...")
    try:
        subprocess.run(cmd, check=True, cwd=str(PROJECT_DIR))
    except FileNotFoundError:
        print("Error: Rscript is not available on PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: ancestry analysis failed with exit code {e.returncode}.", file=sys.stderr)
        sys.exit(e.returncode)

    print(f"[SPICE:ancestry] Completed. Results: {output_directory}")


def run_plasticity(args: argparse.Namespace) -> None:
    """Classify lineage transitions and optionally run a BayesTraits permutation test."""
    print("[SPICE:plasticity] Starting plasticity with arguments:")
    for k, v in vars(args).items():
        print(f"  - {k}: {v}")

    tree = _require_file(args.tree, "Lineage tree")
    states = _require_file(args.states, "Cell-state table")
    ancestral_states = _require_file(args.ancestral_states, "Ancestral-state table")
    state_order = _require_file(args.state_order, "State-order table")

    output_directory = Path(args.output_directory).expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    if args.perm_replicates < 0:
        print("Error: --perm_replicates must be >= 0.", file=sys.stderr)
        sys.exit(1)
    if args.threads < 1:
        print("Error: --threads must be >= 1.", file=sys.stderr)
        sys.exit(1)
    if args.perm_chains < 1:
        print("Error: --perm_chains must be >= 1.", file=sys.stderr)
        sys.exit(1)
    if args.perm_iterations <= args.perm_burnin:
        print("Error: --perm_iterations must be greater than --perm_burnin.", file=sys.stderr)
        sys.exit(1)

    bayestraits = "NA"
    if args.perm_replicates > 0:
        resolved = _resolve_bayestraits_binary(args.bayestraits_bin)
        if resolved is None:
            print(
                "Error: permutation testing requires BayesTraits. Use --bayestraits_bin, "
                "set BAYESTRAITS_BIN, or place BayesTraitsV4 on PATH.",
                file=sys.stderr,
            )
            sys.exit(1)
        bayestraits = resolved

    rprog = SCRIPTS_DIR / "plasticity_core.R"
    cmd = [
        "Rscript", str(rprog),
        str(tree), str(states), str(ancestral_states), str(state_order),
        str(output_directory), args.prefix, bayestraits,
        str(args.perm_replicates), args.sig_direction, str(args.threads),
        str(args.seed), str(args.min_ancestral_probability),
        str(args.perm_chains), str(args.perm_iterations), str(args.perm_burnin),
        str(args.perm_sample_period), str(args.stepping_stones),
        str(args.stone_iterations), str(args.effective_size_threshold),
        str(args.psrf_threshold),
    ]
    cmd.append(args.hyperprior)
    cmd.extend(_qc_arguments(args))

    print("[SPICE:plasticity] Running plasticity_core.R ...")
    try:
        subprocess.run(cmd, check=True, cwd=str(PROJECT_DIR))
    except FileNotFoundError:
        print("Error: Rscript is not available on PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: plasticity analysis failed with exit code {e.returncode}.", file=sys.stderr)
        sys.exit(e.returncode)

    print(f"[SPICE:plasticity] Completed. Results: {output_directory}")


# ------------------------------ Helper Functions ------------------------------
def str_to_bool_strict(val: str) -> bool:
    """
    Convert a string to boolean with strict 'true'/'false' semantics.

    Parameters
    ----------
    val : str
        Expected to be 'true' or 'false' (case-insensitive).

    Returns
    -------
    bool
        Parsed boolean value.

    Raises
    ------
    argparse.ArgumentTypeError
        If value is not one of {'true', 'false'}.
    """
    lv = val.lower()
    if lv in {"true", "t", "1", "yes", "y"}:
        return True
    if lv in {"false", "f", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected a boolean string: 'true' or 'false'.")


def ensure_dir(path: Path) -> None:
    """Create the directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


# --------------------------------- CLI Parser ---------------------------------
def build_parser() -> argparse.ArgumentParser:
    """
    Build the top-level parser and subparsers to match the provided usage text.
    """
    parser = argparse.ArgumentParser(
        prog="python SPICE.py",
        description="SPICE command-line interface",
        add_help=True,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="")

    # ------------------------------- filter -----------------------------------
    p_filter = subparsers.add_parser(
        "filter",
        help="Filter somatic SNVs and cells using quality and model thresholds",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Mandatory positional arguments
    p_filter.add_argument("input_directory", help="Path to the monopogen somatic variants calling output folder")
    p_filter.add_argument("output_directory", help="Path to the directory where outputs will be saved")
    p_filter.add_argument("prefix", help="Identifier to prefix output filenames")
    p_filter.add_argument("cell_barcode", help="File containing cell barcodes to be used in the analysis")

    # Optional arguments
    p_filter.add_argument("--depth_ref", type=int, default=5,
                          help="Minimum threshold for the number of cells supporting the reference allele")
    p_filter.add_argument("--depth_alt", type=int, default=5,
                          help="Minimum threshold for the number of cells supporting the alternative allele")
    p_filter.add_argument("--svm_pos_score", type=float, default=0.1,
                          help="Minimum threshold from the Monopogen SVM module")
    p_filter.add_argument("--ldrefine_merged_score", type=float, default=0.25,
                          help="Minimum threshold from the Monopogen LD refinement module")
    p_filter.add_argument("--baf_alt", type=float, default=0.5,
                          help="Maximum threshold for the alternative allele frequency (BAF)")
    p_filter.add_argument("--min_alt_cells_per_snv", type=int, default=5,
                          help="Minimum number of cells that must support a mutated allele")
    p_filter.add_argument("--min_snvs_per_cell", type=int, default=5,
                          help="Minimum number of somatic SNVs that must be supported")
    p_filter.add_argument("--threads", type=int, default=1,
                          help="Number of threads to use")
    p_filter.set_defaults(func=run_filter)

    # ------------------------------ phylogeny ---------------------------------
    p_phy = subparsers.add_parser(
        "phylogeny",
        help="Infer phylogeny with IQ-TREE2 and apply support/branch filters",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_phy.add_argument("--include_failed_chisq", type=str_to_bool_strict, default=False,
                       choices=[True, False],
                       help="Determines whether to include cells that do not pass the IQTREE2 composition chi-square test")
    p_phy.add_argument("--model", type=str, default="TEST",
                       help="Specifies the model selection option for IQTREE2")
    p_phy.add_argument("--uf_bootstrap_replicates", type=int, default=1000,
                       help="Number of replicates (≥1000) for ultrafast bootstrap analysis")
    p_phy.add_argument("--sh_alrt_replicates", type=int, default=1000,
                       help="Number of replicates (≥1000) to perform the SH-like approximate likelihood ratio test (SH-aLRT)")
    p_phy.add_argument("--uf_support_threshold", type=int, default=90,
                       help="Branch support threshold value to be applied if ultrafast bootstrap is performed")
    p_phy.add_argument("--sh_support_threshold", type=int, default=75,
                       help="Branch support threshold value to be applied if the SH-aLRT is performed")
    p_phy.add_argument("--branch_cut_min", type=float, default=0,
                       help="Minimum value for the branch-length cutting range")
    p_phy.add_argument("--branch_cut_max", type=float, default=0.5,
                       help="Maximum value for the branch-length cutting range")
    p_phy.add_argument("--branch_cut_step", type=float, default=0.01,
                       help="Step size for the branch-length cutting range")
    p_phy.add_argument(
        "--clone_cut_mode",
        choices=["auto", "manual"],
        default="auto",
        help=(
            "How to choose the final incoming branch-length threshold. "
            "'auto' selects a stable, trusted, parsimonious solution; "
            "'manual' uses --clone_cut_threshold."
        ),
    )
    p_phy.add_argument(
        "--clone_cut_threshold",
        type=float,
        default=None,
        help="Final clone-cut threshold when --clone_cut_mode manual is used",
    )
    p_phy.add_argument(
        "--min_trusted_ratio",
        type=float,
        default=0.95,
        help="Minimum trusted-cluster ratio required for automatic threshold selection",
    )
    p_phy.add_argument(
        "--min_partition_stability",
        type=float,
        default=0.95,
        help="Minimum adjacent-threshold Adjusted Rand Index required for automatic selection",
    )
    p_phy.add_argument(
        "--stability_window",
        type=int,
        default=3,
        help="Minimum number of consecutive eligible thresholds defining a stable region",
    )
    p_phy.add_argument("--min_tips", type=int, default=50,
                       help="Threshold for the minimum number of tips in the subclonal phylogenetic tree")
    p_phy.add_argument("--threads", type=int, default=1,
                       help="Number of threads to use")

    p_phy.add_argument(
            "--root_method",
            choices=["midpoint", "outgroup", "none"],
            default="midpoint",
            help=(
                "Tree rooting method. "
                "If --outgroup is provided, outgroup rooting takes precedence. "
                "'none' requires the input tree to already be rooted."
                )
            )
    
    p_phy.add_argument(
        "--outgroup",
        nargs="+",
        default=None,
        help=(
            "One or more tip names to use as outgroup. "
            "Providing this option automatically enables outgroup rooting."
            )
        )

    # Required positional arguments
    p_phy.add_argument("fasta_path", help="")
    p_phy.add_argument("output_directory", help="")
    p_phy.add_argument("prefix", help="")
    p_phy.set_defaults(func=run_phylogeny)

    # ------------------------------ ancestry ----------------------------------
    p_anc = subparsers.add_parser(
        "ancestry",
        help="Infer ancestral cell states on a supplied lineage tree using BayesTraits MCMC",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_anc.add_argument("tree", help="Rooted lineage tree in Newick or NEXUS format")
    p_anc.add_argument("states", help="TSV containing cell_id and state columns")
    p_anc.add_argument("output_directory", help="Directory for ancestry outputs")
    p_anc.add_argument("prefix", help="Identifier used to prefix ancestry output files")
    p_anc.add_argument("--bayestraits_bin", default=None,
                       help="Path/name of BayesTraits executable; otherwise BAYESTRAITS_BIN or PATH is used")
    p_anc.add_argument("--mcmc_chains", type=int, default=3,
                       help="Number of independent MCMC chains")
    p_anc.add_argument("--iterations", type=int, default=1000000,
                       help="MCMC iterations per chain")
    p_anc.add_argument("--burnin", type=int, default=200000,
                       help="Burn-in iterations per chain")
    p_anc.add_argument("--log_sample_period", type=int, default=1000,
                       help="MCMC sampling period")
    p_anc.add_argument("--stepping_stones", type=int, default=10,
                       help="Number of stepping stones; use 0 to disable")
    p_anc.add_argument("--stone_iterations", type=int, default=1000,
                       help="Iterations per stepping stone")
    p_anc.add_argument("--effective_size_threshold", type=float, default=200,
                       help="Minimum ESS used for convergence QC")
    p_anc.add_argument("--psrf_threshold", type=float, default=1.1,
                       help="Maximum Gelman-Rubin PSRF used for convergence QC")
    p_anc.add_argument("--min_ancestral_probability", type=float, default=0.90,
                       help="Minimum posterior probability required to call an internal-node state")
    p_anc.add_argument("--hyperprior", type=str, default="exp 0 10",
                       help="BayesTraits HyperPriorAll specification")
    p_anc.add_argument("--threads", type=int, default=3,
                       help="Maximum number of independent MCMC chains run in parallel")
    _add_qc_options(p_anc)
    p_anc.set_defaults(func=run_ancestry)

    # ------------------------------ plasticity --------------------------------
    p_pl = subparsers.add_parser(
        "plasticity",
        help="Classify state transitions, quantify dedifferentiation-based plasticity, and optionally permute tip states",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_pl.add_argument("tree", help="Rooted lineage tree in Newick or NEXUS format")
    p_pl.add_argument("states", help="TSV containing cell_id and state columns")
    p_pl.add_argument("ancestral_states", help="Ancestral-state TSV produced by SPICE ancestry")
    p_pl.add_argument("state_order", help="TSV containing state and order columns")
    p_pl.add_argument("output_directory", help="Directory for plasticity outputs")
    p_pl.add_argument("prefix", help="Identifier used to prefix plasticity output files")
    p_pl.add_argument("--perm_replicates", type=int, default=1000,
                      help="Number of tip-state permutation replicates; use 0 to skip permutation testing")
    p_pl.add_argument("--sig_direction", choices=["greater", "less", "two-sided"], default="greater",
                      help="Alternative hypothesis for empirical permutation significance")
    p_pl.add_argument("--bayestraits_bin", default=None,
                      help="Path/name of BayesTraits executable used for permutation ancestry runs")
    p_pl.add_argument("--perm_chains", type=int, default=3,
                      help="Number of BayesTraits chains per permutation replicate")
    p_pl.add_argument("--perm_iterations", type=int, default=1000000,
                      help="MCMC iterations per permutation chain")
    p_pl.add_argument("--perm_burnin", type=int, default=200000,
                      help="Burn-in iterations per permutation chain")
    p_pl.add_argument("--perm_sample_period", type=int, default=1000,
                      help="Sampling period for permutation MCMC chains")
    p_pl.add_argument("--stepping_stones", type=int, default=0,
                      help="Number of stepping stones for permutation runs; 0 disables stepping stones")
    p_pl.add_argument("--stone_iterations", type=int, default=1000,
                      help="Iterations per stepping stone when enabled")
    p_pl.add_argument("--effective_size_threshold", type=float, default=200,
                      help="Minimum ESS recorded for permutation ancestry QC")
    p_pl.add_argument("--psrf_threshold", type=float, default=1.1,
                      help="Maximum PSRF recorded when >1 chain is run per permutation")
    p_pl.add_argument("--min_ancestral_probability", type=float, default=0.90,
                      help="Minimum posterior probability required to use an inferred internal-node state")
    p_pl.add_argument("--hyperprior", type=str, default="exp 0 10",
                      help="BayesTraits HyperPriorAll specification")
    p_pl.add_argument("--seed", type=int, default=12345,
                      help="Seed controlling reproducible tip-state shuffling")
    p_pl.add_argument("--threads", type=int, default=1,
                      help="Maximum number of permutation replicates executed in parallel")
    _add_qc_options(p_pl)
    p_pl.set_defaults(func=run_plasticity)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """
    Program entrypoint.

    Parameters
    ----------
    argv : list[str], optional
        Argument vector; defaults to sys.argv[1:] when None.

    Returns
    -------
    int
        Exit status code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        # No subcommand provided
        parser.print_help()
        return 2

    # Ensure output directory exists for subcommands that define it
    if hasattr(args, "output_directory") and args.output_directory:
        ensure_dir(Path(args.output_directory))

    # Dispatch to the selected subcommand
    try:
        args.func(args)
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
