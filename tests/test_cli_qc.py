"""CLI forwarding, validation, and README parameter coverage (standard library)."""
import pathlib, tempfile, unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from spice_lineage import cli as SPICE
class QCInterface(unittest.TestCase):
 def test_cli_forwarding_and_validation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp); files=[]
   for name in ('tree','states','ancestry','order'):
    p=root/name;p.touch();files.append(str(p))
   parser=SPICE.build_parser()
   for stage,inputs in [('ancestry',files[:2]),('plasticity',files)]:
    args=parser.parse_args([stage,*inputs,str(root/'out'),'sample','--mcmc_seed','47','--rhat_threshold','1.02','--bulk_ess_threshold','500','--tail_ess_threshold','600','--max_retries','1','--retry_multiplier','3'])
    with patch.object(SPICE,'_resolve_bayestraits_binary',return_value='/bin/true'),patch.object(SPICE.subprocess,'run') as run:
     args.func(args)
     cmd=run.call_args.args[0]
     self.assertEqual(cmd[-6:],['1.02','500.0','600.0','1','3.0','47'])
    args.mcmc_seed=0
    with self.assertRaises(ValueError):SPICE._qc_arguments(args)
    args.mcmc_seed=47;args.rhat_threshold=float('nan')
    with self.assertRaises(ValueError):SPICE._qc_arguments(args)
    args.rhat_threshold=1.01;args.min_ancestral_probability=1.1
    with self.assertRaises(ValueError):SPICE._qc_arguments(args)
 def test_readme_options(self):
  doc=(pathlib.Path(__file__).resolve().parents[1]/'README.md').read_text()
  parsers=next(a.choices for a in SPICE.build_parser()._actions if hasattr(a,'choices') and isinstance(a.choices,dict))
  for stage in ('ancestry','plasticity'):
   for action in parsers[stage]._actions:
    for opt in action.option_strings:
     self.assertIn('`'+opt+'`',doc,(stage,opt))
if __name__=='__main__':unittest.main()
