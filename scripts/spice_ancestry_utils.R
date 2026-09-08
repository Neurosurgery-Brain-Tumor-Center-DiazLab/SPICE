# Stable positive seeds, independent of worker scheduling.
spice_derive_seed <- function(base, offset=0) {
  if (length(base)!=1 || !is.finite(base) || base < 1 || base > 2147483646 || base != floor(base))
    stop("Invalid MCMC seed.")
  as.integer(((as.double(base)-1+as.double(offset)) %% 2147483646)+1)
}

# SPICE ancestry utilities
# Core BayesTraits orchestration and posterior ancestral-state parsing.

required_pkgs <- c("ape", "coda", "btw", "janitor", "posterior")
missing_pkgs <- required_pkgs[!vapply(required_pkgs, requireNamespace, logical(1), quietly=TRUE)]
if (length(missing_pkgs) > 0) {
  stop(
    paste0(
      "Missing required R package(s): ", paste(missing_pkgs, collapse=", "),
      ". Install these packages before running SPICE ancestry/plasticity."
    )
  )
}

spice_read_tree <- function(tree_file) {
  ext <- tolower(tools::file_ext(tree_file))
  tree <- if (ext %in% c("nex", "nexus")) {
    ape::read.nexus(tree_file)
  } else {
    ape::read.tree(tree_file)
  }
  if (inherits(tree, "multiPhylo")) {
    if (length(tree) != 1) stop("SPICE currently expects exactly one tree per ancestry analysis.")
    tree <- tree[[1]]
  }
  if (!inherits(tree, "phylo")) stop("Unable to read input as a phylo tree.")
  if (!ape::is.rooted(tree)) {
    stop("Ancestry requires a rooted lineage tree. Root the tree before running SPICE ancestry.")
  }
  if (anyDuplicated(tree$tip.label)) stop("Tree contains duplicated tip labels.")
  tree
}

spice_read_states <- function(state_file) {
  first <- readLines(state_file, n=1, warn=FALSE)
  fields <- strsplit(first, "\t", fixed=TRUE)[[1]]
  has_header <- length(fields) >= 2 &&
    tolower(trimws(fields[1])) %in% c("cell_id", "cell", "label", "tip", "barcode") &&
    tolower(trimws(fields[2])) %in% c("state", "cell_state", "trait", "label", "assignedlabel")

  x <- utils::read.table(
    state_file, header=has_header, sep="\t", quote="", comment.char="",
    stringsAsFactors=FALSE, check.names=FALSE
  )
  if (ncol(x) < 2) stop("State table must contain at least two tab-separated columns.")
  x <- x[,1:2, drop=FALSE]
  colnames(x) <- c("cell_id", "state")
  x$cell_id <- as.character(x$cell_id)
  x$state <- as.character(x$state)
  if (any(is.na(x$cell_id) | x$cell_id == "")) stop("State table contains missing cell IDs.")
  if (any(is.na(x$state) | x$state == "")) stop("State table contains missing states.")
  if (anyDuplicated(x$cell_id)) stop("State table contains duplicated cell IDs.")
  x
}

spice_validate_tree_states <- function(tree, states) {
  missing_states <- setdiff(tree$tip.label, states$cell_id)
  extra_states <- setdiff(states$cell_id, tree$tip.label)
  if (length(missing_states) > 0) {
    stop(
      paste0(
        "Missing state annotation for ", length(missing_states), " tree tip(s): ",
        paste(head(missing_states, 10), collapse=", ")
      )
    )
  }
  if (length(extra_states) > 0) {
    message(
      "Ignoring ", length(extra_states),
      " state-table cell(s) not present in the supplied tree."
    )
  }
  states <- states[match(tree$tip.label, states$cell_id),,drop=FALSE]
  if (!identical(states$cell_id, tree$tip.label)) {
    stop("Internal error while ordering state table to tree tips.")
  }
  states
}

spice_descendant_tips <- function(tree, node) {
  children <- tree$edge[tree$edge[,1] == node, 2]
  if (length(children) == 0) {
    if (node <= length(tree$tip.label)) return(tree$tip.label[node])
    return(character(0))
  }
  unlist(lapply(children, function(ch) spice_descendant_tips(tree, ch)), use.names=FALSE)
}

