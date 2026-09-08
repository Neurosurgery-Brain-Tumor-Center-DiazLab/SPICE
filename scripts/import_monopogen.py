"""Optional Monopogen adapter. R is used only to decode upstream RDS matrices."""
from pathlib import Path
import subprocess
import tempfile
import re
from .standard_input import read_table, unique_index, write_bundle, QUALITY


def import_monopogen(directory, output):
    directory = Path(directory)
    def chromosome_order(path):
        parts = re.split(r'(\d+)', path.name)
        return tuple((0, int(p)) if p.isdigit() else (1, p) for p in parts)
    files = sorted(directory.glob('chr*.SNV_mat.RDS'), key=chromosome_order)
    if not files:
        raise ValueError('no chr*.SNV_mat.RDS matrices found')
    cell_order = None
    cell_meta = {}
    pass_cells = None
    variants = {}
    variant_columns = ['variant_id', 'chrom', 'pos', 'ref', 'alt', 'source_file']
    patterns = {}
    for path in files:
        chrom = path.name.removesuffix('.SNV_mat.RDS')
        ch, cr = read_table(directory / f'{chrom}.cell_snv.cellID.csv', ',')
        ci = unique_index(ch, cr, 'cell')
        fh, fr = read_table(directory / f'{chrom}.cell_snv.cellID.filter.csv', ',')
        fi = unique_index(fh, fr, 'cell')
        if not set(fi).issubset(ci):
            raise ValueError(f'{chrom}: filtered cell IDs absent from cell metadata')
        pass_cells = set(fi) if pass_cells is None else pass_cells.intersection(fi)
        if cell_order is None:
            cell_order = list(ci)
            cell_meta = {c: {'cell_id': c} for c in ci}
        elif set(ci) != set(cell_order):
            raise ValueError(f'{chrom}: inconsistent chromosome cell sets')
        for c in ci:
            for key, value in ci[c].items():
                if key != 'cell':
                    cell_meta[c][f'{chrom}.{key}'] = value
            for key, value in fi.get(c, {}).items():
                if key != 'cell':
                    cell_meta[c][f'{chrom}.filter.{key}'] = value
        vh, vr = read_table(directory / f'{chrom}.putativeSNVs.csv', ',')
        if not set(('chr','pos','Ref_allele','Alt_allele', *QUALITY)).issubset(vh):
            raise ValueError(f'{chrom}: missing putative SNV metadata columns')
        raw_variants = {}
        for row in vr:
            item = dict(zip(vh, row))
            vid = ':'.join(item[k] for k in ('chr','pos','Ref_allele','Alt_allele'))
            if vid in raw_variants and raw_variants[vid] != item:
                raise ValueError(f'conflicting metadata for duplicate variant: {vid}')
            raw_variants[vid] = item
        with tempfile.TemporaryDirectory() as tmp:
            exported = Path(tmp) / 'matrix.tsv'
            subprocess.run(['Rscript', str(Path(__file__).with_name('matrix_bridge.R')), 'export', str(path), str(exported)], check=True)
            mh, mr = read_table(exported)
        if set(mh[1:]) != set(cell_order):
            raise ValueError(f'{chrom}: RDS and cell metadata IDs disagree')
        cell_index = {c: i for i, c in enumerate(mh)}
        order = [cell_index[c] for c in cell_order]
        for row in mr:
            vid = row[0]
            if vid not in raw_variants:
                raise ValueError(f'{chrom}: matrix variant lacks putative metadata: {vid}')
            pattern = [row[i] for i in order]
            raw = raw_variants[vid]
            item = {'variant_id': vid, 'chrom': raw['chr'], 'pos': raw['pos'],
                    'ref': raw['Ref_allele'], 'alt': raw['Alt_allele'], 'source_file': path.name, **raw}
            if vid in patterns:
                if patterns[vid] != pattern or any(variants[vid].get(k) != v for k,v in item.items() if k != 'source_file'):
                    raise ValueError(f'conflicting duplicate variant: {vid}')
                continue
            patterns[vid] = pattern
            variants[vid] = item
            variant_columns.extend(k for k in item if k not in variant_columns)
    # Variants absent from the RDS are not observed sites and cannot enter an alignment.
    cell_columns = ['cell_id', 'pass_filter']
    for c in cell_order:
        cell_meta[c]['pass_filter'] = 'true' if c in pass_cells else 'false'
        cell_columns.extend(k for k in cell_meta[c] if k not in cell_columns)
    write_bundle(output,
                 (['cell_id', *patterns], [[c, *[p[i] for p in patterns.values()]] for i,c in enumerate(cell_order)]),
                 (variant_columns, [[v.get(k, '') for k in variant_columns] for v in variants.values()]),
                 (cell_columns, [[cell_meta[c].get(k, '') for k in cell_columns] for c in cell_order]))
