args <- commandArgs(trailingOnly=TRUE)
library(ape)
if (length(args) == 3) {
  original <- read.tree(args[2])
  converted <- read.nexus(args[3])
  stopifnot(is.rooted(converted), identical(original$tip.label, converted$tip.label),
            isTRUE(all.equal.phylo(original, converted, use.edge.length=TRUE, tolerance=1e-14)),
            original$Nnode == converted$Nnode)
  cat("PASS: Newick/NEXUS tree, tips, root and branch lengths preserved\n")
} else {
  out <- args[1]
  tree <- read.tree(file.path(out, "synthetic.fasta.treefile"))
  stopifnot(Ntip(tree) == 13, all(is.finite(tree$edge.length)), all(tree$edge.length >= 0))
  labels <- tree$node.label[grepl("^[0-9.]+/[0-9.]+$", tree$node.label)]
  stopifnot(length(labels) > 0)
  support <- as.numeric(unlist(strsplit(labels,"/",fixed=TRUE)))
  stopifnot(all(is.finite(support)), all(support >= 0 & support <= 100))
  rooted <- root(tree, outgroup="Ref", resolve.root=TRUE)
  stopifnot(is.rooted(rooted))
  assignments <- read.delim(file.path(out,"Clone/synthetic.clone_assignment.tsv"))
  for (clone in unique(na.omit(assignments$clone_id))) {
    expected <- assignments$cell_id[!is.na(assignments$clone_id) & assignments$clone_id == clone]
    nwk <- read.tree(file.path(out, "Clone", clone, paste0(clone, ".nwk")))
    nex <- read.nexus(file.path(out, "Clone", clone, paste0(clone, ".nex")))
    stopifnot(setequal(nwk$tip.label,expected), setequal(nex$tip.label,expected),
              Ntip(nwk)==4, is.rooted(nwk), is.rooted(nex),
              all(is.finite(nwk$edge.length)), all(nwk$edge.length>=0),
              isTRUE(all.equal.phylo(nwk,nex,use.edge.length=TRUE,tolerance=1e-7)))
  }
  cat("PASS: real dual supports and readable rooted clone exports\n")
}
