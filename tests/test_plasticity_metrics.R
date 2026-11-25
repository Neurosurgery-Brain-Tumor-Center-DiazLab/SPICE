source('spice_lineage/resources/r/spice_plasticity_utils.R')
s <- spice_summarize_plasticity(data.frame(transition=c(rep('self-renewal',8),'differentiation','dedifferentiation','uncertain')))
stopifnot(s$cellular_plasticity==10,s$P_reverse==50,s$informative_fraction==10/11)
z <- spice_summarize_plasticity(data.frame(transition='self-renewal'))
stopifnot(z$cellular_plasticity==0,is.na(z$P_reverse))
x <- spice_metric_test(c(0,NA,20),rep('ok',3),10,3,'two-sided')
stopifnot(x$test_status=='pass',x$n_permutations_successful==2,x$n_permutations_undefined==1,x$DeltaP==0,x$empirical_p==1)
f <- spice_metric_test(c(0,NA),c('ok','error'),10,2,'greater')
stopifnot(f$test_status=='incomplete',is.na(f$empirical_p))
stopifnot(spice_metric_test(NA,'ok',0,1,'greater')$test_status=='empty_null')
stopifnot(spice_metric_test(0,'ok',NA,1,'greater')$test_status=='undefined_observed')
stopifnot(spice_empirical_p(c(0,0,0,10),10,'two-sided')==.8)
stopifnot(spice_empirical_p(c(0,0,0,10),10,'greater')==.4)
stopifnot(spice_empirical_p(c(0,0,0,10),10,'less')==1)
code <- readLines('spice_lineage/resources/r/plasticity_core.R')
a <- grep('^perm_template <-',code); b <- grep('^if \\(perm_replicates > 0\\)',code)[1]
eval(parse(text=code[a:(b-1)]))
stopifnot(nrow(perm_results)==0,ncol(perm_row(1,s))==ncol(perm_row(2,status='error')))
stopifnot(is.na(perm_row(2,status='error')$self_renewal))
cat('PASS plasticity metric and output-contract tests\n')

# Execute the production completion/exit path with synthetic permutation results.
end <- grep('^cat\\("SPICE plasticity completed',code)
for (good in c(TRUE,FALSE)) {
 perm_replicates <- 2
 observed_summary <- s
 test_summary <- spice_metric_test(c(0,NA),c("ok",if(good) "ok" else "error"),10,2,"greater")
 error <- tryCatch({eval(parse(text=code[end:length(code)])); FALSE},error=function(e) {
   stopifnot(grepl("Permutation test incomplete",conditionMessage(e))); TRUE
 })
 stopifnot(error == !good)
}