spice_addnode_commands <- function(tree, outfile=NULL) {
  ntip <- length(tree$tip.label)
  lines <- character(0)
  for (i in seq_len(tree$Nnode)) {
    node_index <- ntip + i
    tips <- spice_descendant_tips(tree, node_index)
    lines <- c(
      lines,
      paste(c(paste("AddTag", paste0("T", i)), tips), collapse="\t"),
      paste("AddNode", i, paste0("T", i))
    )
  }
  if (!is.null(outfile)) writeLines(lines, outfile)
  lines
}

spice_encode_states <- function(states) {
  # Deterministic coding only; biological direction is supplied separately
  # to the plasticity module through state_order.tsv.
  levels <- sort(unique(states$state))
  map <- data.frame(
    state=levels,
    state_code=seq_along(levels) - 1L,
    stringsAsFactors=FALSE
  )
  encoded <- merge(states, map, by="state", sort=FALSE)
  encoded <- encoded[match(states$cell_id, encoded$cell_id),,drop=FALSE]
  list(states=encoded, map=map)
}

spice_make_bt_commands <- function(
  tree,
  command_file,
  addnodes_file,
  logfile_prefix,
  iterations,
  burnin,
  sample_period,
  stepping_stones,
  stone_iterations,
  hyperprior,
  mcmc_seed=12345
) {
  addnodes <- spice_addnode_commands(tree, addnodes_file)
  cmd <- c(
    "1",  # MultiState
    "2",  # MCMC
    paste("Seed", format(mcmc_seed, scientific=FALSE)),
    paste("Iterations", format(iterations, scientific=FALSE)),
    paste("Burnin", format(burnin, scientific=FALSE)),
    paste("HyperPriorAll", hyperprior)
  )
  if (stepping_stones > 0) {
    cmd <- c(cmd, paste("Stones", stepping_stones, stone_iterations))
  }
  cmd <- c(
    cmd,
    paste("Sample", sample_period),
    addnodes,
    paste("LogFile", logfile_prefix),
    "Run"
  )
  writeLines(cmd, command_file)
  invisible(cmd)
}

spice_run_bt_chain <- function(
  chain_id,
  tree_file,
  trait_file,
  tree,
  output_dir,
  prefix,
  bayestraits_bin,
  iterations,
  burnin,
  sample_period,
  stepping_stones,
  stone_iterations,
  hyperprior,
  mcmc_seed=12345
) {
  chain_name <- sprintf("MCMC%d", chain_id)
  chain_dir <- file.path(output_dir, chain_name)
  dir.create(chain_dir, recursive=TRUE, showWarnings=FALSE)
  cmd_file <- file.path(chain_dir, paste0(chain_name, "_cmd.txt"))
  addnodes_file <- file.path(chain_dir, paste0(chain_name, "_AddNodes.txt"))
  logfile_prefix <- file.path(chain_dir, chain_name)

  spice_make_bt_commands(
    tree=tree,
    command_file=cmd_file,
    addnodes_file=addnodes_file,
    logfile_prefix=logfile_prefix,
    iterations=iterations,
    burnin=burnin,
    sample_period=sample_period,
    stepping_stones=stepping_stones,
    stone_iterations=stone_iterations,
    hyperprior=hyperprior, mcmc_seed=mcmc_seed
  )

  status <- system2(
    bayestraits_bin,
    args=c(shQuote(tree_file), shQuote(trait_file)),
    stdin=cmd_file,
    stdout=file.path(chain_dir, paste0(chain_name, ".stdout.txt")),
    stderr=file.path(chain_dir, paste0(chain_name, ".stderr.txt"))
  )
  if (!identical(as.integer(status), 0L)) {
    stop(sprintf("BayesTraits chain %s failed with exit code %s.", chain_name, status))
  }
  log_file <- paste0(logfile_prefix, ".Log.txt")
  if (!file.exists(log_file)) {
    stop(sprintf("Expected BayesTraits log was not created: %s", log_file))
  }
  log_file
}

