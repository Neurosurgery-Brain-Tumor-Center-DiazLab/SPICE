"""Validated SPICE v1 interchange: cell × variant REF/ALT count TSV + metadata.

No caller-specific dependency belongs in this module. Variant order is site order.
"""
import csv
import math
import re
from pathlib import Path

QUALITY = ('Depth_total', 'Depth_ref', 'Depth_alt', 'SVM_pos_score',
           'LDrefine_merged_score', 'BAF_alt')
VARIANT = re.compile(r'[^:\s]+:[1-9][0-9]*:[ACGT]:[ACGT]\Z')
COUNT = re.compile(r'(0|[1-9][0-9]*)/(0|[1-9][0-9]*)\Z')
CELL = re.compile(r'[A-Za-z0-9_.-]+\Z')


def read_table(path, delimiter='\t'):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        rows = list(csv.reader(handle, delimiter=delimiter))
    if len(rows) < 2 or not rows[0] or any(not x for x in rows[0]):
        raise ValueError(f'{path}: a header and at least one data row are required')
    if len(set(rows[0])) != len(rows[0]):
        raise ValueError(f'{path}: duplicate column names')
    if any(len(row) != len(rows[0]) for row in rows[1:]):
        raise ValueError(f'{path}: ragged/blank rows')
    return rows[0], rows[1:]


def write_table(path, header, rows, delimiter='\t'):
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle, delimiter=delimiter, lineterminator='\n')
        writer.writerow(header)
        writer.writerows(rows)


def unique_index(header, rows, key):
    if key not in header:
        raise ValueError(f'metadata requires {key}')
    index = header.index(key)
    result = {}
    for row in rows:
        if not row[index] or row[index] in result:
            raise ValueError(f'empty or duplicate {key}: {row[index]}')
        result[row[index]] = dict(zip(header, row))
    return result


def validate(matrix, variants, cells):
    header, rows = matrix
    if header[0] != 'cell_id' or len(header) < 2:
        raise ValueError('matrix.tsv: first column must be cell_id, followed by variant IDs')
    ids = header[1:]
    for vid in ids:
        if not VARIANT.fullmatch(vid) or vid.split(':')[2] == vid.split(':')[3]:
            raise ValueError(f'invalid biallelic SNV ID: {vid}; expected chrom:pos:REF:ALT')
    cell_ids = [row[0] for row in rows]
    if len(set(cell_ids)) != len(cell_ids) or any(not CELL.fullmatch(c) or c == 'Variant_ID' for c in cell_ids):
        raise ValueError('cell IDs must be unique, cannot be Variant_ID, and use only letters, digits, _, . or -')
    for row in rows:
        for vid, value in zip(ids, row[1:]):
            if not COUNT.fullmatch(value) or any(int(n) > 2147483647 for n in value.split('/')) or sum(map(int, value.split('/'))) > 2147483647:
                raise ValueError(f'invalid REF/ALT counts for {row[0]}, {vid}: {value}')
    vh, vr = variants
    required = {'variant_id', 'chrom', 'pos', 'ref', 'alt'}
    if not required.issubset(vh):
        raise ValueError('variants.tsv requires variant_id, chrom, pos, ref, alt')
    vm = unique_index(vh, vr, 'variant_id')
    cm = unique_index(*cells, 'cell_id')
    if set(vm) != set(ids) or set(cm) != set(cell_ids):
        raise ValueError('matrix and metadata IDs must match exactly')
    for vid, row in vm.items():
        if ':'.join(row[k] for k in ('chrom', 'pos', 'ref', 'alt')) != vid:
            raise ValueError(f'variant metadata disagrees with ID: {vid}')
    for row in cm.values():
        if row.get('pass_filter', 'true') not in ('true', 'false'):
            raise ValueError('cells.tsv pass_filter must be true or false')
    present = set(QUALITY).intersection(vh)
    if present and present != set(QUALITY):
        raise ValueError('quality metadata must contain all six QC fields or none')
    for row in vm.values():
        for field in present:
            value = row[field]
            if value in ('NA', ''):  # Legacy Monopogen missing-quality behavior.
                continue
            try:
                valid = math.isfinite(float(value))
            except ValueError:
                valid = False
            if not valid:
                raise ValueError(f'invalid quality metadata: {field}={value}')
    return vm, cm


def load_bundle(directory):
    directory = Path(directory)
    tables = tuple(read_table(directory / name) for name in ('matrix.tsv', 'variants.tsv', 'cells.tsv'))
    validate(*tables)
    return tables


def write_bundle(directory, matrix, variants, cells):
    validate(matrix, variants, cells)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, table in zip(('matrix.tsv', 'variants.tsv', 'cells.tsv'), (matrix, variants, cells)):
        if (directory / name).exists():
            raise FileExistsError(f'refusing to overwrite standard input: {directory / name}')
    for name, table in zip(('matrix.tsv', 'variants.tsv', 'cells.tsv'), (matrix, variants, cells)):
        write_table(directory / name, *table)


def select_quality(tables, args):
    matrix, variants, cells = tables
    vm, cm = validate(*tables)
    use_quality = args.variant_qc == 'metadata' or (args.variant_qc == 'auto' and set(QUALITY).issubset(variants[0]))
    if use_quality and not set(QUALITY).issubset(variants[0]):
        raise ValueError('--variant_qc metadata requires all six QC fields in variants.tsv')
    if not use_quality and any(getattr(args, k) != v for k, v in
                              [('depth_ref', 5), ('depth_alt', 5), ('svm_pos_score', .1),
                               ('ldrefine_merged_score', .25), ('baf_alt', .5)]):
        raise ValueError('quality thresholds were changed but quality filtering is disabled or metadata is absent')
    for name in ('depth_ref', 'depth_alt', 'min_alt_cells_per_snv', 'min_snvs_per_cell', 'threads'):
        if getattr(args, name) < (1 if name == 'threads' else 0):
            raise ValueError(f'{name} is out of range')
    for name in ('svm_pos_score', 'ldrefine_merged_score', 'baf_alt'):
        if not math.isfinite(getattr(args, name)) or not 0 <= getattr(args, name) <= 1:
            raise ValueError(f'{name} must be finite and between 0 and 1')
    ids = []
    for vid in matrix[0][1:]:
        q = {k: float(vm[vid][k]) if vm[vid][k] not in ('NA', '') else 0 for k in QUALITY} if use_quality else {}
        if not use_quality or (q['Depth_total'] >= args.depth_ref + args.depth_alt and
                               q['Depth_ref'] >= args.depth_ref and q['Depth_alt'] >= args.depth_alt and
                               q['SVM_pos_score'] >= args.svm_pos_score and
                               q['LDrefine_merged_score'] >= args.ldrefine_merged_score and q['BAF_alt'] <= args.baf_alt):
            ids.append(vid)
    eligible = [r for r in matrix[1] if cm[r[0]].get('pass_filter', 'true') == 'true']
    print(f'[SPICE:filter] Variant metadata QC: {"applied" if use_quality else "disabled (count filtering still applies)"}')
    return ids, eligible, vm, cm
