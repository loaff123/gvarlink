"""Original tiny workflow, including two writer processes and a fresh reader."""
import json
import os
from pathlib import Path
import subprocess
import sys
import gvar as gv
from .adapter import Context, load_many
from .format import read, write
from .model import Artifact, Source, canonical


def _worker(directory,action):
    root=Path(directory)
    registry=read(root/'registry.gvl').sources
    if action in ('1','2'):
        shared,first,second=registry
        exposure=first if action=='1' else second
        # Deliberately reverse whole-block order in the second writer.
        sources=[shared,exposure] if action=='1' else [exposure,shared]
        context=Context(sources)
        shared_value=context.primary(shared)[0]
        independent=context.primary(exposure)[0]
        values=[10+2*shared_value,20+2*independent]
        write(context.pack(values,unit='counts',interpretation='affine'),root/f'branch-{action}.gvl')
        return {'pid':os.getpid()}
    _,arrays=load_many([root/'branch-1.gvl',root/'branch-2.gvl'])
    a,b=arrays
    return dict(pid=os.getpid(),shared_contrast_variance=float(gv.var(a[0]-b[0])),
                independent_equal_contrast_variance=float(gv.var(a[1]-b[1])),
                shared_cross_covariance=float(gv.cov(a[0],b[0])),
                interpretation='affine',scope='original synthetic example; declarations are not authentication')


def run_demo(directory):
    root=Path(directory);root.mkdir(parents=False,exist_ok=False)
    sources=[Source.create('background',(1,),'one standardized demo shared measurement'),
             Source.create('exposure',(1,),'one standardized independently acquired demo value'),
             Source.create('exposure',(1,),'one standardized independently acquired demo value')]
    write(Artifact.from_arrays([], [0], [], [], sources),root/'registry.gvl')
    pids=[];result={}
    for action in ('1','2','merge'):
        process=subprocess.run([sys.executable,'-m','gvarlink.demo',str(root),action],
                               capture_output=True,text=True,check=True,timeout=30)
        result=json.loads(process.stdout);pids.append(result.pop('pid'))
    result['worker_pids']=pids
    (root/'summary.json').write_bytes(canonical(result)+b'\n')
    return result


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[2] not in ('1','2','merge'):
        raise SystemExit('internal demo worker expects DIRECTORY and 1|2|merge')
    print(json.dumps(_worker(sys.argv[1],sys.argv[2]),sort_keys=True))
