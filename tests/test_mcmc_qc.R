source("scripts/spice_ancestry_utils.R")
source("scripts/spice_plasticity_utils.R")
expect_error <- function(expr, pattern) {
  e <- tryCatch({force(expr); NULL}, error=function(e) e)
  stopifnot(inherits(e,"error"), grepl(pattern,conditionMessage(e)))
}
set.seed(721)
good <- lapply(1:3,function(i) data.frame(iteration=1:4000,q01=rnorm(4000),x1_p_0=runif(4000)))
d <- spice_mcmc_diagnostics(good)
stopifnot(all(d$qc_pass),all(is.finite(d$MCSE_mean)),all(c("ESS","PSRF_point","ESS_bulk","Rhat") %in% names(d)))
bad <- good; bad[[3]]$q01 <- bad[[3]]$q01+8
stopifnot(!spice_mcmc_diagnostics(bad)$qc_pass[1])
constant <- good; constant[[1]]$q01 <- 0
stopifnot(spice_mcmc_diagnostics(constant)$diagnostic_status[1]=="constant_chain")
short <- good; short[[3]] <- short[[3]][-1,]
expect_error(spice_mcmc_diagnostics(short),"grids differ")
missing <- good; missing[[3]]$q01 <- NULL
expect_error(spice_mcmc_diagnostics(missing),"columns differ")
nonfinite <- good; nonfinite[[2]]$q01[5] <- Inf
expect_error(spice_mcmc_diagnostics(nonfinite),"Non-finite")
expect_error(spice_mcmc_diagnostics(good[1]),"two independent")
log <- tempfile()
writeLines(c("Options:","Iteration\tq01","100\t1","200\t2","300\t3","400\t4","500\t5"),log)
x <- spice_clean_bt_results(log,burnin=100,iterations=500,sample_period=100)
stopifnot(nrow(x)==4,"q01" %in% names(x),x$iteration[1]==200)
expect_error(spice_clean_bt_results(log,burnin=100,iterations=600,sample_period=100),"Incomplete")

# Test retry orchestration without spending MCMC time; retain every attempt.
original_runner <- spice_run_ancestry_once
calls <- list()
spice_run_ancestry_once <- function(...){
 a <- list(...); calls[[length(calls)+1]] <<- a
 dir.create(a$output_dir,recursive=TRUE)
 ok <- length(calls)>=2
 for (suf in c(".ancestral_states.tsv",".mcmc_diagnostics.tsv",".state_mapping.tsv",
               ".bayestraits_traits.tsv",".ancestry_run_info.tsv","_ASE.txt"))
   writeLines("fixture",file.path(a$output_dir,paste0(a$prefix,suf)))
 list(run_qc_pass=ok, ancestry=data.frame(node_qc_pass=ok))
}
out <- tempfile()
r <- spice_run_ancestry("tree",output_dir=out,prefix="test",bayestraits_bin="bt",
                        iterations=1000,burnin=200,max_retries=2)
stopifnot(length(calls)==2,calls[[2]]$iterations==2000,calls[[2]]$burnin==400,
          calls[[1]]$chains==3,file.exists(file.path(out,"test.ancestral_states.tsv")))
expect_error(spice_run_ancestry("tree",output_dir=out,prefix="test",bayestraits_bin="bt"),"Existing ancestry")
calls <- list()
out2 <- tempfile()
expect_error(spice_run_ancestry("tree",output_dir=out2,prefix="test",bayestraits_bin="bt",max_retries=0),"model QC failed")
stopifnot(length(calls)==1,!file.exists(file.path(out2,"test.ancestral_states.tsv")))
spice_run_ancestry_once <- function(...) stop("parser defect")
out3 <- tempfile()
expect_error(spice_run_ancestry("tree",output_dir=out3,prefix="test",bayestraits_bin="bt"),"parser defect")
h <- read.delim(file.path(out3,"test.qc_attempts.tsv"))
stopifnot(nrow(h)==1,h$status=="execution_error")
spice_run_ancestry_once <- original_runner

# Downstream blocks legacy/failed inputs and mismatched tree/state provenance.
tree_file <- tempfile(fileext=".nwk")
writeLines("(a:1,b:1);",tree_file)
tree <- spice_read_tree(tree_file)
states <- data.frame(cell_id=c("a","b"),state=c("A","B"))
anc <- data.frame(node_id="T1",inferred_state="A",posterior_probability=.95,confident=TRUE)
af <- tempfile()
write.table(anc,af,sep="\t",row.names=FALSE,quote=FALSE)
expect_error(spice_read_ancestry(af),"lacks QC")
anc$run_qc_pass <- FALSE; anc$node_qc_pass <- TRUE
anc$tree_md5 <- unname(tools::md5sum(tree_file));anc$states_md5 <- spice_state_fingerprint(states)
write.table(anc,af,sep="\t",row.names=FALSE,quote=FALSE)
expect_error(spice_read_ancestry(af),"QC failed")
anc$run_qc_pass <- TRUE;anc$node_qc_pass <- FALSE
write.table(anc,af,sep="\t",row.names=FALSE,quote=FALSE)
a <- spice_read_ancestry(af,tree_file=tree_file,states=states)
tr <- spice_build_transitions(tree,states,a,data.frame(state=c("A","B"),order=0:1))
stopifnot(all(tr$transition=="uncertain"))
changed <- states;changed$state[1] <- "B"
expect_error(spice_read_ancestry(af,tree_file=tree_file,states=changed),"fingerprint")
cat("PASS: modern/legacy diagnostics, parser, retries, failure isolation, downstream QC and provenance\n")

# Changing the analysis cutoff must recover confident nodes without bypassing QC.
anc$posterior_probability <- .85; anc$confident <- FALSE; anc$node_qc_pass <- TRUE
write.table(anc,af,sep="\t",row.names=FALSE,quote=FALSE)
a80 <- spice_read_ancestry(af,min_probability=.8)
a90 <- spice_read_ancestry(af,min_probability=.9)
stopifnot(a80$confident,!a90$confident)
ord <- data.frame(state=c("A","B"),order=0:1)
stopifnot(all(spice_build_transitions(tree,states,a90,ord,.8)$transition != "uncertain"))
stopifnot(all(spice_build_transitions(tree,states,a80,ord,.9)$transition == "uncertain"))
anc$node_qc_pass <- FALSE
write.table(anc,af,sep="\t",row.names=FALSE,quote=FALSE)
stopifnot(!spice_read_ancestry(af,min_probability=.7)$confident)
cat("PASS: posterior cutoff sensitivity preserves convergence gating\n")

stopifnot(spice_derive_seed(12345,0)==12345L,spice_derive_seed(12345,1)==12346L,
          spice_derive_seed(2147483646,1)==1L)
cat("PASS: deterministic seed derivation\n")
