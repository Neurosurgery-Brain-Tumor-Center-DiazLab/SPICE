# Independent real-R comparison, matching exports by tip set rather than clone ID.
library(ape)
args <- commandArgs(trailingOnly=TRUE)
stopifnot(length(args) == 2)

exports <- function(out) {
  assignments <- read.delim(file.path(out, "Clone/synthetic.clone_assignment.tsv"))
  ids <- unique(na.omit(assignments$clone_id))
  directories <- list.dirs(file.path(out, "Clone"), recursive=FALSE, full.names=FALSE)
  stopifnot(setequal(directories, ids))
  result <- list()
  for (id in ids) {
    expected <- sort(assignments$cell_id[!is.na(assignments$clone_id) & assignments$clone_id == id])
    key <- paste(expected, collapse="|")
    stopifnot(is.null(result[[key]]))
    directory <- file.path(out, "Clone", id)
    stopifnot(setequal(list.files(directory), paste0(id, c(".nwk", ".nex"))))
    trees <- list(nwk=read.tree(file.path(directory, paste0(id, ".nwk"))),
                  nex=read.nexus(file.path(directory, paste0(id, ".nex"))))
    for (tree in trees) {
      stopifnot(setequal(tree$tip.label, expected), Ntip(tree) == length(expected),
                is.rooted(tree), all(is.finite(tree$edge.length)), all(tree$edge.length >= 0))
    }
    stopifnot(isTRUE(all.equal.phylo(trees$nwk, trees$nex, use.edge.length=TRUE, tolerance=1e-7)))
    result[[key]] <- trees
  }
  result
}

combined <- exports(args[1])
standalone <- exports(args[2])
stopifnot(length(combined) == 3, setequal(names(combined), names(standalone)))
for (key in names(combined)) {
  for (format in c("nwk", "nex")) {
    left <- combined[[key]][[format]]
    right <- standalone[[key]][[format]]
    stopifnot(left$Nnode == right$Nnode,
              isTRUE(all.equal.phylo(left, right, use.edge.length=TRUE, tolerance=1e-12)),
              isTRUE(all.equal(left$root.edge, right$root.edge, tolerance=1e-12)))
  }
}
cat("PASS: same exportable clone count, tip sets, rooted topology and branch lengths in both formats\n")
