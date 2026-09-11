# Fail before unittest's optional-R skips can conceal missing integration.
required <- c("ape", "coda", "janitor", "posterior", "dplyr", "progress", "parallel")
available <- vapply(required, requireNamespace, logical(1), quietly=TRUE)
if (!all(available)) stop("Missing required R packages: ",
                         paste(required[!available], collapse=", "))
if (packageVersion("posterior") < "1.6.0") stop("posterior >= 1.6.0 required")
cat(R.version.string, "\n")
print(vapply(required, function(p) as.character(packageVersion(p)), character(1)))
sessionInfo()