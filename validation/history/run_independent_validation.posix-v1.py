"""Bounded fresh-process candidate integration and independent Fraction comparison."""
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

from fraction_oracle import covariance, evaluate_fixture
from reference_reader import read, reconcile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def limit_process():
    resource.setrlimit(resource.RLIMIT_AS,(512<<20,512<<20))
    resource.setrlimit(resource.RLIMIT_CPU,(20,20))


def run(args, output):
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    command=[sys.executable,str(HERE/'fixture_worker.py')]+[str(x) for x in args]
    start=time.monotonic()
    result=subprocess.run(command,capture_output=True,text=True,env=env,timeout=30,preexec_fn=limit_process)
    record={'command':command,'returncode':result.returncode,'wall_seconds':time.monotonic()-start,
            'stdout':result.stdout,'stderr':result.stderr,'requested_address_space_bytes':512<<20,'requested_cpu_seconds':20,'wall_timeout_seconds':30}
    output.write_text(json.dumps(record,indent=2)+'\n')
    if result.returncode:
        raise RuntimeError('fresh process failed: '+str(output))
    return json.loads(result.stdout)


def flatten(value):
    if isinstance(value,list):
        return [number for child in value for number in flatten(child)]
    return [float(value)]


def compare(actual,expected):
    results={}
    for category,ref in expected.items():
        a=flatten(actual[category]);e=flatten(ref)
        assert len(a)==len(e),(category,'wrong size')
        scale=max([1.]+[abs(x) for x in e])
        errors=[abs(x-y) for x,y in zip(a,e)]
        assert all(math.isfinite(x) for x in a),category
        assert max(errors,default=0)<=5e-12*scale,(category,'error exceeds tolerance')
        zero_error=max([error for error,value in zip(errors,e) if value==0],default=0)
        assert zero_error<=5e-12,(category,'zero error exceeds tolerance')
        results[category]={'maximum_absolute_error':max(errors,default=0),'reference_scale':scale,'maximum_expected_zero_error':zero_error}
    return results


def decoded_rows(document):
    coordinates=[]
    for source in document['header']['sources']:
        count=math.prod(source['shape'])
        coordinates.extend((source['uuid'],i) for i in range(count))
    rows=[]
    for start,end in zip(document['indptr'],document['indptr'][1:]):
        rows.append({coordinates[document['indices'][i]]:Fraction.from_float(document['data'][i]) for i in range(start,end)})
    return rows


def main():
    destination=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'results'/'integration'
    destination.mkdir(parents=True,exist_ok=True)
    a=destination/'a.gvl';b=destination/'b.gvl'
    run(['write','a',a],destination/'write-a.json')
    run(['write','b',b],destination/'write-b.json')
    decoded_a,decoded_b=read(a),read(b)
    assert len(reconcile([decoded_a,decoded_b]))==4
    assert decoded_a['header']['interpretation']==decoded_b['header']['interpretation']=='affine'
    assert decoded_a['header']['unit']==decoded_b['header']['unit']=='count'
    fixture=json.loads((HERE/'fixtures'/'branch_model.json').read_text())
    for name,doc in [('a',decoded_a),('b',decoded_b)]:
        expected_order=[fixture['sources'][x]['uuid'] for x in fixture['branches'][name]['source_order']]
        assert [s['uuid'] for s in doc['header']['sources']]==expected_order
        assert [Fraction.from_float(x) for x in doc['mean']]==list(map(Fraction,fixture['branches'][name]['means']))
        expected_rows=[]
        for row in fixture['branches'][name]['factors']:
            expected_rows.append({(fixture['sources'][key]['uuid'],i):Fraction(v) for key,values in row.items() for i,v in enumerate(values) if Fraction(v)})
        assert decoded_rows(doc)==expected_rows,(name,'wrong decoded CSR factor')
    expected=evaluate_fixture(HERE/'fixtures'/'branch_model.json')
    ar,br=decoded_rows(decoded_a),decoded_rows(decoded_b)
    assert covariance(ar,br)==expected['cross_covariance']
    result=run(['merge',a,b],destination/'merge.json')
    report={'merged':compare(result['merged'],expected),'native_joint':compare(result['native_joint'],expected),
            'independent_reader_factors_exact':True,'independent_fraction_cross_covariance_exact':True,
            'separate_processes':3,'versions':result['versions']}
    assert all(x==0 for x in flatten(result['separate_context_cross_covariance']))
    report['separate_contexts_do_not_correlate']=True
    report['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (a,b)}
    (destination/'validation.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))


if __name__=='__main__':
    main()