spice_clean_bt_results <- function(log_file, burnin=0, iterations=Inf, sample_period=NULL) {
  lines <- readLines(log_file, warn=FALSE)
  header <- grep("^Iteration\\t", lines)
  if (length(header) != 1) stop("Expected exactly one MCMC header in ", log_file)
  raw <- utils::read.table(log_file, skip=header-1L, header=TRUE, sep="\t",
                           quote="", comment.char="", check.names=FALSE)
  # BayesTraits may write a trailing empty column. Never discard a real parameter.
  empty <- names(raw) == "" & vapply(raw, function(x) all(is.na(x)), logical(1))
  raw <- raw[, !empty, drop=FALSE]
  x <- janitor::clean_names(raw)
  if (!"iteration" %in% names(x) || anyDuplicated(names(x))) stop("Invalid MCMC columns.")
  if (!is.numeric(x$iteration) || any(!is.finite(x$iteration)) ||
      any(diff(x$iteration) <= 0)) stop("Invalid or repeated MCMC iterations.")
  x <- x[x$iteration > burnin & x$iteration <= iterations,,drop=FALSE]
  if (nrow(x) < 4) stop("Too few post-burn-in samples for QC.")
  if (!is.null(sample_period)) {
    expected <- seq.int((floor(burnin / sample_period)+1)*sample_period,
                        floor(iterations / sample_period)*sample_period, by=sample_period)
    if (!identical(as.numeric(x$iteration), as.numeric(expected)))
      stop("Incomplete MCMC sample grid in ", log_file)
  }
  x
}

spice_parameter_columns <- function(df) setdiff(colnames(df), c("tree_no", "iteration"))

spice_mcmc_diagnostics <- function(chain_results, min_ess=200, max_psrf=1.1,
                                   max_rhat=1.01, min_bulk_ess=400, min_tail_ess=400) {
  if (length(chain_results) < 2) stop("QC requires at least two independent chains.")
  common <- spice_parameter_columns(chain_results[[1]])
  if (!length(common)) stop("No MCMC parameters found.")
  for (x in chain_results) {
    if (!identical(spice_parameter_columns(x), common)) stop("Chain parameter columns differ.")
    if (!identical(x$iteration, chain_results[[1]]$iteration)) stop("Chain sample grids differ.")
    if (!all(vapply(x[,common,drop=FALSE], is.numeric, logical(1)))) stop("Non-numeric MCMC parameter.")
    if (any(!is.finite(as.matrix(x[,common,drop=FALSE])))) stop("Non-finite MCMC sample.")
  }
  safe <- function(expr) tryCatch(suppressWarnings(as.numeric(expr)[1]), error=function(e) NA_real_)
  rows <- lapply(common, function(nm) {
    mat <- do.call(cbind, lapply(chain_results, function(x) x[[nm]]))
    chains <- coda::mcmc.list(lapply(seq_len(ncol(mat)), function(i) coda::mcmc(mat[,i])))
    ess <- safe(coda::effectiveSize(chains))
    ps <- tryCatch(suppressWarnings(coda::gelman.diag(chains, autoburnin=FALSE,
                            multivariate=FALSE)$psrf[1,]), error=function(e) c(NA_real_, NA_real_))
    rh <- safe(posterior::rhat(mat))
    bulk <- safe(posterior::ess_bulk(mat))
    tail <- safe(posterior::ess_tail(mat))
    mcse <- safe(posterior::mcse_mean(mat))
    constant <- any(apply(mat, 2, function(x) length(unique(x)) == 1))
    valid <- all(is.finite(c(rh,bulk,tail,mcse))) && !constant
    pass <- valid && rh < max_rhat && bulk >= min_bulk_ess && tail >= min_tail_ess
    is_node <- grepl("^x[0-9]+_p_", nm) || grepl("^root_p_", nm)
    node <- if (grepl("^x[0-9]+_p_", nm)) sub("^x([0-9]+)_.*", "T\\1", nm) else
      if (grepl("^root_p_", nm)) "T1" else NA_character_
    data.frame(parameter=nm, ESS=ess, PSRF_point=ps[1], PSRF_upper=ps[2],
      ESS_pass=is.finite(ess) && ess >= min_ess,
      PSRF_pass=is.finite(ps[1]) && ps[1] <= max_psrf,
      Rhat=rh, ESS_bulk=bulk, ESS_tail=tail, MCSE_mean=mcse,
      diagnostic_status=if (constant) "constant_chain" else if (!valid) "unavailable" else
        if (pass) "pass" else "fail",
      qc_pass=pass, scope=if (is_node) "node" else "model", node_id=node,
      draws_per_chain=nrow(mat), chains=ncol(mat), stringsAsFactors=FALSE)
  })
  do.call(rbind, rows)
}

