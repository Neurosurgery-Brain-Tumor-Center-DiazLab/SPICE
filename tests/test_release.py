import csv,json,os,pathlib,subprocess,sys,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from spice_lineage.IQTREE2 import iqtree2_command,generate_script
from spice_lineage.summarize_clones import run_summary,bh_adjust
from spice_lineage.runtime_info import capture_runtime,save_runtime,ROOT
class ReleaseTests(unittest.TestCase):
 def test_shell_characters_are_literal(self):
  with tempfile.TemporaryDirectory(prefix='SPICE path ') as tmp:
   root=pathlib.Path(tmp);binary=root/'fake iqtree'
   binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n');binary.chmod(0o755)
   fasta=root/'input ; literal.fasta';fasta.touch()
   with patch.dict(os.environ,{'IQTREE2_BIN':str(binary)}):cmd=iqtree2_command(str(fasta),tmp,'sample','GTR+G',1000,1000,3)
   direct=subprocess.check_output(cmd,text=True)
   script=generate_script(cmd,tmp,'sample')
   via_script=subprocess.check_output(['bash',script],text=True)
   self.assertEqual(direct,via_script)
   self.assertIn(str(fasta),direct.splitlines())
 def test_bh_and_failed_family_members(self):
  self.assertEqual(bh_adjust([.01,.04,.03]),[.03,.04,.04])
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp)
   def result(name,status,p):
    f=root/name
    f.write_text('test_status\tobserved_plasticity\tempirical_p\talternative\tn_permutations_requested\tn_permutations_successful\n'+f'{status}\t12\t{p}\tgreater\t1000\t'+('1000' if status=='pass' else '0')+'\n')
   result('a.tsv','pass','.01');result('b.tsv','incomplete','NA')
   manifest=root/'manifest.tsv';manifest.write_text('clone_id\tplasticity_test\nA\ta.tsv\nB\tb.tsv\nC\tmissing.tsv\n')
   out=root/'summary.tsv';args=SimpleNamespace(manifest=str(manifest),output=str(out),alpha=.05)
   run_summary(args)
   with out.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
   self.assertEqual(float(rows[0]['q_value']),.03)
   self.assertEqual(rows[1]['q_value'],'NA');self.assertEqual(rows[2]['significant'],'False')
   with self.assertRaises(FileExistsError):run_summary(args)
 def test_runtime_record_preserves_previous_file(self):
  with tempfile.TemporaryDirectory() as tmp:
   args=SimpleNamespace(command='ancestry',output_directory=tmp,prefix='sample')
   with patch('spice_lineage.runtime_info.probe',return_value={'unavailable':'fixture'}):record=capture_runtime(args,ROOT)
   self.assertIn('spice_lineage/cli.py',record['source_sha256'])
   save_runtime(record,args,ROOT,True);save_runtime(record,args,ROOT,False)
   paths=list(pathlib.Path(tmp).glob('*.runtime*.json'));self.assertEqual(len(paths),2)
   self.assertEqual({json.loads(p.read_text())['success'] for p in paths},{True,False})
if __name__=='__main__':unittest.main()
