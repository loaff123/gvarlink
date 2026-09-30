"""Candidate API driver in fresh processes; expected results live in a separate oracle."""
from fractions import Fraction
import json
from pathlib import Path
import sys

import gvar as gv
import numpy as np
import gvarlink as gl

HERE = Path(__file__).resolve().parent


def write_branch(name, path):
    model = json.loads((HERE / 'fixtures' / 'branch_model.json').read_text())
    branch = model['branches'][name]
    sources = {name:gl.Source.create(**source) for name,source in model['sources'].items()}
    ctx = gl.Context([sources[key] for key in branch['source_order']])
    primary = {key:np.asarray(ctx.primary(sources[key]),dtype=object).reshape(-1) for key in branch['source_order']}
    values = []
    for mean,factors in zip(branch['means'],branch['factors']):
        value = float(Fraction(mean))
        for key,weights in factors.items():
            for variable,weight in zip(primary[key],weights):
                value += float(Fraction(weight))*variable
        values.append(value)
    artifact = ctx.pack(np.array(values,dtype=object),unit='count',interpretation='affine')
    gl.write(artifact,path)
    print(json.dumps({'branch':name,'path':str(path),'bytes':Path(path).stat().st_size}))


def summarize(a,b):
    a=np.asarray(a,dtype=object).reshape(-1);b=np.asarray(b,dtype=object).reshape(-1)
    joint=np.concatenate([a,b]);difference=a-b
    matrix=np.asarray(gv.evalcov(joint))
    return {'a_means':np.asarray(gv.mean(a)).tolist(),'b_means':np.asarray(gv.mean(b)).tolist(),
            'a_covariance':matrix[:len(a),:len(a)].tolist(),'b_covariance':matrix[len(a):,len(a):].tolist(),
            'cross_covariance':matrix[:len(a),len(a):].tolist(),'joint_covariance':matrix.tolist(),
            'contrast_means':np.asarray(gv.mean(difference)).tolist(),'contrast_covariance':np.asarray(gv.evalcov(difference)).tolist(),
            'total_contrast_variance':float(gv.var(sum(difference)))}


def merge(a_path,b_path):
    context, arrays = gl.load_many([a_path,b_path])
    a,b=arrays
    merged = summarize(a,b)
    # Trusted, self-generated native JSON joint serialization is a baseline only.
    native = gv.gloads(gv.gdumps(np.concatenate([np.ravel(a),np.ravel(b)]),method='json'))
    ca,one=gl.load_many([a_path]);cb,two=gl.load_many([b_path])
    separate=summarize(one[0],two[0])
    print(json.dumps({'merged':merged,'native_joint':summarize(native[:3],native[3:]),'separate_context_cross_covariance':separate['cross_covariance'],
                      'versions':{'python':sys.version,'numpy':np.__version__,'gvar':gv.__version__,'gvarlink':gl.__version__}},allow_nan=False,sort_keys=True))


if __name__ == '__main__':
    if sys.argv[1]=='write':
        write_branch(sys.argv[2],Path(sys.argv[3]))
    elif sys.argv[1]=='merge':
        merge(Path(sys.argv[2]),Path(sys.argv[3]))
    else:
        raise SystemExit('unknown operation')
