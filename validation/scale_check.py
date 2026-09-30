"""Frozen original scale check, independent closed-form assertions."""
import json, os, pathlib, subprocess, sys, time
import numpy as np
import gvar as gv
from gvarlink import Source, Context, Artifact, read, write, load_many
ROOT=pathlib.Path(__file__).resolve().parents[1]
N=32768
SEL=np.array([0,1,2,3,4095,4096,4097,8191,8192,16383,16384,24575,24576,32765,32766,32767])

def worker(path,action):
    sources=read(path/'registry.gvl').sources
    start=time.monotonic()
    if action in ('0','1'):
        branch=int(action);private=sources[branch];dark,modes=sources[2:]
        context=Context([private,dark,modes] if branch==0 else [modes,dark,private])
        p=context.primary(private);d=context.primary(dark);m=context.primary(modes)
        values=np.empty(N,dtype=object)
        for row in range(N):
            prim=np.r_[p[2*row:2*row+2],d[row%4096:row%4096+1],m]
            coeff=np.r_[.125,-.25,-.5,[(-1)**(row+k+branch)/16 for k in range(8)]]
            values[row]=gv.gvar_function(prim,100+row/1024+branch,coeff)
        write(context.pack(values,interpretation='affine',unit='counts'),path/f'branch-{branch}.gvl')
        result={'action':action,'file_bytes':(path/f'branch-{branch}.gvl').stat().st_size}
    else:
        _,(a,b)=load_many([path/'branch-0.gvl',path/'branch-1.gvl'])
        for branch,value in enumerate((a,b)):
            assert np.max(np.abs(gv.mean(value)-(100+np.arange(N)/1024+branch)))<=5e-12
            assert np.max(np.abs(gv.var(value)-23/64))<=5e-12
        actual=gv.evalcov(np.r_[a[SEL],b[SEL]])
        expected=np.zeros((32,32))
        for i in range(32):
            bi,ri=divmod(i,16);rowi=int(SEL[ri])
            for j in range(32):
                bj,rj=divmod(j,16);rowj=int(SEL[rj])
                expected[i,j]=(5/64 if bi==bj and rowi==rowj else 0)+(1/4 if rowi%4096==rowj%4096 else 0)+((-1)**(rowi+rowj+bi+bj))/32
        error=float(np.max(np.abs(actual-expected)));assert error<=5e-12
        sums=[sum(a),sum(b)]
        branch_vars=[float(gv.var(x)) for x in sums]
        contrast=float(gv.var(sums[0]-sums[1]))
        assert max(abs(x-68096) for x in branch_vars)<=5e-10*68096
        assert abs(contrast-5120)<=5e-10*5120
        result=dict(action=action,rows_per_branch=N,source_union=135176,nnz_total=2*N*11,selected_covariance_max_error=error,branch_sum_variances=branch_vars,sum_contrast_variance=contrast)
    result['wall_seconds']=time.monotonic()-start
    try:
        import resource
        result['maxrss_platform_units']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:pass
    print(json.dumps(result,sort_keys=True))


def main(path):
    path.mkdir(exist_ok=False)
    sources=[Source.create('exposure',(2*N,),f'scale branch{i}') for i in range(2)]+[Source.create('dark',(4096,),'dark channel order'),Source.create('modes',(8,),'eight declared signed modes')]
    write(Artifact.from_arrays([], [0], [], [], sources),path/'registry.gvl')
    reports=[]
    for action in ('0','1','merge'):
        p=subprocess.run([sys.executable,__file__,str(path),action],capture_output=True,text=True,timeout=180)
        (path/f'{action}.stderr.txt').write_text(p.stderr)
        (path/f'{action}.stdout.txt').write_text(p.stdout)
        if p.returncode:raise RuntimeError(f'{action} failed: {p.stderr}')
        reports.append(json.loads(p.stdout))
    (path/'result.json').write_text(json.dumps(reports,indent=2)+'\n')
    print(json.dumps(reports,indent=2))

if __name__=='__main__':
    path=pathlib.Path(sys.argv[1]).resolve()
    if len(sys.argv)>2:worker(path,sys.argv[2])
    else:main(path)
