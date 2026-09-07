# SPICE ancestry utilities
# Core BayesTraits orchestration and posterior ancestral-state parsing.

required_pkgs <- c("ape", "coda", "btw", "janitor")
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
  hyperprior
) {
  addnodes <- spice_addnode_commands(tree, addnodes_file)
  cmd <- c(
    "1",  # MultiState
    "2",  # MCMC
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
  hyperprior
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
    hyperprior=hyperprior
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

spice_clean_bt_results <- function(log_file) {
  parsed <- btw::parse_log(log_file)
  if (is.null(parsed$results) || nrow(parsed$results) == 0) {
    stop(paste("No MCMC results found in", log_file))
  }
  janitor::clean_names(as.data.frame(parsed$results, check.names=FALSE))
}

spice_parameter_columns <- function(df) {
  exclude <- c("tree_no", "iteration")
  setdiff(colnames(df), exclude)
}

spice_mcmc_diagnostics <- function(chain_results, min_ess=200, max_psrf=1.1) {
  parameter_sets <- lapply(chain_results, spice_parameter_columns)
  common <- Reduce(intersect, parameter_sets)
  if (length(common) == 0) stop("No common MCMC parameters were found across chains.")

  chain_objs <- lapply(chain_results, function(x) {
    mat <- as.matrix(x[, common, drop=FALSE])
    storage.mode(mat) <- "numeric"
    coda::mcmc(mat)
  })
  ml <- coda::mcmc.list(chain_objs)
  ess <- coda::effectiveSize(ml)

  psrf_point <- rep(NA_real_, length(common))
  psrf_upper <- rep(NA_real_, length(common))
  names(psrf_point) <- common
  names(psrf_upper) <- common

  if (length(chain_objs) >= 2) {
    gd <- tryCatch(
      coda::gelman.diag(ml, autoburnin=FALSE, multivariate=FALSE)$psrf,
      error=function(e) NULL
    )
    if (!is.null(gd)) {
      psrf_point[rownames(gd)] <- gd[,1]
      psrf_upper[rownames(gd)] <- gd[,2]
    }
  }

  out <- data.frame(
    parameter=common,
    ESS=as.numeric(ess[common]),
    PSRF_point=as.numeric(psrf_point[common]),
    PSRF_upper=as.numeric(psrf_upper[common]),
    stringsAsFactors=FALSE
  )
  out$ESS_pass <- !is.na(out$ESS) & out$ESS >= min_ess
  out$PSRF_pass <- if (length(chain_objs) >= 2) {
    !is.na(out$PSRF_point) & out$PSRF_point <= max_psrf
  } else {
    NA
  }
  out
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

spice_run_ancestry <- function(
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
  write_outputs=TRUE
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
    hyperprior=hyperprior
  )
  log_files <- if (.Platform$OS.type != "windows" && ncores > 1) {
    parallel::mclapply(ids, runner, mc.cores=ncores)
  } else {
    lapply(ids, runner)
  }

  chain_results <- lapply(log_files, spice_clean_bt_results)
  diagnostics <- spice_mcmc_diagnostics(chain_results, min_ess=min_ess, max_psrf=max_psrf)
  ancestry <- spice_parse_node_posteriors(
    chain_results, encoded$map, min_probability=min_probability
  )

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
        hyperprior=hyperprior
      )
    )
  }

  list(
    tree=tree,
    states=states,
    state_map=encoded$map,
    ancestry=ancestry,
    diagnostics=diagnostics,
    log_files=unlist(log_files),
    trait_file=trait_file
  )
}
