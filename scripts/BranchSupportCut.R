library(ape)
library(phangorn)
library(phytools)
library(ggplot2)
library(ggtree)
library(ggsci)

args <- commandArgs(trailingOnly = TRUE)
output_directory <- args[1]
sample_id <- args[2]

# thresholds for "trusted" node support
UF_SUPPORT_THRESHOLD <- as.integer(args[3])
SH_SUPPORT_THRESHOLD <- as.integer(args[4])
BRANCH_CUT_MIN <- as.double(args[5])
BRANCH_CUT_MAX <- as.double(args[6])
BRANCH_CUT_STEP <- as.double(args[7])
TIP_THRESHOLD <- as.integer(args[8])	# skip clusters with fewer than tips

# Tree rooting options
ROOT_METHOD <- if (length(args) >= 9) args[9] else "midpoint"
OUTGROUP_STRING <- if (length(args) >= 10) args[10] else "NA"

# Final clone-cut threshold selection options
CLONE_CUT_MODE <- if (length(args) >= 11) args[11] else "auto"
MANUAL_CLONE_CUT_THRESHOLD <- if (length(args) >= 12) suppressWarnings(as.double(args[12])) else NA_real_
MIN_TRUSTED_RATIO <- if (length(args) >= 13) as.double(args[13]) else 0.95
MIN_PARTITION_STABILITY <- if (length(args) >= 14) as.double(args[14]) else 0.95
STABILITY_WINDOW <- if (length(args) >= 15) as.integer(args[15]) else 3

if (!(CLONE_CUT_MODE %in% c("auto", "manual"))) {
  stop("CLONE_CUT_MODE must be either 'auto' or 'manual'.")
}
if (CLONE_CUT_MODE == "manual" && is.na(MANUAL_CLONE_CUT_THRESHOLD)) {
  stop("Manual clone-cut mode requires a numeric clone-cut threshold.")
}
if (MIN_TRUSTED_RATIO < 0 || MIN_TRUSTED_RATIO > 1) {
  stop("MIN_TRUSTED_RATIO must be between 0 and 1.")
}
if (MIN_PARTITION_STABILITY < 0 || MIN_PARTITION_STABILITY > 1) {
  stop("MIN_PARTITION_STABILITY must be between 0 and 1.")
}
if (is.na(STABILITY_WINDOW) || STABILITY_WINDOW < 2) {
  stop("STABILITY_WINDOW must be >= 2.")
}

# Preserve historical SPICE behavior when no rooting option is supplied.
if (is.na(ROOT_METHOD) || ROOT_METHOD == "") {
  ROOT_METHOD <- "midpoint"
}

# Parse optional comma-separated outgroup tips passed from SPICE.py.
if (is.na(OUTGROUP_STRING) || OUTGROUP_STRING == "" || OUTGROUP_STRING == "NA") {
  OUTGROUPS <- character(0)
} else {
  OUTGROUPS <- trimws(strsplit(OUTGROUP_STRING, ",", fixed=TRUE)[[1]])
}

BRANCH_SEQ <- seq(BRANCH_CUT_MIN, BRANCH_CUT_MAX, by=BRANCH_CUT_STEP)	# range of branch-length cut thresholds

treefile <- paste0(output_directory, sample_id, ".fasta.treefile")
if (!file.exists(treefile)) {
  stop(paste("Phylogenetic tree file not found:", treefile))
}

output_path <- paste0(output_directory, "Phylo/")
if (!dir.exists(output_path)) {
  dir.create(output_path, recursive=TRUE)
  cat("Directory created:", output_path, "\n")
}

clone_path <- paste0(output_directory, "Clone/")
if (!dir.exists(clone_path)) {
  dir.create(clone_path, recursive=TRUE)
  cat("Directory created:", clone_path, "\n")
}

########################################################
## 1. Read and Root the Tree
########################################################
# Read IQ-TREE output
unrooted_tree <- read.tree(treefile)

if (is.null(unrooted_tree)) {
  stop(paste("Failed to read phylogenetic tree:", treefile))
}

