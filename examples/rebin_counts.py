"""Conservative integrated-counts example, not a package-level rebin engine.

Each count is integrated over an old bin. Excluded bins are missing support,
not measured zero. Partial coverage is returned without renormalization.
"""
import json
from pathlib import Path
import sys
import gvar as gv
import numpy as np
from gvarlink import Source,Context,write,load_many


def run(destination):
    root=Path(destination);root.mkdir(exist_ok=False)
    counts=Source.create('counts',(4,),'independent old bins ordered by increasing edge')
    dark=Source.create('dark',(4,),'shared dark old bins ordered by increasing edge')
    context=Context([counts,dark])
    values=np.array([10,20,30,40])+np.array([1,2,3,4])*context.primary(counts)-(1+0.5*context.primary(dark))
    old=[0,1,3,4,6];new=[0,0.5,1,3,6];valid=[True,False,True,True]
    outputs=[];coverage=[]
    for lo,hi in zip(new[:-1],new[1:]):
        value=0.;covered=0.
        for i,(left,right) in enumerate(zip(old[:-1],old[1:])):
            overlap=max(0.,min(hi,right)-max(lo,left)) if valid[i] else 0.
            value+=values[i]*overlap/(right-left)
            covered+=overlap
        outputs.append(value);coverage.append(covered/(hi-lo))
    # The first measured bin is split: the two halves remain correlated.
    before=sum(value for value,good in zip(values,valid) if good)
    path=root/'rebinned.gvl';write(context.pack(outputs,unit='counts',interpretation='affine'),path)
    _,(restored,)=load_many([path]);after=sum(restored)
    report=dict(input_integral=float(gv.mean(before)),output_integral=float(gv.mean(after)),
                integral_variance_before=float(gv.var(before)),integral_variance_after=float(gv.var(after)),
                coverage=coverage,zero_coverage_is_missing_support=True,
                semantics='integrated counts; deterministic mask; uncovered support excluded, never renormalized',
                covariance_of_split_halves=float(gv.cov(restored[0],restored[1])))
    (root/'coverage.json').write_text(json.dumps({'old_edges':old,'new_edges':new,'coverage':coverage,'valid':valid}),encoding='utf8')
    return report


if __name__=='__main__':print(json.dumps(run(sys.argv[1]),sort_keys=True))
