"""Summarize a predeclared family of clone tests with Benjamini–Hochberg FDR."""
import csv
import math
from pathlib import Path

def bh_adjust(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [1.0]*len(values)
    previous = 1.0
    for rank in range(len(values),0,-1):
        i = order[rank-1]
        previous = min(previous,values[i]*len(values)/rank)
        adjusted[i] = previous
    return adjusted

def run_summary(args):
    if not math.isfinite(args.alpha) or not 0<args.alpha<1:
        raise ValueError('--alpha must be finite and between 0 and 1')
    manifest = Path(args.manifest).expanduser().resolve()
    with manifest.open() as handle:
        reader=csv.DictReader(handle,delimiter='\t')
        if not {'clone_id','plasticity_test'}.issubset(reader.fieldnames or []):
            raise ValueError('Manifest requires clone_id and plasticity_test columns')
        entries=list(reader)
    if not entries:raise ValueError('Manifest is empty')
    rows=[]; identifiers=set(); paths=set(); alternatives=set(); pvalues=[]
    for entry in entries:
        clone = entry['clone_id'].strip()
        if not clone or clone in identifiers:raise ValueError('Clone IDs must be nonempty and unique')
        identifiers.add(clone)
        if not entry['plasticity_test'].strip():raise ValueError('Each clone requires a test-result path')
        path=(manifest.parent/entry['plasticity_test']).resolve()
        if path in paths:raise ValueError('Repeated test-result file in manifest')
        paths.add(path)
        row={'clone_id':clone,'test_file':str(path),'test_status':'missing','observed_plasticity':'NA','empirical_p':'NA','alternative':'NA','q_value':'NA','significant':False}
        if path.is_file():
            with path.open() as handle:records=list(csv.DictReader(handle,delimiter='\t'))
            if len(records)!=1:raise ValueError(f'Expected one test-summary row: {path}')
            test=records[0]
            if not {'test_status','observed_plasticity','empirical_p','alternative','n_permutations_requested','n_permutations_successful'}.issubset(test):
                raise ValueError(f'Missing required test-summary columns: {path}')
            row.update({k:test[k] for k in ('test_status','observed_plasticity','empirical_p','alternative')})
            alternatives.add(test['alternative'])
            if test['test_status']=='pass':
                try:
                    value=float(test['empirical_p']);obs=float(test['observed_plasticity'])
                    count=int(test['n_permutations_requested']);completed=int(test['n_permutations_successful'])
                except ValueError:raise ValueError(f'Invalid successful test: {path}') from None
                if not math.isfinite(value) or not 0<=value<=1 or not math.isfinite(obs) or count<1 or completed!=count:
                    raise ValueError(f'Invalid successful test: {path}')
                pvalues.append(value)
            else:
                row['empirical_p']='NA';pvalues.append(1.0)
        else:pvalues.append(1.0)
        rows.append(row)
    if len(alternatives)>1 or not alternatives.issubset({'greater','less','two-sided'}):
        raise ValueError('All supplied tests must use the same valid alternative')
    for row,q in zip(rows,bh_adjust(pvalues)):
        row['n_tests_planned']=len(rows)
        if row['test_status']=='pass':row['q_value']=q;row['significant']=q<=args.alpha
    output=Path(args.output).expanduser()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),delimiter='\t')
        writer.writeheader();writer.writerows(rows)
    print(f'Wrote {len(rows)} clone results to {output}')