# Rooting priority:
#   1. Explicit outgroup tip(s), when supplied
#   2. User-selected ROOT_METHOD
#   3. Midpoint rooting by default for backward compatibility
if (length(OUTGROUPS) > 0) {

  missing_outgroups <- setdiff(OUTGROUPS, unrooted_tree$tip.label)

  if (length(missing_outgroups) > 0) {
    stop(
      paste(
        "The following outgroup tip(s) were not found in the tree:",
        paste(missing_outgroups, collapse=", ")
      )
    )
  }

  cat("Rooting method: outgroup\n")
  cat("Outgroup tip(s):", paste(OUTGROUPS, collapse=", "), "\n")

  rooted_tree <- root(
    unrooted_tree,
    outgroup=OUTGROUPS,
    resolve.root=TRUE
  )
  ROOT_METHOD_USED <- "outgroup"

} else if (ROOT_METHOD == "midpoint") {

  cat("Rooting method: midpoint\n")
  rooted_tree <- midpoint(unrooted_tree)
  ROOT_METHOD_USED <- "midpoint"

} else if (ROOT_METHOD == "none") {

  cat("Rooting method: none\n")
  rooted_tree <- unrooted_tree

  if (!is.rooted(rooted_tree)) {
    stop(
      paste(
        "ROOT_METHOD='none' was requested, but the input tree is not rooted.",
        "Provide a rooted tree or use midpoint/outgroup rooting."
      )
    )
  }
  ROOT_METHOD_USED <- "none"

} else if (ROOT_METHOD == "outgroup") {

  stop("ROOT_METHOD='outgroup' requires at least one outgroup tip.")

} else {

  stop(paste("Unsupported rooting method:", ROOT_METHOD))
}

if (!is.rooted(rooted_tree)) {
  stop(paste("Tree rooting failed using method:", ROOT_METHOD_USED))
}

cat("Tree successfully rooted using:", ROOT_METHOD_USED, "\n")

# Save rooting metadata for reproducibility
rooting_info <- data.frame(
  sample_id=sample_id,
  root_method=ROOT_METHOD_USED,
  outgroup=if (length(OUTGROUPS) > 0) paste(OUTGROUPS, collapse=",") else NA_character_,
  stringsAsFactors=FALSE
)

write.table(
  rooting_info,
  file=paste0(output_path, sample_id, ".rooting_info.tsv"),
  sep="\t",
  quote=FALSE,
  row.names=FALSE
)

pdf(paste0(output_path, sample_id, ".rooted_tree.pdf"), width=10, height=8)
p <- ggtree(rooted_tree, branch.length='none', layout='circular') +
	geom_tippoint(shape=21, size=2, fill="#f0cd82", color=NA) +
	theme_tree2()

print(p)
dev.off()

pdf(paste0(output_path, sample_id, ".rooted_tree_with_branch_length.pdf"), width=10, height=8)
p <- ggtree(rooted_tree, branch.length='branch.length', layout='circular') +
        geom_tippoint(shape=21, size=2, fill="#f0cd82", color=NA) +
	geom_treescale(
		width=0.10,   # length of the scale bar in branch-length units
		linesize=0.8, # thickness of the scale bar line
		offset=2      # vertical offset from the bottom tips (adjust as needed)
		) +
	theme_tree2()

print(p)
dev.off()

tip_count <- length(rooted_tree$tip.label)
pdf(paste0(output_path, sample_id, ".rooted_tree_with_branch_support.pdf"), width=12, height=10)
p <- ggtree(rooted_tree, branch.length='none', layout='circular') +
        geom_tippoint(shape=21, size=2, fill="#f0cd82", color=NA) +
	geom_text2(
		data = function(x) x[x$node > tip_count, ],
		aes(label = label),
		hjust = -0.3, vjust = -0.5, size = 3
		) +
	theme_tree2()

print(p)
dev.off()

pdf(paste0(output_path, sample_id, ".rooted_tree_with_branch_length_support.pdf"), width=12, height=10)
p <- ggtree(rooted_tree, branch.length='branch.length', layout='circular') +
        geom_tippoint(shape=21, size=2, fill="#f0cd82", color=NA) +
        geom_treescale(
                width=0.10,   # length of the scale bar in branch-length units
                linesize=0.8, # thickness of the scale bar line
                offset=2      # vertical offset from the bottom tips (adjust as needed)
                ) +
        geom_text2(
                data = function(x) x[x$node > tip_count, ],
                aes(label = label),
                hjust = -0.3, vjust = -0.5, size = 3
                ) +
        theme_tree2()

print(p)
dev.off()

# Basic info
cat("Number of tips:", Ntip(rooted_tree), "\n")
cat("Number of internal nodes:", Nnode(rooted_tree), "\n")

# Read label info (tip -> discrete label)
# Format: two columns: tip_name, label
#label_df <- read.table(label_file, header=FALSE, stringsAsFactors=FALSE)
#colnames(label_df) <- c("tip", "group")