spice_state_fingerprint <- function(states) {
  states <- states[order(states$cell_id),c("cell_id","state"),drop=FALSE]
  path <- tempfile()
  on.exit(unlink(path), add=TRUE)
  utils::write.table(states,path,sep="\t",row.names=FALSE,quote=FALSE)
  unname(tools::md5sum(path))
}

spice_parse_node_posteriors <- function(chain_results, state_map, min_probability=0.90) {
  combined <- do.call(rbind, lapply(seq_along(chain_results), function(i) {
    x <- chain_results[[i]]
    x$.chain <- i
    x
  }))

  # btw::parse_log + janitor::clean_names convention:
  # X1.P.0. -> x1_p_0, X2.P.1. -> x2_p_1, etc.
  node_cols <- grep("^x[0-9]+_p_.+$", colnames(combined), value=TRUE)
  if (length(node_cols) == 0) {
    stop(
      paste0(
        "Could not identify BayesTraits AddNode posterior columns. ",
        "Expected cleaned names such as x1_p_0. Observed columns include: ",
        paste(head(colnames(combined), 20), collapse=", ")
      )
    )
  }

  long <- do.call(rbind, lapply(node_cols, function(col) {
    m <- regexec("^x([0-9]+)_p_(.+)$", col)
    parts <- regmatches(col, m)[[1]]
    data.frame(
      node_number=as.integer(parts[2]),
      state_code=parts[3],
      probability=as.numeric(combined[[col]]),
      stringsAsFactors=FALSE
    )
  }))

  agg_mean <- aggregate(probability ~ node_number + state_code, long, mean, na.rm=TRUE)
  agg_low <- aggregate(probability ~ node_number + state_code, long,
                       function(z) stats::quantile(z, 0.025, na.rm=TRUE, names=FALSE))
  agg_high <- aggregate(probability ~ node_number + state_code, long,
                        function(z) stats::quantile(z, 0.975, na.rm=TRUE, names=FALSE))
  colnames(agg_mean)[3] <- "posterior_mean"
  colnames(agg_low)[3] <- "posterior_q025"
  colnames(agg_high)[3] <- "posterior_q975"
  post <- Reduce(
    function(a,b) merge(a,b,by=c("node_number","state_code"),all=TRUE,sort=FALSE),
    list(agg_mean, agg_low, agg_high)
  )

  state_map$state_code <- as.character(state_map$state_code)
  post$state_code <- as.character(post$state_code)
  post <- merge(post, state_map, by="state_code", all.x=TRUE, sort=FALSE)
  if (any(is.na(post$state))) {
    stop("BayesTraits returned a state code not present in the encoded state mapping.")
  }

  nodes <- sort(unique(post$node_number))
  rows <- lapply(nodes, function(n) {
    d <- post[post$node_number == n,,drop=FALSE]
    best <- d[which.max(d$posterior_mean),,drop=FALSE]
    out <- data.frame(
      node_id=paste0("T", n),
      node_number=n,
      inferred_state=best$state,
      inferred_state_code=best$state_code,
      posterior_probability=best$posterior_mean,
      posterior_q025=best$posterior_q025,
      posterior_q975=best$posterior_q975,
      confident=best$posterior_mean >= min_probability,
      stringsAsFactors=FALSE
    )
    for (i in seq_len(nrow(d))) {
      safe <- make.names(d$state[i])
      out[[paste0("posterior_", safe)]] <- d$posterior_mean[i]
    }
    out
  })
  do.call(rbind, rows)
}

