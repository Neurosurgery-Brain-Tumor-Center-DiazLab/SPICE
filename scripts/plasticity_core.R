#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly=TRUE)
if (length(args) < 20) {
  stop(
    paste(
      "Usage: plasticity_core.R TREE STATES ANCESTRAL_STATES STATE_ORDER OUTPUT_DIR PREFIX",
      "BAYESTRAITS_BIN PERM_REPLICATES ALTERNATIVE THREADS SEED MIN_ANCESTRAL_PROB",
      "PERM_CHAINS PERM_ITERATIONS PERM_BURNIN PERM_SAMPLE_PERIOD STEPPING_STONES",
      "STONE_ITERATIONS MIN_ESS MAX_PSRF [HYPERPRIOR]"
    )
  )
}

tree_file <- args[1]
state_file <- args[2]
ancestry_file <- args[3]
state_order_file <- args[4]
output_dir <- args[5]
prefix <- args[6]
bayestraits_bin <- args[7]
perm_replicates <- as.integer(args[8])
alternative <- args[9]
threads <- as.integer(args[10])
seed <- as.integer(args[11])
min_probability <- as.numeric(args[12])
perm_chains <- as.integer(args[13])
perm_iterations <- as.integer(args[14])
perm_burnin <- as.integer(args[15])
perm_sample_period <- as.integer(args[16])
stepping_stones <- as.integer(args[17])
stone_iterations <- as.integer(args[18])
min_ess <- as.numeric(args[19])
max_psrf <- as.numeric(args[20])
hyperprior <- if (length(args) >= 21) args[21] else "exp 0 10"

max_rhat <- if (length(args) >= 22) as.numeric(args[22]) else 1.01
min_bulk_ess <- if (length(args) >= 23) as.numeric(args[23]) else 400
min_tail_ess <- if (length(args) >= 24) as.numeric(args[24]) else 400
max_retries <- if (length(args) >= 25) as.integer(args[25]) else 2
retry_multiplier <- if (length(args) >= 26) as.numeric(args[26]) else 2

mcmc_seed <- if (length(args) >= 27) as.numeric(args[27]) else 12345

file_arg <- grep("^--file=", commandArgs(trailingOnly=FALSE), value=TRUE)
if (length(file_arg) > 0) {
  script_path <- sub("^--file=", "", file_arg[1])
  script_dir <- dirname(normalizePath(script_path, mustWork=TRUE))
} else {
  script_dir <- getwd()
}
source(file.path(script_dir, "spice_ancestry_utils.R"))

source(file.path(script_dir, "spice_plasticity_utils.R"))

if (!file.exists(tree_file)) stop(paste("Tree file not found:", tree_file))
if (!file.exists(state_file)) stop(paste("State file not found:", state_file))
if (!file.exists(ancestry_file)) stop(paste("Ancestral-state file not found:", ancestry_file))
if (!file.exists(state_order_file)) stop(paste("State-order file not found:", state_order_file))
dir.create(output_dir, recursive=TRUE, showWarnings=FALSE)
existing <- c(".transitions.tsv", ".plasticity.tsv", ".plasticity_test.tsv", ".permutations")
if (any(file.exists(file.path(output_dir,paste0(prefix,existing)))))
  stop("Existing plasticity run found. Use a fresh output directory/prefix.")

tree <- spice_read_tree(tree_file)
states <- spice_validate_tree_states(tree, spice_read_states(state_file))
ancestry <- spice_read_ancestry(ancestry_file, min_probability=min_probability, tree_file=tree_file, states=states)
state_order <- spice_read_state_order(state_order_file)

observed_transitions <- spice_build_transitions(
  tree, states, ancestry, state_order, min_probability=min_probability
)
observed_summary <- spice_summarize_plasticity(observed_transitions)

utils::write.table(
  observed_transitions,
  file.path(output_dir, paste0(prefix, ".transitions.tsv")),
  sep="\t", row.names=FALSE, quote=FALSE
)
utils::write.table(
  observed_summary,
  file.path(output_dir, paste0(prefix, ".plasticity.tsv")),
  sep="\t", row.names=FALSE, quote=FALSE
)

# Historical compatibility files to simplify regression testing.
utils::write.table(
  spice_transition_compatibility(observed_transitions),
  file.path(output_dir, paste0(prefix, "_ASE_Summary.txt")),
  sep="\t", row.names=FALSE, quote=FALSE
)
compat_summary <- data.frame(
  `self-renewal`=observed_summary$self_renewal,
  differentiation=observed_summary$differentiation,
  dedifferentiation=observed_summary$dedifferentiation,
  total_transitions=observed_summary$informative_transitions,
  cellular_plasticity=round(observed_summary$cellular_plasticity, 2),
  check.names=FALSE
)
utils::write.table(
  compat_summary,
  file.path(output_dir, paste0(prefix, "_cellular_plasticity.tsv")),
  sep="\t", row.names=FALSE, quote=FALSE
)

perm_results <- data.frame(
  permutation=integer(0),
  plasticity=numeric(0),
  status=character(0),
  stringsAsFactors=FALSE
)