########################################################
## 2. Examine distribution of branch lengths
##    and distribution of node supports
########################################################
# 'rooted_tree$edge.length' gives vector of branch lengths
branch_lengths <- rooted_tree$edge.length

# Node-Label parsing
# Suppose node labels look like "79.2/73", meaning (SH-aLRT=79.2, UFBoot=73).
parse_node_label <- function(lbl) {
    if (is.na(lbl) || lbl == "") {
        return(c(
            SHaLRT = NA_real_,
            UFBoot = NA_real_
        ))
    }
    parts <- strsplit(lbl, "/", fixed = TRUE)[[1]]
    if (length(parts) == 2) {
        # IQ-TREE with --alrt and -B reports:
        # SH-aLRT / UFBoot
        sh_val <- suppressWarnings(as.numeric(parts[1]))
        uf_val <- suppressWarnings(as.numeric(parts[2]))
    } else {
        sh_val <- NA_real_
        uf_val <- NA_real_
    }
    return(c(
        SHaLRT = sh_val,
        UFBoot = uf_val
    ))
}

# We'll parse all node labels into numeric vectors
all_supports <- as.data.frame(
    t(sapply(rooted_tree$node.label, parse_node_label))
)

sh_values <- all_supports$SHaLRT
uf_values <- all_supports$UFBoot

# Let's visualize these distributions and store them in a PDF
## 2A. Branch-length distribution
pdf(paste0(output_path, "branch_length_distributions.pdf"), width=8, height=5)
df_bl <- data.frame(branch_length = branch_lengths)
p_bl <- ggplot(df_bl, aes(x=branch_length)) +
  geom_histogram(aes(y=after_stat(density)), fill="#a1d99b", color="black", alpha=0.6) +
  geom_density(color="black", linewidth=1) +
  theme_classic() +
  labs(
    title="Distribution of Branch Lengths",
    x="Branch length",
    y="Density"
  ) #+
  #scale_x_continuous(
    #limits=c(0,0.1),
    #breaks=seq(0,0.5,by=0.02)
  #)

print(p_bl)
dev.off()

## 2B. UFBoot distribution
if (sum(uf_values, na.rm=TRUE) > 0) {
  pdf(paste0(output_path, "UFBoot_distributions.pdf"), width=8, height=5)
  df_uf <- data.frame(UFBoot = uf_values)
  df_uf <- subset(df_uf, UFBoot > 0)
  p_uf <- ggplot(df_uf, aes(x=UFBoot)) +
    geom_histogram(aes(y=after_stat(density)), fill="#feb24c", color="black", alpha=0.6) +
    geom_density(color="black", linewidth=1) +
    theme_classic() +
    labs(
      title="Distribution of UFBoot Values",
      x="UFBoot",
      y="Density"
    ) +
    scale_x_continuous(
      #limits=c(0,100),
      breaks=seq(0,100,by=5)
    )

  print(p_uf)
  dev.off()
}

## 2C. SH-aLRT distribution
pdf(paste0(output_path, "SHaLRT_distributions.pdf"), width=8, height=5)
df_sh <- data.frame(SHaLRT=sh_values)
df_sh <- subset(df_sh, SHaLRT > 0)
p_sh <- ggplot(df_sh, aes(x=SHaLRT)) +
  geom_histogram(aes(y=after_stat(density)), fill="#ffeda0", color="black", alpha=0.6) +
  geom_density(color="black", linewidth=1) +
  theme_classic() +
  labs(
    title="Distribution of SH-aLRT Values",
    x="SH-aLRT",
    y="Density"
  ) +
  scale_x_continuous(
    #limits=c(0,100),
    breaks=seq(0,100,by=5)
  )

print(p_sh)
dev.off()

cat("Saved branch length & node support distributions to 'branch_length_and_support_distributions.pdf'\n")

########################################################
## 3. Function to Cut the Tree by Branch-Length Threshold
########################################################
# We'll implement a "top-down" DFS:
# If the edge leading to a node is >= branchLengthThreshold,
# we cut there -> define a new cluster (subtree).
# We'll also mark it as "trusted" if that node label meets support cutoffs.