spice_write_run_info <- function(path, values) {
  tab <- data.frame(
    parameter=names(values),
    value=vapply(values, as.character, character(1)),
    stringsAsFactors=FALSE
  )
  utils::write.table(tab, path, sep="\t", row.names=FALSE, quote=FALSE)
}

spice_run_ancestry_once <- function(
  tree_file,
  state_file=NULL,
  states_df=NULL,
  output_dir,
  prefix,
  bayestraits_bin,
  chains=3,
  iterations=1000000,
  burnin=200000,
  sample_period=1000,
  stepping_stones=10,
  stone_iterations=1000,
  min_ess=200,
  max_psrf=1.1,
  min_probability=0.90,
  threads=1,
  hyperprior="exp 0 10",
  write_outputs=TRUE,
  max_rhat=1.01, min_bulk_ess=400, min_tail_ess=400, mcmc_seed=12345
) {
  dir.create(output_dir, recursive=TRUE, showWarnings=FALSE)
  tree <- spice_read_tree(tree_file)
  states <- if (!is.null(states_df)) states_df else spice_read_states(state_file)
  states <- spice_validate_tree_states(tree, states)
  encoded <- spice_encode_states(states)

  trait_file <- file.path(output_dir, paste0(prefix, ".bayestraits_traits.tsv"))
  utils::write.table(
    encoded$states[,c("cell_id","state_code")],
    trait_file, sep="\t", row.names=FALSE, col.names=FALSE, quote=FALSE
  )
  mapping_file <- file.path(output_dir, paste0(prefix, ".state_mapping.tsv"))
  utils::write.table(encoded$map, mapping_file, sep="\t", row.names=FALSE, quote=FALSE)

  ncores <- max(1L, min(as.integer(threads), as.integer(chains)))
  ids <- seq_len(chains)
  runner <- function(i) spice_run_bt_chain(
    chain_id=i, tree_file=tree_file, trait_file=trait_file, tree=tree,
    output_dir=output_dir, prefix=prefix, bayestraits_bin=bayestraits_bin,
    iterations=iterations, burnin=burnin, sample_period=sample_period,
    stepping_stones=stepping_stones, stone_iterations=stone_iterations,
    hyperprior=hyperprior, mcmc_seed=spice_derive_seed(mcmc_seed, i-1)
  )
  log_files <- if (.Platform$OS.type != "windows" && ncores > 1) {
    parallel::mclapply(ids, runner, mc.cores=ncores)
  } else {
    lapply(ids, runner)
  }

  if (any(vapply(log_files, inherits, logical(1), "try-error"))) stop("A BayesTraits chain failed; inspect chain logs.")
  chain_results <- lapply(log_files, spice_clean_bt_results, burnin=burnin,
                         iterations=iterations, sample_period=sample_period)
  diagnostics <- spice_mcmc_diagnostics(chain_results, min_ess=min_ess, max_psrf=max_psrf,
                                       max_rhat=max_rhat, min_bulk_ess=min_bulk_ess,
                                       min_tail_ess=min_tail_ess)
  ancestry <- spice_parse_node_posteriors(
    chain_results, encoded$map, min_probability=min_probability
  )

  expected_nodes <- paste0("T", seq_len(tree$Nnode))
  if (!setequal(ancestry$node_id, expected_nodes)) stop("Missing or unexpected ancestral nodes.")
  expected_columns <- as.vector(outer(seq_len(tree$Nnode), encoded$map$state_code,
                                    function(n, s) paste0("x", n, "_p_", s)))
  if (!all(expected_columns %in% diagnostics$parameter)) stop("Missing node/state probability columns.")
  model_qc <- diagnostics$qc_pass[diagnostics$scope == "model"]
  run_qc_pass <- length(model_qc) > 0 && all(model_qc)
  ancestry$node_qc_pass <- vapply(ancestry$node_id, function(n) {
    d <- diagnostics[!is.na(diagnostics$node_id) & diagnostics$node_id == n,,drop=FALSE]
    nrow(d) > 0 && all(d$qc_pass)
  }, logical(1))
  ancestry$run_qc_pass <- run_qc_pass
  ancestry$usable <- ancestry$run_qc_pass & ancestry$node_qc_pass & ancestry$confident
  ancestry$tree_md5 <- unname(tools::md5sum(tree_file))
  ancestry$states_md5 <- spice_state_fingerprint(states)

  if (write_outputs) {
    utils::write.table(
      ancestry,
      file.path(output_dir, paste0(prefix, ".ancestral_states.tsv")),
      sep="\t", row.names=FALSE, quote=FALSE
    )
    utils::write.table(
      diagnostics,
      file.path(output_dir, paste0(prefix, ".mcmc_diagnostics.tsv")),
      sep="\t", row.names=FALSE, quote=FALSE
    )
    # Compatibility file for comparison with the historical workflow.
    compatibility <- ancestry
    compatibility$node <- compatibility$node_id
    compatibility$anc_state <- paste0("state", compatibility$inferred_state_code)
    compatibility$anc_prob <- compatibility$posterior_probability
    compatibility <- compatibility[,c("node","anc_state","anc_prob","confident")]
    utils::write.table(
      compatibility,
      file.path(output_dir, paste0(prefix, "_ASE.txt")),
      sep="\t", row.names=FALSE, quote=FALSE
    )

    spice_write_run_info(
      file.path(output_dir, paste0(prefix, ".ancestry_run_info.tsv")),
      c(
        tree=normalizePath(tree_file, mustWork=FALSE),
        states=ifelse(is.null(state_file), "<in-memory>", normalizePath(state_file, mustWork=FALSE)),
        bayestraits_bin=bayestraits_bin,
        mcmc_chains=chains,
        iterations=iterations,
        burnin=burnin,
        sample_period=sample_period,
        stepping_stones=stepping_stones,
        stone_iterations=stone_iterations,
        min_ess=min_ess,
        max_psrf=max_psrf,
        min_ancestral_probability=min_probability,
        mcmc_seed=mcmc_seed,
        hyperprior=hyperprior
      )
    )
  }

  list(
    tree=tree,
    states=states,
    run_qc_pass=run_qc_pass,
    state_map=encoded$map,
    ancestry=ancestry,
    diagnostics=diagnostics,
    log_files=unlist(log_files),
    trait_file=trait_file
  )
}