if (perm_replicates > 0) {
  if (bayestraits_bin == "NA" || !file.exists(bayestraits_bin)) {
    stop("A valid BayesTraits executable is required when PERM_REPLICATES > 0.")
  }

  run_one_perm <- function(i) {
    perm_states <- states
    set.seed(seed + i)
    perm_states$state <- sample(perm_states$state, replace=FALSE)

    tmp <- file.path(output_dir, paste0(prefix,".permutations"), sprintf("perm_%04d",i))
    dir.create(tmp, recursive=TRUE, showWarnings=FALSE)

    tryCatch({
      anc <- spice_run_ancestry(
        tree_file=tree_file,
        states_df=perm_states,
        output_dir=tmp,
        prefix=sprintf("Perm_%d", i),
        bayestraits_bin=bayestraits_bin,
        chains=perm_chains,
        iterations=perm_iterations,
        burnin=perm_burnin,
        sample_period=perm_sample_period,
        stepping_stones=stepping_stones,
        stone_iterations=stone_iterations,
        min_ess=min_ess,
        max_psrf=max_psrf,
        min_probability=min_probability,
        threads=1,
        hyperprior=hyperprior,
      max_rhat=max_rhat, min_bulk_ess=min_bulk_ess, min_tail_ess=min_tail_ess,
      max_retries=max_retries, retry_multiplier=retry_multiplier,
      mcmc_seed=spice_derive_seed(mcmc_seed,(i-1)*perm_chains*(max_retries+1)),
        write_outputs=FALSE
      )
      tr <- spice_build_transitions(
        anc$tree, perm_states, anc$ancestry, state_order,
        min_probability=min_probability
      )
      sm <- spice_summarize_plasticity(tr)
      data.frame(
        permutation=i,
        plasticity=sm$cellular_plasticity,
        status="ok",
        stringsAsFactors=FALSE
      )
    }, error=function(e) {
      data.frame(
        permutation=i,
        plasticity=NA_real_,
        status=paste0("error: ", conditionMessage(e)),
        stringsAsFactors=FALSE
      )
    })
  }

  ids <- seq_len(perm_replicates)
  ncores <- max(1L, min(threads, perm_replicates))
  res <- if (.Platform$OS.type != "windows" && ncores > 1) {
    parallel::mclapply(ids, run_one_perm, mc.cores=ncores)
  } else {
    lapply(ids, run_one_perm)
  }
  perm_results <- do.call(rbind, res)
}

utils::write.table(
  perm_results,
  file.path(output_dir, paste0(prefix, ".permutation_plasticity.tsv")),
  sep="\t", row.names=FALSE, quote=FALSE
)

test_valid <- perm_replicates > 0 && nrow(perm_results) == perm_replicates &&
  all(perm_results$status == "ok" & is.finite(perm_results$plasticity))
null <- perm_results$plasticity[perm_results$status == "ok" & is.finite(perm_results$plasticity)]
obs <- observed_summary$cellular_plasticity
test_summary <- data.frame(
  test_status=if (perm_replicates == 0) "not_requested" else if (test_valid && is.finite(obs)) "pass" else "incomplete",
  observed_plasticity=obs,
  perm_mean=if (length(null)) mean(null) else NA_real_,
  perm_sd=if (length(null) > 1) stats::sd(null) else NA_real_,
  perm_median=if (length(null)) stats::median(null) else NA_real_,
  empirical_p=if (test_valid) spice_empirical_p(null, obs, alternative) else NA_real_,
  z_score=if (test_valid && length(null) > 1 && stats::sd(null) > 0) (obs - mean(null))/stats::sd(null) else NA_real_,
  n_permutations_requested=perm_replicates,
  n_permutations_successful=length(null),
  alternative=alternative,
  stringsAsFactors=FALSE
)
utils::write.table(
  test_summary,
  file.path(output_dir, paste0(prefix, ".plasticity_test.tsv")),
  sep="\t", row.names=FALSE, quote=FALSE
)

spice_write_run_info(
  file.path(output_dir, paste0(prefix, ".plasticity_run_info.tsv")),
  c(
    tree=normalizePath(tree_file, mustWork=FALSE),
    states=normalizePath(state_file, mustWork=FALSE),
    ancestral_states=normalizePath(ancestry_file, mustWork=FALSE),
    state_order=normalizePath(state_order_file, mustWork=FALSE),
    min_ancestral_probability=min_probability,
    permutation_replicates=perm_replicates,
    alternative=alternative,
    seed=seed,
    mcmc_seed=mcmc_seed,
    threads=threads,
    rhat_threshold=max_rhat,
    bulk_ess_threshold=min_bulk_ess,
    tail_ess_threshold=min_tail_ess,
    max_retries=max_retries,
    retry_multiplier=retry_multiplier,
    hyperprior=hyperprior,
    stepping_stones=stepping_stones,
    stone_iterations=stone_iterations,
    permutation_chains=perm_chains,
    permutation_iterations=perm_iterations,
    permutation_burnin=perm_burnin,
    permutation_sample_period=perm_sample_period,
    denominator="self-renewal + differentiation + dedifferentiation; uncertain edges excluded"
  )
)

cat("SPICE plasticity completed.\n")
cat("Observed plasticity:", observed_summary$cellular_plasticity, "\n")
cat("Informative transitions:", observed_summary$informative_transitions, "\n")
if (perm_replicates > 0) {
  cat("Successful permutations:", length(null), "/", perm_replicates, "\n")
  cat("Empirical p-value:", test_summary$empirical_p, "\n")
}

if (perm_replicates > 0 && (!test_valid || !is.finite(obs))) stop("Permutation test incomplete; no valid p-value published. Inspect retained replicate logs.")