cut_tree_by_threshold <- function(tree, node_id,
                                  branchLengthThreshold,
                                  uf_thr=90, sh_thr=75) {
  # 'tree' is assumed to be rooted/bifurcating.
  # 'node_id' can be tip (1..Ntip) or internal node (Ntip+1 .. Ntip+Nnode).
  # We'll return a list with:
  #   $clusters -> a list of vectors (tip labels)
  #   $unassigned -> a character vector of tips not yet clustered under this node

  # If it's a tip, just return that tip (cannot subdivide further).
  if (node_id <= Ntip(tree)) {
    tips <- tree$tip.label[node_id]
    return(list(
      clusters = list(),  # no new cluster from an internal node
      unassigned = tips
    ))
  }

  # Parse the node label (ultrafast bootstrap / SH-aLRT)
  label_idx <- node_id - Ntip(tree)
  node_label <- tree$node.label[label_idx]
  parsed     <- parse_node_label(node_label)
  uf_val     <- parsed["UFBoot"]
  sh_val     <- parsed["SHaLRT"]
  if(is.na(uf_val)) uf_val <- 0
  if(is.na(sh_val)) sh_val <- 0

  # Find the edge length from this node's parent. The root has no parent edge, length=0.
  # tree$edge is a matrix with rows: (parent, child)
  parent_edge_idx <- which(tree$edge[,2] == node_id)
  edge_len <- if (length(parent_edge_idx) == 1) {
    tree$edge.length[parent_edge_idx]
  } else {
    0  # root node
  }

  # If edge_len >= branchLengthThreshold, we "cut" here => define a new cluster = all descendant tips
  # Check if this node is "trusted" (based on node label)
  if (edge_len >= branchLengthThreshold &&
      uf_val >= uf_thr && sh_val >= sh_thr) {

    # Extract all descendant tips
    sub_clade <- extract.clade(tree, node_id)
    tips_in_subclade <- sub_clade$tip.label

    # We'll define a single cluster from this node, and return no "unassigned" tips from it
    return(list(
      clusters = list(list(
        tips       = tips_in_subclade,
        uf_boot    = uf_val,
        sh_alrt    = sh_val,
        edge_len   = edge_len,
        trusted    = TRUE  # because it meets thresholds
      )),
      unassigned = character(0)
    ))
  }

  # Otherwise, we descend into children
  child_rows <- which(tree$edge[,1] == node_id)
  if (length(child_rows) < 2) {
    # Possibly a polytomy or a leaf
    # For simplicity, assume binary tree. If not, adapt logic.
    # Return everything as unassigned
    return(list(clusters=list(), unassigned=character(0)))
  }

  child1 <- tree$edge[child_rows[1], 2]
  child2 <- tree$edge[child_rows[2], 2]

  # Recur on children
  res1 <- cut_tree_by_threshold(tree, child1, branchLengthThreshold, uf_thr, sh_thr)
  res2 <- cut_tree_by_threshold(tree, child2, branchLengthThreshold, uf_thr, sh_thr)

  # Combine child clusters
  all_clusters <- c(res1$clusters, res2$clusters)

  # We haven't formed a cluster at THIS node, but let's see if we can label it anyway
  # If the node doesn't meet the branch-length threshold, it doesn't form a new cluster,
  # but we might still mark it "trusted" or not for reference. However, no new cluster is formed.
  # We'll handle that in a future extension if needed.

  # Combine unassigned tips from children
  unassigned <- c(res1$unassigned, res2$unassigned)
  return(list(
    clusters   = all_clusters,
    unassigned = unassigned
  ))
}

# We'll wrap it with a helper that also clusters any leftover "unassigned" tips
# (i.e., if the node doesn't meet threshold, we eventually get tips that were never cut).
cut_tree_wrapper <- function(tree, branchLengthThreshold,
                             uf_thr=90, sh_thr=75) {

  root_node <- Ntip(tree) + 1
  res <- cut_tree_by_threshold(tree, root_node, branchLengthThreshold, uf_thr, sh_thr)

  # If any tips remain unassigned, we group them as a "low-support" cluster
  # or we can check if it has multiple sets of unassigned tips from different subtrees
  if (length(res$unassigned) > 0) {
    # One cluster of leftover tips
    leftover <- list(
      tips      = res$unassigned,
      uf_boot   = NA,
      sh_alrt   = NA,
      edge_len  = NA,
      trusted   = FALSE
    )
    res$clusters <- c(res$clusters, list(leftover))
    res$unassigned <- character(0)
  }

  return(res$clusters)
}

########################################################
## 4. Iterate Over Branch-Length Thresholds
##    and quantify partition stability
########################################################

cluster_assignment_vector <- function(tree, clusters) {
  assignment <- rep(NA_integer_, Ntip(tree))
  names(assignment) <- tree$tip.label

  for (i in seq_along(clusters)) {
    assignment[clusters[[i]]$tips] <- i
  }

  if (any(is.na(assignment))) {
    stop("At least one tree tip was not assigned to a partition.")
  }

  assignment[tree$tip.label]
}

