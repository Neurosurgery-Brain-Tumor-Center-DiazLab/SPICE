# SPICE plasticity utilities
# Generic state-order validation, edge transition classification, and statistics.

spice_read_state_order <- function(path) {
  x <- utils::read.table(
    path, header=TRUE, sep="\t", quote="", comment.char="",
    stringsAsFactors=FALSE, check.names=FALSE
  )
  names_lower <- tolower(colnames(x))
  state_col <- which(names_lower == "state")
  order_col <- which(names_lower == "order")
  if (length(state_col) != 1 || length(order_col) != 1) {
    stop("state_order.tsv must contain columns named 'state' and 'order'.")
  }
  out <- data.frame(
    state=as.character(x[[state_col]]),
    order=as.numeric(x[[order_col]]),
    stringsAsFactors=FALSE
  )
  if (any(is.na(out$state) | out$state == "")) stop("State order contains missing state names.")
  if (any(!is.finite(out$order))) stop("State order contains non-finite, non-numeric or missing order values.")
  if (anyDuplicated(out$state)) stop("State order contains duplicated state names.")
  out
}

spice_read_ancestry <- function(path, min_probability=0.90, tree_file=NULL, states=NULL, expected_qc=NULL) {
  x <- utils::read.table(
    path, header=TRUE, sep="\t", quote="", comment.char="",
    stringsAsFactors=FALSE, check.names=FALSE
  )
  req <- c("node_id", "inferred_state", "posterior_probability")
  if (!all(req %in% colnames(x))) {
    stop(
      paste0(
        "Ancestral-state file must contain columns: ",
        paste(req, collapse=", ")
      )
    )
  }
  required_qc <- c("run_qc_pass", "node_qc_pass", "tree_md5", "states_md5")
  if (!all(required_qc %in% names(x))) stop("Ancestry lacks QC/provenance; rerun SPICE ancestry with convergence QC.")
  if (!"qc_policy" %in% names(x) || anyNA(x$qc_policy) || !all(x$qc_policy == SPICE_QC_POLICY))
    stop("Ancestry QC policy missing or incompatible; rerun ancestry with the current SPICE version.")
  if (!is.null(expected_qc)) {
    for (nm in names(expected_qc)) {
      if (!nm %in% names(x) || anyNA(x[[nm]]) || !all(x[[nm]] == expected_qc[[nm]]))
        stop("Observed/permutation setting mismatch: ", nm, ". Use matching settings or rerun ancestry.")
    }
  }
  logical_flag <- function(z) tolower(as.character(z)) %in% c("true","t","1")
  if (!nrow(x) || !all(logical_flag(x$run_qc_pass))) stop("Ancestry model QC failed; plasticity blocked.")
  if (!is.null(tree_file) && !all(x$tree_md5 == unname(tools::md5sum(tree_file))))
    stop("Ancestry tree fingerprint does not match supplied tree.")
  if (!is.null(states) && !all(x$states_md5 == spice_state_fingerprint(states)))
    stop("Ancestry cell-state fingerprint does not match supplied states.")
  x$node_qc_pass <- logical_flag(x$node_qc_pass)
  x$node_id <- as.character(x$node_id)
  x$inferred_state <- as.character(x$inferred_state)
  x$posterior_probability <- as.numeric(x$posterior_probability)
  if (anyDuplicated(x$node_id)) stop("Ancestral-state file contains duplicated node_id values.")
  if (any(!is.finite(x$posterior_probability) | x$posterior_probability < 0 |
          x$posterior_probability > 1)) stop("Invalid ancestral posterior probability.")
  # Recalculate confidence for this analysis; convergence QC remains mandatory.
  x$confident <- x$posterior_probability >= min_probability & x$node_qc_pass
  x$usable <- x$confident & logical_flag(x$run_qc_pass)
  x
}

spice_node_label <- function(tree, idx) {
  ntip <- length(tree$tip.label)
  if (idx <= ntip) return(tree$tip.label[idx])
  paste0("T", idx - ntip)
}

spice_validate_state_order <- function(states, state_order) {
  missing_order <- setdiff(unique(as.character(states$state)), state_order$state)
  if (length(missing_order) > 0) {
    stop(paste("State(s) missing from state_order.tsv:", paste(missing_order, collapse=", ")))
  }
  invisible(TRUE)
}

