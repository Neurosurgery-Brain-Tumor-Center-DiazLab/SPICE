#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly=TRUE)
if (length(args) < 15) {
  stop(
    paste(
      "Usage: ancestry_core.R TREE STATES OUTPUT_DIR PREFIX BAYESTRAITS_BIN",
      "CHAINS ITERATIONS BURNIN SAMPLE_PERIOD STEPPING_STONES STONE_ITERATIONS",
      "MIN_ESS MAX_PSRF MIN_ANCESTRAL_PROB THREADS [HYPERPRIOR]"
    )
  )
}

tree_file <- args[1]
state_file <- args[2]
output_dir <- args[3]
prefix <- args[4]
bayestraits_bin <- args[5]
chains <- as.integer(args[6])
iterations <- as.integer(args[7])
burnin <- as.integer(args[8])
sample_period <- as.integer(args[9])
stepping_stones <- as.integer(args[10])
stone_iterations <- as.integer(args[11])
min_ess <- as.numeric(args[12])
max_psrf <- as.numeric(args[13])
min_probability <- as.numeric(args[14])
threads <- as.integer(args[15])
hyperprior <- if (length(args) >= 16) args[16] else "exp 0 10"

# Resolve the directory containing this script so it can source shared utilities.
max_rhat <- if (length(args) >= 17) as.numeric(args[17]) else 1.01
min_bulk_ess <- if (length(args) >= 18) as.numeric(args[18]) else 400
min_tail_ess <- if (length(args) >= 19) as.numeric(args[19]) else 400
max_retries <- if (length(args) >= 20) as.integer(args[20]) else 2
retry_multiplier <- if (length(args) >= 21) as.numeric(args[21]) else 2

mcmc_seed <- if (length(args) >= 22) as.numeric(args[22]) else 12345

file_arg <- grep("^--file=", commandArgs(trailingOnly=FALSE), value=TRUE)
if (length(file_arg) > 0) {
  script_path <- sub("^--file=", "", file_arg[1])
  script_dir <- dirname(normalizePath(script_path, mustWork=TRUE))
} else {
  script_dir <- getwd()
}
source(file.path(script_dir, "spice_ancestry_utils.R"))

if (!file.exists(tree_file)) stop(paste("Tree file not found:", tree_file))
if (!file.exists(state_file)) stop(paste("State file not found:", state_file))
if (!file.exists(bayestraits_bin)) stop(paste("BayesTraits executable not found:", bayestraits_bin))
if (chains < 1) stop("CHAINS must be >= 1.")
if (iterations <= burnin) stop("ITERATIONS must be greater than BURNIN.")
if (sample_period < 1) stop("SAMPLE_PERIOD must be >= 1.")
if (min_probability < 0 || min_probability > 1) stop("MIN_ANCESTRAL_PROB must be in [0,1].")

res <- spice_run_ancestry(
  tree_file=tree_file,
  state_file=state_file,
  output_dir=output_dir,
  prefix=prefix,
  bayestraits_bin=bayestraits_bin,
  chains=chains,
  iterations=iterations,
  burnin=burnin,
  sample_period=sample_period,
  stepping_stones=stepping_stones,
  stone_iterations=stone_iterations,
  min_ess=min_ess,
  max_psrf=max_psrf,
  min_probability=min_probability,
  threads=threads,
  hyperprior=hyperprior,
      max_rhat=max_rhat, min_bulk_ess=min_bulk_ess, min_tail_ess=min_tail_ess,
      max_retries=max_retries, retry_multiplier=retry_multiplier,
      mcmc_seed=mcmc_seed,
  write_outputs=TRUE
)

cat("SPICE ancestry completed.\n")
cat("Internal nodes inferred:", nrow(res$ancestry), "\n")
cat("Confident nodes:", sum(res$ancestry$confident, na.rm=TRUE), "\n")