# Adjusted Rand Index implemented locally to avoid an additional dependency.
adjusted_rand_index <- function(labels_a, labels_b) {
  if (length(labels_a) != length(labels_b)) {
    stop("ARI requires assignment vectors of identical length.")
  }

  n <- length(labels_a)
  if (n < 2) {
    return(1)
  }

  tab <- table(labels_a, labels_b)
  choose2 <- function(x) x * (x - 1) / 2

  sum_comb <- sum(choose2(tab))
  sum_rows <- sum(choose2(rowSums(tab)))
  sum_cols <- sum(choose2(colSums(tab)))
  total_pairs <- choose2(n)

  if (total_pairs == 0) {
    return(1)
  }

  expected <- (sum_rows * sum_cols) / total_pairs
  max_index <- 0.5 * (sum_rows + sum_cols)
  denominator <- max_index - expected

  if (abs(denominator) < .Machine$double.eps) {
    return(ifelse(identical(as.integer(labels_a), as.integer(labels_b)), 1, 0))
  }

  (sum_comb - expected) / denominator
}

results_list <- list()
assignment_list <- list()

for (i in seq_along(BRANCH_SEQ)) {
  th <- BRANCH_SEQ[i]

  cl_list <- cut_tree_wrapper(
    tree = rooted_tree,
    branchLengthThreshold = th,
    uf_thr = UF_SUPPORT_THRESHOLD,
    sh_thr = SH_SUPPORT_THRESHOLD
  )

  n_clusters <- length(cl_list)
  n_trusted <- sum(sapply(cl_list, function(x) isTRUE(x$trusted)))
  n_untrusted <- n_clusters - n_trusted
  pass_ratio <- if (n_clusters > 0) n_trusted / n_clusters else 0

  n_exportable <- sum(
    sapply(
      cl_list,
      function(x) isTRUE(x$trusted) && length(x$tips) >= TIP_THRESHOLD
    )
  )

  assignment_list[[i]] <- cluster_assignment_vector(rooted_tree, cl_list)

  results_list[[i]] <- data.frame(
    threshold = th,
    n_clusters = n_clusters,
    n_trusted = n_trusted,
    n_untrusted = n_untrusted,
    n_exportable = n_exportable,
    pass_ratio = pass_ratio,
    stringsAsFactors = FALSE
  )
}

res_df <- do.call(rbind, results_list)

# Compare adjacent thresholds using cell-level partition concordance.
ari_prev <- rep(NA_real_, nrow(res_df))
ari_next <- rep(NA_real_, nrow(res_df))

if (nrow(res_df) > 1) {
  for (i in seq_len(nrow(res_df) - 1)) {
    ari_val <- adjusted_rand_index(
      assignment_list[[i]],
      assignment_list[[i + 1]]
    )
    ari_next[i] <- ari_val
    ari_prev[i + 1] <- ari_val
  }
}

res_df$ari_prev <- ari_prev
res_df$ari_next <- ari_next
res_df$partition_stability <- ifelse(
  is.na(ari_prev),
  ari_next,
  ifelse(
    is.na(ari_next),
    ari_prev,
    pmin(ari_prev, ari_next)
  )
)

########################################################
## 5. Select final clone-cut threshold
########################################################

