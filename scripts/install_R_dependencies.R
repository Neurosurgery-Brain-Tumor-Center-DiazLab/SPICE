cran <- c("ape","coda","janitor","posterior","dplyr","progress","phangorn",
          "phytools","ggplot2","ggsci","BiocManager")
missing <- cran[!vapply(cran,requireNamespace,logical(1),quietly=TRUE)]
if (length(missing)) install.packages(missing,repos="https://cloud.r-project.org")
if (!requireNamespace("ggtree",quietly=TRUE)) BiocManager::install("ggtree",ask=FALSE,update=FALSE)
