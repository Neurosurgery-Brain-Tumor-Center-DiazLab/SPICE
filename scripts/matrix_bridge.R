# Base-R interchange only; scientific filtering remains in mutation_filter.R.
args <- commandArgs(trailingOnly=TRUE)
if (args[1] == "export") {
  m <- readRDS(args[2])
  if (is.null(rownames(m)) || is.null(colnames(m)) || length(dim(m)) != 2) stop("RDS requires named variants x cells matrix")
  write.table(data.frame(variant_id=rownames(m), as.matrix(m), check.names=FALSE), args[3], sep="\t", quote=TRUE, row.names=FALSE)
} else if (args[1] == "import") {
  d <- read.delim(args[2], check.names=FALSE, colClasses="character")
  m <- as.matrix(d[,-1,drop=FALSE]); rownames(m) <- d[[1]]
  saveRDS(m, args[3])
} else stop("unknown bridge operation")