# Automatic selection:
#   1) trusted ratio >= predefined minimum
#   2) adjacent partition ARI >= predefined minimum
#   3) criteria persist across a consecutive stable window
#   4) among stable solutions, prefer fewer subtrees
#   5) if the same parsimonious solution persists, use the plateau center
select_threshold_auto <- function(df,
                                  min_trusted_ratio = 0.95,
                                  min_stability = 0.95,
                                  stability_window = 3) {

  candidate <- (
    df$pass_ratio >= min_trusted_ratio &
    !is.na(df$partition_stability) &
    df$partition_stability >= min_stability
  )

  run_info <- rle(candidate)
  run_end <- cumsum(run_info$lengths)
  run_start <- run_end - run_info$lengths + 1

  stable_indices <- integer(0)

  for (j in seq_along(run_info$values)) {
    if (isTRUE(run_info$values[j]) &&
        run_info$lengths[j] >= stability_window) {
      stable_indices <- c(
        stable_indices,
        seq.int(run_start[j], run_end[j])
      )
    }
  }

  if (length(stable_indices) == 0) {
    stop(
      paste0(
        "Automatic clone-cut selection failed: no stable threshold region ",
        "contains at least ", stability_window,
        " consecutive thresholds with trusted ratio >= ",
        min_trusted_ratio,
        " and partition stability >= ", min_stability,
        ". Inspect branch_length_cut_analysis.tsv and use manual mode, ",
        "or adjust the predefined automatic-selection criteria."
      )
    )
  }

  stable_df <- df[stable_indices, , drop = FALSE]

  min_clusters <- min(stable_df$n_clusters)
  parsimonious_idx <- stable_indices[
    stable_df$n_clusters == min_clusters
  ]

  # Split parsimonious solutions into consecutive threshold plateaus.
  group_id <- cumsum(c(1, diff(parsimonious_idx) != 1))
  plateau_runs <- split(parsimonious_idx, group_id)

  plateau_lengths <- vapply(plateau_runs, length, integer(1))
  longest_length <- max(plateau_lengths)
  longest_runs <- plateau_runs[plateau_lengths == longest_length]

  # Resolve equally long plateaus by higher trusted ratio, then stability.
  run_scores <- lapply(longest_runs, function(idx) {
    c(
      median_pass = median(df$pass_ratio[idx]),
      median_stability = median(df$partition_stability[idx], na.rm = TRUE)
    )
  })
  run_scores_df <- as.data.frame(do.call(rbind, run_scores))
  best_order <- order(
    -run_scores_df$median_pass,
    -run_scores_df$median_stability
  )
  best_run <- longest_runs[[best_order[1]]]

  plateau_center <- median(df$threshold[best_run])
  selected_idx <- best_run[
    which.min(abs(df$threshold[best_run] - plateau_center))
  ]

  list(
    threshold = df$threshold[selected_idx],
    selected_index = selected_idx,
    stable_indices = stable_indices,
    plateau_indices = best_run,
    n_clusters = df$n_clusters[selected_idx]
  )
}

res_df$eligible <- FALSE
res_df$selected <- FALSE
res_df$selection_plateau <- FALSE

if (CLONE_CUT_MODE == "manual") {
  final_threshold <- MANUAL_CLONE_CUT_THRESHOLD
  selection_reason <- "user-specified manual threshold"

  # Mark the nearest swept threshold for visualization only.
  nearest_idx <- which.min(abs(res_df$threshold - final_threshold))
  res_df$selected[nearest_idx] <- TRUE

  cat("Clone-cut mode: manual\n")
  cat("Chosen final threshold:", final_threshold, "\n")

} else {
  auto_selection <- select_threshold_auto(
    res_df,
    min_trusted_ratio = MIN_TRUSTED_RATIO,
    min_stability = MIN_PARTITION_STABILITY,
    stability_window = STABILITY_WINDOW
  )

  final_threshold <- auto_selection$threshold
  res_df$eligible[auto_selection$stable_indices] <- TRUE
  res_df$selection_plateau[auto_selection$plateau_indices] <- TRUE
  res_df$selected[auto_selection$selected_index] <- TRUE

  selection_reason <- paste0(
    "automatic stable-parsimonious selection: trusted ratio >= ",
    MIN_TRUSTED_RATIO,
    ", partition stability >= ",
    MIN_PARTITION_STABILITY,
    ", stable window >= ",
    STABILITY_WINDOW,
    " thresholds; selected center of parsimonious plateau"
  )

  cat("Clone-cut mode: auto\n")
  cat("Chosen final threshold:", final_threshold, "\n")
  cat("Selected number of subtrees:", auto_selection$n_clusters, "\n")
}

# Save the complete sweep and the selection decision.
write.table(
  res_df,
  paste0(output_path, "branch_length_cut_analysis.tsv"),
  sep = "\t",
  quote = FALSE,
  row.names = FALSE
)

selection_info <- data.frame(
  sample_id = sample_id,
  mode = CLONE_CUT_MODE,
  selected_threshold = final_threshold,
  min_trusted_ratio = if (CLONE_CUT_MODE == "auto") MIN_TRUSTED_RATIO else NA_real_,
  min_partition_stability = if (CLONE_CUT_MODE == "auto") MIN_PARTITION_STABILITY else NA_real_,
  stability_window = if (CLONE_CUT_MODE == "auto") STABILITY_WINDOW else NA_integer_,
  reason = selection_reason,
  stringsAsFactors = FALSE
)

write.table(
  selection_info,
  paste0(output_path, sample_id, ".clone_cut_selection.tsv"),
  sep = "\t",
  quote = FALSE,
  row.names = FALSE
)

