"""Caller-independent schema, real R filtering equivalence, and downstream forwarding."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import SPICE
from scripts.standard_input import load_bundle, validate, write_bundle, read_table, write_table
from scripts.import_monopogen import import_monopogen

IDS = ['chr1:10:A:G', 'chr1:20:A:G', 'chr2:30:C:T', 'chr2:40:G:A']
CELLS = ['Ref', 'cell-2', 'cell_3', 'cell4']
COUNTS = [['0/3', '0/3', '2/0', '0/0'], ['1/2', '1/2', '0/3', '3/0'],
          ['3/0', '3/0', '0/4', '0/2'], ['0/0', '0/0', '2/0', '0/0']]


def tables(quality=False):
    vh = ['variant_id', 'chrom', 'pos', 'ref', 'alt']
    vr = [[v, *v.split(':')] for v in IDS]
    if quality:
        vh += ['Depth_total', 'Depth_ref', 'Depth_alt', 'SVM_pos_score', 'LDrefine_merged_score', 'BAF_alt']
        vr = [row + ['20', '10', '10', '.9', '.9', '.4'] for row in vr]
    return ((['cell_id', *IDS], [[c, *counts] for c,counts in zip(CELLS, COUNTS)]),
            (vh, vr), (['cell_id'], [[c] for c in CELLS]))


def monopogen_fixture(root):
    root.mkdir()
    matrix, variants, cells = tables(True)
    for chrom, indices in [('chr1', [0, 1]), ('chr2', [2, 3])]:
        # Deliberately reverse chromosome-2 cell order to test name-based alignment.
        order = list(range(4)) if chrom == 'chr1' else [3, 2, 1, 0]
        write_table(root / f'{chrom}.cell_snv.cellID.csv', ['cell', 'id', 'index'],
                    [[CELLS[i], i+10, j+1] for j,i in enumerate(order)], ',')
        write_table(root / f'{chrom}.cell_snv.cellID.filter.csv', ['cell'], [[c] for c in CELLS], ',')
        vh = ['chr', 'pos', 'Ref_allele', 'Alt_allele', *variants[0][5:], 'extra_annotation']
        write_table(root / f'{chrom}.putativeSNVs.csv', vh,
                    [[*variants[1][i][1:], 'kept'] for i in indices], ',')
        export = root / f'{chrom}.tsv'
        write_table(export, ['Variant_ID', *[CELLS[i] for i in order]],
                    [[IDS[j], *[COUNTS[i][j] for i in order]] for j in indices])
        subprocess.run(['Rscript', str(SPICE.SCRIPTS_DIR / 'matrix_bridge.R'), 'import',
                        str(export), str(root / f'{chrom}.SNV_mat.RDS')], check=True, capture_output=True)


class SchemaTests(unittest.TestCase):
    def test_valid_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_bundle(tmp, *tables())
            self.assertEqual(load_bundle(tmp), tables())
            with self.assertRaises(FileExistsError):
                write_bundle(tmp, *tables())

    def test_bad_counts_ids_and_metadata(self):
        for value in ('-1/0', '1.5/0', 'NA', '', '0/1/2', '2147483647/1', './.'):
            t = copy.deepcopy(tables()); t[0][1][0][1] = value
            with self.subTest(value=value), self.assertRaises(ValueError): validate(*t)
        for mutate in (
            lambda t: t[0][0].__setitem__(2, IDS[0]),
            lambda t: t[0][1][1].__setitem__(0, CELLS[0]),
            lambda t: t[0][1][0].__setitem__(0, 'cell with spaces'),
            lambda t: t[1][1][0].__setitem__(2, '11'),
            lambda t: t[1][0].append('Depth_ref'),
        ):
            t = copy.deepcopy(tables()); mutate(t)
            with self.assertRaises(ValueError): validate(*t)

    def test_duplicate_header_ragged_and_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.tsv'
            for text in ('cell_id\tv\tv\na\t0/1\t0/1\n', 'cell_id\tv\na\n', 'cell_id\tv\n'):
                p.write_text(text)
                with self.assertRaises(ValueError): read_table(p)

    def test_removed_flag_and_parser_defaults(self):
        p = SPICE.build_parser()
        with self.assertRaises(SystemExit): p.parse_args(['phylogeny', 'a', 'b', 'c', '--include_failed_chisq', 'true'])
        a = p.parse_args(['filter', 'a', 'b', 'c', '--input_format', 'standard'])
        self.assertEqual((a.min_alt_cells_per_snv, a.min_snvs_per_cell, a.variant_qc), (5, 5, 'auto'))


@unittest.skipUnless(shutil.which('Rscript'), 'Rscript required for Monopogen RDS tests')
class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='SPICE routes ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'monopogen'
        monopogen_fixture(self.source)
        self.bundle = self.root / 'bundle'
        import_monopogen(self.source, self.bundle)
        self.parser = SPICE.build_parser()

    def args(self, source, out, *extra):
        return self.parser.parse_args(['filter', str(source), str(self.root / out), 'sample',
                                      '--min_alt_cells_per_snv', '2', '--min_snvs_per_cell', '1', *extra])

    def test_import_retains_sites_counts_metadata_and_alignment(self):
        t = load_bundle(self.bundle)
        self.assertEqual(t[0], tables()[0])
        self.assertIn('extra_annotation', t[1][0])
        self.assertIn('chr2.index', t[2][0])
        self.assertEqual(len(t[0][0])-1, 4)  # Two distinct sites share a pattern.

    def test_routes_and_legacy_filter_equivalent(self):
        SPICE.run_filter(self.args(self.source, 'convenience', '--threads', '2'))
        SPICE.run_filter(self.args(self.source, 'convenience', '--threads', '2'))  # Safe identical-input rerun.
        SPICE.run_filter(self.args(self.bundle, 'direct', '--input_format', 'standard'))
        for suffix in ('.SNV_mat.filter.csv', '.SNV_mat.filter.fasta'):
            self.assertEqual((self.root/'convenience'/('sample'+suffix)).read_bytes(),
                             (self.root/'direct'/('sample'+suffix)).read_bytes())
        h, rows = read_table(self.root/'direct'/'sample.SNV_mat.filter.csv', ',')
        self.assertEqual([r[0] for r in rows], IDS[:3])
        self.assertEqual(h, ['Variant_ID', *CELLS[:3]])
        fasta = (self.root/'direct'/'sample.SNV_mat.filter.fasta').read_text()
        self.assertIn('>Ref\nGGC', fasta)
        self.assertIn('>cell-2\nRRT', fasta)
        # Independent old R merge + count-filter route, using the legacy QC tables.
        legacy = self.root/'legacy'; legacy.mkdir()
        for name in ('sample.cellID.filter.csv', 'sample.SNVs.filter.csv'):
            shutil.copyfile(self.root/'direct'/name, legacy/name)
        subprocess.run(['Rscript', str(SPICE.SCRIPTS_DIR/'monopogen_merge.R'), str(self.source), str(legacy), 'sample'], check=True, capture_output=True)
        subprocess.run(['Rscript', str(SPICE.SCRIPTS_DIR/'mutation_filter.R'), str(legacy)+os.sep, 'sample',
                        str(self.root/'direct'/'sample.selected_cells.tsv'), '2', '1', '1'], check=True, capture_output=True)
        self.assertEqual((legacy/'sample.SNV_mat.filter.csv').read_bytes(), (self.root/'direct'/'sample.SNV_mat.filter.csv').read_bytes())

    def test_no_quality_metadata_and_empty_selection(self):
        generic = self.root/'generic'; write_bundle(generic, *tables())
        SPICE.run_filter(self.args(generic, 'generic-out', '--input_format', 'standard'))
        with self.assertRaises(ValueError):
            SPICE.run_filter(self.args(generic, 'bad', '--input_format', 'standard', '--variant_qc', 'metadata'))
        with self.assertRaises(ValueError):
            SPICE.run_filter(self.args(generic, 'bad', '--input_format', 'standard', '--depth_alt', '9'))
        with self.assertRaises(ValueError):
            SPICE.run_filter(self.args(generic, 'bad', '--input_format', 'standard', '--min_alt_cells_per_snv', '99'))

    def test_quality_eligibility_and_barcode_selection(self):
        t = copy.deepcopy(tables(True))
        t[1][1][1][t[1][0].index('SVM_pos_score')] = '0'
        t = (t[0], t[1], (['cell_id', 'pass_filter'], [[c, 'false' if c == 'cell4' else 'true'] for c in CELLS]))
        bundle = self.root/'quality'; write_bundle(bundle, *t)
        selected = self.root/'selected.tsv'
        write_table(selected, ['cell_barcodes'], [['cell_3'], ['Ref'], ['cell-2'], ['cell4']])
        a = self.args(bundle, 'quality-out', '--input_format', 'standard')
        a.cell_barcode = str(selected)
        SPICE.run_filter(a)
        h, rows = read_table(self.root/'quality-out'/'sample.SNV_mat.filter.csv', ',')
        self.assertEqual(h, ['Variant_ID', 'cell_3', 'Ref', 'cell-2'])
        self.assertEqual([r[0] for r in rows], [IDS[0], IDS[2]])
        write_table(selected, ['cell_barcodes'], [['unknown']])
        with self.assertRaises(ValueError): SPICE.run_filter(a)
        write_table(selected, ['cell_barcodes'], [['Ref'], ['Ref']])
        with self.assertRaises(ValueError): SPICE.run_filter(a)

    def test_import_cli_dispatch_and_missing_companion(self):
        a = self.parser.parse_args(['import-monopogen', str(self.source), str(self.root), 'cli-bundle'])
        a.func(a)
        self.assertEqual(load_bundle(self.root/'cli-bundle'), load_bundle(self.bundle))
        (self.source/'chr2.cell_snv.cellID.filter.csv').unlink()
        with self.assertRaises(FileNotFoundError): import_monopogen(self.source, self.root/'missing')

    def test_duplicate_variant_consistent_and_conflicting(self):
        tsv = self.source/'chr1.tsv'
        h, rows = read_table(tsv); rows.append(rows[0][:])
        def rebuild():
            write_table(tsv,h,rows)
            subprocess.run(['Rscript', str(SPICE.SCRIPTS_DIR/'matrix_bridge.R'), 'import', str(tsv),
                            str(self.source/'chr1.SNV_mat.RDS')], check=True, capture_output=True)
        rebuild(); import_monopogen(self.source, self.root/'dedup')
        self.assertEqual(len(load_bundle(self.root/'dedup')[0][0])-1, 4)
        rows[-1][1] = '9/9'; rebuild()
        with self.assertRaises(ValueError): import_monopogen(self.source, self.root/'conflict')

    def test_pipeline_passes_alignment_threads_root_and_cut(self):
        # Real conversion/filtering; only external tree computation is replaced.
        real_run = subprocess.run
        calls = []
        def dispatch(cmd, **kwargs):
            if cmd[0] == '/fixture/iqtree' or str(cmd[1]).endswith('BranchSupportCut.R'):
                calls.append(cmd)
                return subprocess.CompletedProcess(cmd, 0)
            return real_run(cmd, **kwargs)
        for mode, source in [('standard', self.bundle), ('monopogen', self.source)]:
            args = self.parser.parse_args(['phylogeny', str(source), str(self.root/mode), 'sample',
                '--input_format', mode, '--min_alt_cells_per_snv', '2', '--min_snvs_per_cell', '1',
                '--threads', '2', '--clone_cut_mode', 'manual', '--clone_cut_threshold', '.02', '--outgroup', 'Ref'])
            with patch('scripts.IQTREE2.os.path.isfile', return_value=True), patch('scripts.IQTREE2.os.access', return_value=True), patch.dict(os.environ, {'IQTREE2_BIN':'/fixture/iqtree'}), patch.object(SPICE.subprocess, 'run', side_effect=dispatch):
                SPICE.run_phylogeny(args)
        self.assertEqual((self.root/'standard'/'sample.fasta').read_bytes(), (self.root/'monopogen'/'sample.fasta').read_bytes())
        self.assertEqual(calls[0][calls[0].index('-T')+1], '2')
        self.assertEqual(calls[1][4:6], ['90', '75'])  # UFBoot then SH thresholds to R.
        self.assertEqual(calls[1][10:14], ['outgroup', 'Ref', 'manual', '0.02'])

if __name__ == '__main__': unittest.main()