# Fresh attempts are retained independently. No selection or pooling of chains
# across attempts, and no automatic retry for process/parser/input errors.
spice_run_ancestry <- function(tree_file, state_file=NULL, states_df=NULL,
  output_dir, prefix, bayestraits_bin, chains=3, iterations=1000000,
  burnin=200000, sample_period=1000, stepping_stones=10, stone_iterations=1000,
  min_ess=200, max_psrf=1.1, min_probability=0.90, threads=3,
  hyperprior="exp 0 10", write_outputs=TRUE,
  max_rhat=1.01, min_bulk_ess=400, min_tail_ess=400,
  max_retries=2, retry_multiplier=2, mcmc_seed=12345) {
  if (chains < 2) stop("Convergence QC requires at least two independent chains; default is three.")
  if (iterations <= burnin || burnin < 0 || sample_period < 1 || threads < 1 ||
      max_retries < 0 || retry_multiplier <= 1 || max_rhat <= 1 ||
      min_bulk_ess <= 0 || min_tail_ess <= 0) stop("Invalid MCMC/QC settings.")
  dir.create(output_dir, recursive=TRUE, showWarnings=FALSE)
  output_dir <- normalizePath(output_dir, mustWork=TRUE)
  attempt_root <- file.path(output_dir, paste0(prefix, ".attempts"))
  if (dir.exists(attempt_root) || file.exists(file.path(output_dir,paste0(prefix,".ancestral_states.tsv"))))
    stop("Existing ancestry run found. Use a fresh output directory/prefix to preserve prior results.")
  dir.create(attempt_root)
  history <- data.frame()
  final <- NULL
  for (attempt in seq_len(max_retries+1L)) {
    mult <- retry_multiplier^(attempt-1L)
    niter <- ceiling(iterations*mult)
    nburn <- ceiling(burnin*mult)
    if (!is.finite(niter) || niter > .Machine$integer.max) stop("Retry iteration limit exceeded.")
    attempt_dir <- file.path(attempt_root, sprintf("attempt_%02d",attempt))
    message("Ancestry attempt ",attempt,": ",chains," chains, ",niter," iterations, burnin ",nburn)
    result <- tryCatch(spice_run_ancestry_once(tree_file=tree_file,
      state_file=state_file, states_df=states_df, output_dir=attempt_dir,
      prefix=prefix, bayestraits_bin=bayestraits_bin, chains=chains,
      iterations=niter, burnin=nburn, sample_period=sample_period,
      stepping_stones=stepping_stones, stone_iterations=stone_iterations,
      min_ess=min_ess, max_psrf=max_psrf, min_probability=min_probability,
      threads=threads, hyperprior=hyperprior, write_outputs=TRUE,
      max_rhat=max_rhat, min_bulk_ess=min_bulk_ess, min_tail_ess=min_tail_ess,
      mcmc_seed=spice_derive_seed(mcmc_seed,(attempt-1)*chains)),
      error=function(e) e)
    errored <- inherits(result,"error")
    passed <- !errored && result$run_qc_pass && all(result$ancestry$node_qc_pass)
    history <- rbind(history,data.frame(attempt=attempt,iterations=niter,burnin=nburn,
      seed_base=spice_derive_seed(mcmc_seed,(attempt-1)*chains),
      status=if (errored) "execution_error" else if (passed) "pass" else "qc_failed",
      model_qc_pass=if (errored) FALSE else result$run_qc_pass,
      failed_nodes=if (errored) NA_integer_ else sum(!result$ancestry$node_qc_pass),
      reason=if (errored) conditionMessage(result) else "", stringsAsFactors=FALSE))
    utils::write.table(history,file.path(output_dir,paste0(prefix,".qc_attempts.tsv")),
                       sep="\t",row.names=FALSE,quote=FALSE)
    if (errored) {
      spice_write_run_info(file.path(output_dir,paste0(prefix,".qc_status.tsv")),
                           c(status="execution_error",run_qc_pass=FALSE,reason=conditionMessage(result)))
      stop(conditionMessage(result),call.=FALSE)
    }
    final <- result
    if (passed) break
  }
  # Model failures block the entire lineage. Failed node diagnostics remain
  # explicit and their incident edges are uncertain after the retry budget.
  status <- if (!final$run_qc_pass) "failed" else if (all(final$ancestry$node_qc_pass)) "passed" else "passed_with_uncertain_nodes"
  spice_write_run_info(file.path(output_dir,paste0(prefix,".qc_status.tsv")),
    c(status=status,run_qc_pass=final$run_qc_pass,attempts=nrow(history),
      failed_nodes=sum(!final$ancestry$node_qc_pass),chains=chains,
      rhat_threshold=max_rhat,bulk_ess_threshold=min_bulk_ess,tail_ess_threshold=min_tail_ess,
      max_retries=max_retries,retry_multiplier=retry_multiplier))
  if (!final$run_qc_pass) stop("Ancestry model QC failed after ",nrow(history),
                              " attempt(s); downstream blocked. See .qc_attempts.tsv and attempt logs.")
  # Only the selected final attempt is exported. Attempt-level tables always
  # carry run/node QC flags so they cannot bypass plasticity validation.
  for (suffix in c(".ancestral_states.tsv",".mcmc_diagnostics.tsv",".state_mapping.tsv",
                   ".bayestraits_traits.tsv",".ancestry_run_info.tsv","_ASE.txt")) {
    if (!file.copy(file.path(attempt_dir,paste0(prefix,suffix)),
                   file.path(output_dir,paste0(prefix,suffix)))) stop("Unable to publish ancestry output.")
  }
  final$attempts <- history
  final
}