# QC plots
pdf(paste0(output_path, "branch_cut_analysis.pdf"), width=7, height=4)

p1 <- ggplot(res_df, aes(x=threshold)) +
  geom_line(aes(y=n_clusters, color="Total Clusters")) +
  geom_line(aes(y=n_trusted, color="Trusted Clusters")) +
  geom_point(aes(y=n_clusters, color="Total Clusters")) +
  geom_point(aes(y=n_trusted, color="Trusted Clusters")) +
  geom_vline(xintercept=final_threshold, linetype="dashed") +
  theme_classic() +
  labs(
    x="Root-to-clade distance threshold",
    y="Number of clusters",
    title="Clustering vs clone-cut threshold",
    color="Legend"
  ) +
  scale_color_manual(values = c(
    "Total Clusters" = "black",
    "Trusted Clusters" = "#bc3282"
  ))
print(p1)

p2 <- ggplot(res_df, aes(x=threshold, y=pass_ratio, color="Trusted Ratio")) +
  geom_line() +
  geom_point() +
  geom_hline(yintercept=MIN_TRUSTED_RATIO, linetype="dotted") +
  geom_vline(xintercept=final_threshold, linetype="dashed") +
  theme_classic() +
  labs(
    x="Root-to-clade distance threshold",
    y="Trusted Cluster Ratio",
    title="Trusted cluster ratio by threshold",
    color="Legend"
  ) +
  scale_color_manual(values = c("Trusted Ratio" = "#365f9d"))
print(p2)

p3 <- ggplot(res_df, aes(x=threshold, y=partition_stability)) +
  geom_line() +
  geom_point() +
  geom_hline(yintercept=MIN_PARTITION_STABILITY, linetype="dotted") +
  geom_vline(xintercept=final_threshold, linetype="dashed") +
  theme_classic() +
  labs(
    x="Root-to-clade distance threshold",
    y="Adjusted Rand Index",
    title="Partition stability across adjacent thresholds"
  )
print(p3)

dev.off()
cat("Plots saved to 'branch_cut_analysis.pdf'\n")

final_clusters <- cut_tree_wrapper(
  rooted_tree,
  final_threshold,
  UF_SUPPORT_THRESHOLD,
  SH_SUPPORT_THRESHOLD
)

cat("Number of final clusters:", length(final_clusters), "\n")
cat(
  "Number of trusted clusters:",
  sum(sapply(final_clusters, function(x) isTRUE(x$trusted))),
  "\n"
)

########################################################
## 6. Visualization + NEXUS Export for ASE
########################################################
# We'll create a new PDF to visualize each trusted subtree.
pdf(paste0(output_path, "trusted_clusters.pdf"), width=8, height=6)

cluster_index <- 0
for (i in seq_along(final_clusters)) {
  cl_info <- final_clusters[[i]]

  # Skip untrusted cluster
  if (!cl_info$trusted) {
    # Untrusted => skip
    next
  }

  tips <- cl_info$tips
  # Skip if cluster is too small
  if (length(tips) < TIP_THRESHOLD) {
    next
  }

  # Create a subtree
  sub_tree <- keep.tip(rooted_tree, tips)

  # Plot
  cluster_index <- cluster_index + 1
  final_clusters[[i]]$cluster_index <- paste0("Clone_", cluster_index)
  plot_title <- paste(
	"Trusted Cluster #", cluster_index,
	"(", length(tips), "tips )",
	"\nUFBoot>=", UF_SUPPORT_THRESHOLD,
	", SH-aLRT>=", SH_SUPPORT_THRESHOLD,
	", Edge>=", final_threshold)

  # Now use ggtree for a circular layout, no branch lengths, custom tip points
  p <- ggtree(sub_tree, branch.length='none', layout='circular') +
	geom_tippoint(shape=21, size=2, fill="#f0cd82", color=NA) +
	theme_tree2() +
	ggtitle(plot_title)

  print(p)

  # Now export to NEXUS for BayesTraits
  subclone_path <- paste0(clone_path, "Clone_", cluster_index, "/")
  if (!dir.exists(subclone_path)) {
	dir.create(subclone_path, recursive=TRUE)
  }
  nexus_file <- paste0(subclone_path, "Clone_", cluster_index, ".nex")
  writeNexus(sub_tree, file = nexus_file)
  cat("Wrote NEXUS file:", nexus_file, "\n")

  # Create the Newick file name and save the subtree in Newick format
  newick_file <- paste0(subclone_path, "Clone_", cluster_index, ".nwk")
  write.tree(sub_tree, file = newick_file)
  cat("Wrote Newick file:", newick_file, "\n")
}