spice_build_transitions <- function(tree, states, ancestry, state_order, min_probability=0.90) {
  spice_validate_state_order(states, state_order)
  order_map <- stats::setNames(state_order$order, state_order$state)

  tip_state <- stats::setNames(as.character(states$state), as.character(states$cell_id))
  anc_state <- stats::setNames(as.character(ancestry$inferred_state), as.character(ancestry$node_id))
  anc_prob <- stats::setNames(as.numeric(ancestry$posterior_probability), as.character(ancestry$node_id))
  if (!all(c("run_qc_pass","node_qc_pass") %in% names(ancestry)) ||
      !all(ancestry$run_qc_pass %in% TRUE)) stop("Ancestry QC missing or failed.")
  anc_conf <- stats::setNames(as.numeric(ancestry$posterior_probability) >= min_probability & ancestry$node_qc_pass,
                              as.character(ancestry$node_id))

  expected_nodes <- paste0("T", seq_len(tree$Nnode))
  missing_nodes <- setdiff(expected_nodes, names(anc_state))
  if (length(missing_nodes) > 0) {
    stop(
      paste0(
        "Ancestral-state table is missing ", length(missing_nodes),
        " internal node(s): ", paste(head(missing_nodes, 10), collapse=", ")
      )
    )
  }

  get_info <- function(idx) {
    label <- spice_node_label(tree, idx)
    if (idx <= length(tree$tip.label)) {
      return(list(label=label, state=unname(tip_state[label]), probability=1.0, confident=TRUE))
    }
    prob <- unname(anc_prob[label])
    list(
      label=label,
      state=unname(anc_state[label]),
      probability=prob,
      confident=isTRUE(unname(anc_conf[label])) && !is.na(prob) && prob >= min_probability
    )
  }

  rows <- lapply(seq_len(nrow(tree$edge)), function(i) {
    p <- get_info(tree$edge[i,1])
    c <- get_info(tree$edge[i,2])
    transition <- "uncertain"

    if (isTRUE(p$confident) && isTRUE(c$confident) &&
        !is.na(p$state) && !is.na(c$state) &&
        p$state %in% names(order_map) && c$state %in% names(order_map)) {
      po <- unname(order_map[p$state])
      co <- unname(order_map[c$state])
      transition <- if (co > po) {
        "differentiation"
      } else if (co < po) {
        "dedifferentiation"
      } else {
        "self-renewal"
      }
    }

    data.frame(
      edge_id=i,
      parent_node=p$label,
      child_node=c$label,
      parent_state=p$state,
      child_state=c$state,
      parent_probability=p$probability,
      child_probability=c$probability,
      transition=transition,
      stringsAsFactors=FALSE
    )
  })
  do.call(rbind, rows)
}

spice_summarize_plasticity <- function(transitions) {
  transition_levels <- c("self-renewal", "differentiation", "dedifferentiation", "uncertain")
  counts <- table(factor(transitions$transition, levels=transition_levels))
  informative <- sum(counts[c("self-renewal", "differentiation", "dedifferentiation")])
  total_edges <- sum(counts)

  frac <- function(name) {
    if (informative == 0) return(NA_real_)
    as.numeric(counts[name]) / informative
  }

  data.frame(
    self_renewal=as.integer(counts["self-renewal"]),
    differentiation=as.integer(counts["differentiation"]),
    dedifferentiation=as.integer(counts["dedifferentiation"]),
    uncertain=as.integer(counts["uncertain"]),
    informative_transitions=as.integer(informative),
    total_edges=as.integer(total_edges),
    self_renewal_fraction=frac("self-renewal"),
    differentiation_fraction=frac("differentiation"),
    dedifferentiation_fraction=frac("dedifferentiation"),
    cellular_plasticity=100 * frac("dedifferentiation"),
    stringsAsFactors=FALSE
  )
}

spice_empirical_p <- function(null, observed, alternative="greater") {
  null <- null[is.finite(null)]
  if (length(null) == 0 || !is.finite(observed)) return(NA_real_)

  if (alternative == "greater") {
    b <- sum(null >= observed)
  } else if (alternative == "less") {
    b <- sum(null <= observed)
  } else if (alternative == "two-sided") {
    center <- stats::median(null)
    b <- sum(abs(null - center) >= abs(observed - center))
  } else {
    stop("alternative must be greater, less, or two-sided.")
  }
  (b + 1) / (length(null) + 1)
}

spice_transition_compatibility <- function(transitions) {
  out <- transitions
  colnames(out)[colnames(out) == "parent_node"] <- "parent_label"
  colnames(out)[colnames(out) == "child_node"] <- "child_label"
  out[,c("edge_id", "parent_label", "parent_state", "child_label", "child_state", "transition")]
}
