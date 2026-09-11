#!/usr/bin/env python3
"""
SPICE: Single-cell Plasticity Inference and Clonal Evolution

This module provides a command-line interface with modular subcommands:
- import-monopogen
- filter
- phylogeny
- clones
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
import shlex
import tempfile
from .runtime_info import VERSION, capture_runtime, save_runtime
from .summarize_clones import run_summary

from .paths import PACKAGE_DIR, R_DIR

PROJECT_DIR = PACKAGE_DIR
SCRIPTS_DIR = R_DIR

from .standard_input import load_bundle, select_quality, read_table, write_table
from .import_monopogen import import_monopogen
from .convert_matrix_to_fasta import *
from .IQTREE2 import *

# ------------------------- Subcommand Implementations -------------------------
def add_filter_options(parser):
    parser.add_argument("--depth_ref", type=int, default=5,
                          help="Minimum value of the variant Depth_ref metadata field")
    parser.add_argument("--depth_alt", type=int, default=5,
                          help="Minimum value of the variant Depth_alt metadata field")
    parser.add_argument("--svm_pos_score", type=float, default=0.1,
                          help="Minimum threshold from the Monopogen SVM module")
    parser.add_argument("--ldrefine_merged_score", type=float, default=0.25,
                          help="Minimum threshold from the Monopogen LD refinement module")
    parser.add_argument("--baf_alt", type=float, default=0.5,
                          help="Maximum threshold for the alternative allele frequency (BAF)")
    parser.add_argument("--min_alt_cells_per_snv", type=int, default=5,
                          help="Minimum number of cells that must support a mutated allele")
    parser.add_argument("--min_snvs_per_cell", type=int, default=5,
                          help="Minimum number of somatic SNVs that must be supported")
    parser.add_argument('--variant_qc', choices=['auto', 'metadata', 'none'], default='auto', help='auto uses all six QC metadata fields when present; metadata requires them; none skips metadata QC')


def add_clone_options(parser):
    """One set of clone/rooting options and defaults for both tree entry points."""
    parser.add_argument("--uf_support_threshold", type=int, default=90,
                       help="Branch support threshold value to be applied if ultrafast bootstrap is performed")
    parser.add_argument("--sh_support_threshold", type=int, default=75,
                       help="Branch support threshold value to be applied if the SH-aLRT is performed")
    parser.add_argument("--branch_cut_min", type=float, default=0,
                       help="Minimum value for the branch-length cutting range")
    parser.add_argument("--branch_cut_max", type=float, default=0.5,
                       help="Maximum value for the branch-length cutting range")
    parser.add_argument("--branch_cut_step", type=float, default=0.01,
                       help="Step size for the branch-length cutting range")
    parser.add_argument(
        "--clone_cut_mode",
        choices=["auto", "manual"],
        default="auto",
        help=(
            "How to choose the final incoming branch-length threshold. "
            "'auto' selects a stable, trusted, parsimonious solution; "
            "'manual' uses --clone_cut_threshold."
        ),
    )
    parser.add_argument(
        "--clone_cut_threshold",
        type=float,
        default=None,
        help="Final clone-cut threshold when --clone_cut_mode manual is used",
    )
    parser.add_argument(
        "--min_trusted_ratio",
        type=float,
        default=0.95,
        help="Minimum trusted-cluster ratio required for automatic threshold selection",
    )
    parser.add_argument(
        "--min_partition_stability",
        type=float,
        default=0.95,
        help="Minimum adjacent-threshold Adjusted Rand Index required for automatic selection",
    )
    parser.add_argument(
        "--stability_window",
        type=int,
        default=3,
        help="Minimum number of consecutive eligible thresholds defining a stable region",
    )
    parser.add_argument("--min_tips", type=int, default=50,
                       help="Threshold for the minimum number of tips in the subclonal phylogenetic tree")

    parser.add_argument(
            "--root_method",
            choices=["midpoint", "outgroup", "none"],
            default="midpoint",
            help=(
                "Tree rooting method. "
                "If --outgroup is provided, outgroup rooting takes precedence. "
                "'none' requires the input tree to already be rooted."
                )
            )

    parser.add_argument(
        "--outgroup",
        nargs="+",
        default=None,
        help=(
            "One or more tip names to use as outgroup. "
            "Providing this option automatically enables outgroup rooting."
            )
        )


def run_import_monopogen(args):
    import_monopogen(args.input_directory, Path(args.output_directory) / args.prefix)


def run_filter(args: argparse.Namespace) -> None:
    """Normalize either input, then run the existing count filter and FASTA mapper."""
    output = Path(args.output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = Path(args.input_directory).resolve()
    if args.input_format == "monopogen":
        source_standard = output / f"{args.prefix}.standard"
        if source_standard.exists():
            with tempfile.TemporaryDirectory() as temporary:
                candidate = Path(temporary) / 'standard'
                import_monopogen(source, candidate)
                if load_bundle(candidate) != load_bundle(source_standard):
                    raise ValueError('existing convenience bundle differs from current input; use a new output directory/prefix')
        else:
            import_monopogen(source, source_standard)
        source = source_standard
    tables = load_bundle(source)
    ids, eligible, vm, cm = select_quality(tables, args)
    selected = [r[0] for r in eligible]
    if args.cell_barcode:
        h, rows = read_table(args.cell_barcode)
        if h != ['cell_barcodes']:
            raise ValueError('barcode file requires exactly one cell_barcodes column')
        requested = [r[0] for r in rows]
        if len(set(requested)) != len(requested):
            raise ValueError('duplicate selected cell barcodes')
        unknown = set(requested) - set(cm)
        if unknown:
            raise ValueError(f'unknown selected cell barcodes: {sorted(unknown)}')
        selected = [c for c in requested if c in selected]
    if not ids or not selected:
        raise ValueError('no variants or eligible cells remain after metadata QC/selection')
    column_index = {v: i for i, v in enumerate(tables[0][0])}
    positions = [column_index[v] for v in ids]
    by_cell = {r[0]: r for r in eligible}
    # Check for empty results before launching R or producing a misleading FASTA.
    retained = [i for i in positions if sum(int(by_cell[c][i].split('/')[1]) > 0 for c in selected) >= args.min_alt_cells_per_snv]
    if not retained or not any(sum(int(by_cell[c][i].split('/')[1]) > 0 for i in retained) >= args.min_snvs_per_cell for c in selected):
        raise ValueError('no variants or cells remain after count filtering; review cutoffs')
    matrix_path = output / f'{args.prefix}.SNV_mat.input.tsv'
    write_table(matrix_path, ['Variant_ID', *selected],
                [[vid, *[by_cell[c][i] for c in selected]] for vid,i in zip(ids, positions)])
    cell_path = output / f'{args.prefix}.selected_cells.tsv'
    write_table(cell_path, ['cell_barcodes'], [[c] for c in selected])
    write_table(output / f'{args.prefix}.cellID.filter.csv', ['cell', 'index'],
                [[c, i+1] for i,c in enumerate(selected)], ',')
    write_table(output / f'{args.prefix}.SNVs.filter.csv', tables[1][0],
                [[vm[v][k] for k in tables[1][0]] for v in ids], ',')
    subprocess.run(['Rscript', str(SCRIPTS_DIR / 'matrix_bridge.R'), 'import',
                    str(matrix_path), str(output / f'{args.prefix}.SNV_mat.RDS')], check=True)
    subprocess.run(['Rscript', str(SCRIPTS_DIR / 'mutation_filter.R'),
                    str(output) + os.sep, args.prefix, str(cell_path),
                    str(args.min_alt_cells_per_snv), str(args.min_snvs_per_cell), str(args.threads)], check=True)
    convert_snv_matrix_to_fasta(str(output) + os.sep, args.prefix)


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
    output_directory = str(Path(args.output_directory).resolve()) + os.sep
    Path(output_directory).mkdir(parents=True, exist_ok=True)
    sample_id = args.prefix
    if getattr(args, 'input_format', 'fasta') != 'fasta':
        filtering = argparse.Namespace(**vars(args))
        filtering.input_directory = fasta_path
        filtering.threads = args.threads if args.threads > 0 else (os.cpu_count() or 1)
        run_filter(filtering)
        fasta_path = str(Path(output_directory) / f'{sample_id}.fasta')
        shutil.copyfile(Path(output_directory) / f'{sample_id}.SNV_mat.filter.fasta', fasta_path)

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
    print("  " + shlex.join(cmd))

    # Also persist a runnable script for reproducibility
    script_path = generate_script(cmd, output_directory, sample_id)
    print(f"[SPICE:phylogeny] Wrote script: {script_path}")

    # -------------------------------------------------------------------------
    # Execute IQ-TREE2
    # -------------------------------------------------------------------------
    try:
        subprocess.run(cmd, check=True)
        print("[SPICE:phylogeny] IQ-TREE2 finished successfully.")
    except FileNotFoundError:
        print("Error: IQ-TREE2 binary not found. Set IQTREE2_BIN or ensure iqtree2/iqtree is available on PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: IQ-TREE2 failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)

    # IQ-TREE writes beside the actual alignment passed to -s (also for FASTA
    # outside the output directory). Filtering still supplies <prefix>.fasta.
    tree_file = Path(str(fasta_path) + ".treefile").resolve()
    run_clone_classification(args, tree_file)


def run_clones(args: argparse.Namespace) -> None:
    """Classify an existing supported IQ-TREE Newick tree without inference."""
    tree_file = _require_file(args.tree, "IQ-TREE tree")
    try:
        with tree_file.open("rb") as handle:
            handle.read(1)
    except OSError as exc:
        raise ValueError(f"Cannot read IQ-TREE tree: {tree_file}: {exc}") from exc
    run_clone_classification(args, tree_file)


def run_clone_classification(args: argparse.Namespace, tree_file: Path) -> None:
    """Run the authoritative R clone analysis; scientific options are unchanged.

    R arguments 1-15 retain their historical positions. Argument 16 supplies the
    explicit input tree; output directories still end in a separator for R.
    """
    output_directory = str(Path(args.output_directory).resolve()) + os.sep
    Path(output_directory).mkdir(parents=True, exist_ok=True)
    sample_id = args.prefix
    print(f"\n[SPICE:{args.command}] Running BranchSupportCut.R ...")

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
        print(f"[SPICE:{args.command}] Rooting method: outgroup")
        print(f"[SPICE:{args.command}] Outgroup tip(s): " + ", ".join(outgroup))
    else:
        outgroup_string = "NA"
        if root_method == "outgroup":
            print(
                "Error: --root_method outgroup requires --outgroup.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"[SPICE:{args.command}] Rooting method: {root_method}")

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
        str(Path(tree_file).expanduser().resolve()),  # args[16] explicit IQ-TREE tree
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"[SPICE:{args.command}] BranchSupportCut.R finished successfully.")
    except FileNotFoundError:
        print("Error: 'Rscript' not found or 'BranchSupportCut.R' package resource missing.", file=sys.stderr)
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
        subprocess.run(cmd, check=True)
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
        subprocess.run(cmd, check=True)
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
        prog="python SPICE.py" if Path(sys.argv[0]).name == "SPICE.py" else "spice",
        description="SPICE command-line interface",
        add_help=True,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"SPICE {VERSION}")
    subparsers = parser.add_subparsers(dest="command", metavar="")

    p_import = subparsers.add_parser('import-monopogen', help='Convert Monopogen RDS/count metadata to a standard cell x variant bundle')
    p_import.add_argument('input_directory', help='Monopogen directory')
    p_import.add_argument('output_directory', help='Parent output directory')
    p_import.add_argument('prefix', help='New bundle directory name')
    p_import.set_defaults(func=run_import_monopogen)

    # ------------------------------- filter -----------------------------------
    p_filter = subparsers.add_parser(
        "filter",
        help="Filter somatic SNVs and cells using quality and model thresholds",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Mandatory positional arguments
    p_filter.add_argument("input_directory", help="Monopogen directory or standard bundle directory (see --input_format)")
    p_filter.add_argument("output_directory", help="Path to the directory where outputs will be saved")
    p_filter.add_argument("prefix", help="Identifier to prefix output filenames")
    p_filter.add_argument("cell_barcode", nargs="?", default=None, help="File containing cell barcodes to be used in the analysis")

    p_filter.add_argument('--input_format', choices=['monopogen', 'standard'], default='monopogen', help='Input directory format')

    # Optional arguments
    add_filter_options(p_filter)
    p_filter.add_argument("--threads", type=int, default=1,
                          help="Number of threads to use")
    p_filter.set_defaults(func=run_filter)

    # ------------------------------ phylogeny ---------------------------------
    p_phy = subparsers.add_parser(
        "phylogeny",
        help="Infer phylogeny with IQ-TREE2 and apply support/branch filters",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_phy.add_argument('--input_format', choices=['fasta', 'standard', 'monopogen'], default='fasta', help='Start from FASTA, standard bundle, or Monopogen directory')
    p_phy.add_argument('--cell_barcode', default=None, help='Optional selected-cell TSV for standard/Monopogen input')
    add_filter_options(p_phy)
    p_phy.add_argument("--model", type=str, default="TEST",
                       help="Specifies the model selection option for IQTREE2")
    p_phy.add_argument("--uf_bootstrap_replicates", type=int, default=1000,
                       help="Number of replicates (≥1000) for ultrafast bootstrap analysis")
    p_phy.add_argument("--sh_alrt_replicates", type=int, default=1000,
                       help="Number of replicates (≥1000) to perform the SH-like approximate likelihood ratio test (SH-aLRT)")
    add_clone_options(p_phy)
    p_phy.add_argument("--threads", type=int, default=1,
                       help="Number of threads to use")

    # Required positional arguments
    p_phy.add_argument("fasta_path", help="FASTA file or input bundle/Monopogen directory selected by --input_format")
    p_phy.add_argument("output_directory", help="")
    p_phy.add_argument("prefix", help="")
    p_phy.set_defaults(func=run_phylogeny)

    # ------------------------------- clones -----------------------------------
    p_clones = subparsers.add_parser(
        "clones",
        help="Classify clones from an existing supported IQ-TREE tree; no tree inference",
        description=(
            "Does not infer a tree or run IQ-TREE. Expects an IQ-TREE-style supported "
            "Newick tree with node labels interpreted as SH-aLRT/UFBoot. Performs "
            "SPICE rooting, support filtering, branch-cut analysis, threshold "
            "selection, clone assignment, and clone tree export."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_clones.add_argument("--tree", required=True,
                          help="Existing IQ-TREE Newick tree with SH-aLRT/UFBoot support labels")
    p_clones.add_argument("--output_directory", required=True,
                          help="Directory for the existing Phylo/ and Clone/ output layout")
    p_clones.add_argument("--prefix", required=True,
                          help="Sample identifier used to prefix output filenames")
    add_clone_options(p_clones)
    p_clones.set_defaults(func=run_clones)

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

    p_sum = subparsers.add_parser("summarize", help="Combine clone plasticity results and apply BH FDR")
    p_sum.add_argument("manifest", help="TSV with clone_id and plasticity_test columns; paths relative to manifest")
    p_sum.add_argument("output", help="New output TSV path")
    p_sum.add_argument("--alpha", type=float, default=0.05, help="FDR cutoff for significant clones")
    p_sum.set_defaults(func=run_summary)

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
    if hasattr(args, "prefix") and (not args.prefix or Path(args.prefix).name != args.prefix or args.prefix in (".","..") or any(c in args.prefix for c in "\n\r\t")):
        parser.error("prefix must be a single filename component without tabs/newlines")
    os.environ["SPICE_VERSION"] = VERSION
    metadata = capture_runtime(args, PROJECT_DIR)
    try:
        args.func(args)
    except (ValueError, OSError) as exc:
        save_runtime(metadata, args, PROJECT_DIR, success=False)
        parser.error(str(exc))
    except BaseException:
        save_runtime(metadata, args, PROJECT_DIR, success=False)
        raise
    save_runtime(metadata, args, PROJECT_DIR, success=True)
    return 0



if __name__ == "__main__":
    sys.exit(main())