dev.off()
cat("Saved trusted cluster trees to 'trusted_clusters.pdf'\n")

# We'll define a function to find which cluster (if any) a tip belongs to,
# and whether that cluster is "trusted & large enough" or not.
assign_cluster_info <- function(tip, final_clusters, TIP_THRESHOLD) {
  # This function returns a list: (isTrustedCluster=TRUE/FALSE, clusterIndex=..., reason="small"/"untrusted"/"none")

  # We'll check each cluster in 'final_clusters'
  # Remember final_clusters is a list of cluster_info: { tips, trusted, ... }
  for (i in seq_along(final_clusters)) {
    cl <- final_clusters[[i]]
    if (tip %in% cl$tips) {
      # Found tip in this cluster
      if (!cl$trusted) {
        return(list(ok=FALSE, reason="untrusted"))
      } else {
        # cluster is trusted, but is it large enough?
        if (length(cl$tips) < TIP_THRESHOLD) {
          return(list(ok=FALSE, reason="small"))
        } else {
          # trusted & large enough
          return(list(ok=TRUE, reason=cl$cluster_index))
        }
      }
    }
  }

  # If we never found the tip, it might be in leftover untrusted cluster
  return(list(ok=FALSE, reason="none"))
}

# Build a data frame with one row per tip in the entire rooted_tree
all_tips <- data.frame(
  tip = rooted_tree$tip.label,
  stringsAsFactors = FALSE
)

# Add the "state_label" from label_df (the cell state)
#    We'll do a simple merge on tip name
#    label_df has columns: tip, group
#    We'll call it "state_label" in all_tips
#all_tips <- merge(all_tips, label_df, by="tip", all.x=TRUE)
# Now all_tips has columns: tip, group (where group is e.g. "UBC-early")
#colnames(all_tips)[2] <- "state_label"

# For each tip, figure out if it's in a trusted & big-enough cluster
cluster_assignments <- lapply(all_tips$tip, function(tip) {
  assign_cluster_info(tip, final_clusters, TIP_THRESHOLD)
})

# Convert that list into data frame columns: is_ok, reason
all_tips$in_trusted_cluster <- sapply(cluster_assignments, function(x) x$ok)  # TRUE/FALSE
all_tips$cluster_reason <- sapply(cluster_assignments, function(x) x$reason)
# cluster_reason might be "Clone1", "Clone2", "untrusted", "small", or "none"

# Define a final factor for tip color
#    - If in_trusted_cluster == TRUE, we use the state_label
#    - If FALSE, we use "untrusted_or_small"
all_tips$color_group <- ifelse(
  all_tips$in_trusted_cluster,
  all_tips$cluster_reason,
  "untrusted_or_small"
)

unique_labels <- unique(all_tips$color_group)
sorted_labels <- unique_labels[order(unique_labels == "untrusted_or_small", as.numeric(gsub("[^0-9]", "", unique_labels)))]
all_tips$color_group <- factor(all_tips$color_group, levels = sorted_labels)

c25 <- c(
  "yellow", "dodgerblue2", "green4", "#6A3D9A", "#FF7F00",
  "black", "gold1", "skyblue2", "#FB9A99", "palegreen2",
  "#CAB2D6", "#FDBF6F", "gray70", "khaki2", "maroon",
  "orchid1", "deeppink1", "blue1", "steelblue4", "darkturquoise",
  "green1", "yellow3", "#E31A1C", "darkorange4", "brown"
)

c16 <- pal_simpsons("springfield", alpha=.8)(16)

pdf(paste0(output_path, "rooted_tree_clustered.pdf"), width=10, height=8)
p <- ggtree(rooted_tree, layout="circular", branch.length="none") %<+% all_tips +
  geom_tippoint(aes(fill=color_group), shape=21, size=2) +
  scale_fill_manual(values=c25) +
  #scale_fill_manual(values=c16) +
  # Hide tip labels
  theme(legend.title = element_blank()) +
  theme_tree2()

print(p)
dev.off()

pdf(paste0(output_path, "rooted_tree_clustered_with_brach_length.pdf"), width=10, height=8)
p <- ggtree(rooted_tree, layout="circular") %<+% all_tips +
  geom_tippoint(aes(fill=color_group), shape=21, size=2) +
  scale_fill_manual(values=c25) +
  #scale_fill_manual(values=c16) +
  # Hide tip labels
  theme(legend.title = element_blank()) +
  theme_tree2()

print(p)
dev.off()
