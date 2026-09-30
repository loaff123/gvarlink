import uuid
import numpy as np
import pytest
import gvarlink as gl


def source(n=2, **kw):
    return gl.Source.create('background', (n,), 'detector-index', **kw)


def artifact(s=None, **kw):
    return gl.Artifact.from_arrays([2.,3.], [0,2,3], [0,1,1], [1.,-2.,3.], [s or source()], **kw)


def test_identity_is_not_label_or_numeric_equality():
    a,b=source(),source()
    assert a.uuid!=b.uuid and a.basis_hash==b.basis_hash
    assert gl.Source.from_dict(a.to_dict())==a
    assert str(uuid.UUID(a.uuid))==a.uuid


def test_basis_hash_checked_and_fields_closed():
    s=source(); d=s.to_dict(); d['description']='different'
    with pytest.raises(gl.FormatError):gl.Source.from_dict(d)
    d=s.to_dict();d['remote_url']='https://example.com'
    with pytest.raises(gl.FormatError):gl.Source.from_dict(d)


@pytest.mark.parametrize('shape', [(True,),(-1,),(0,),(2**63,), (1,)*9])
def test_source_bad_shapes(shape):
    with pytest.raises((gl.FormatError,gl.LimitError)):gl.Source.create('x',shape,'x')


def test_copy_immutable_and_shape():
    a=artifact(); assert a.shape==(2,) and a.coordinates==2 and a.nnz==3
    with pytest.raises(ValueError):a.mean[0]=99
    with pytest.raises(ValueError):a.mean.setflags(write=True)
    original=np.array([1.]); x=gl.Artifact.from_arrays(original,[0,0],[],[],[],shape=())
    original[0]=99; assert x.mean[0]==1 and x.shape==()


@pytest.mark.parametrize('change', [dict(indptr=[1,2,3]),dict(indptr=[0,3,2]),dict(indices=[0,0,1]),dict(indices=[0,2,1]),dict(data=[1,0,3]),dict(data=[1,np.nan,3]),dict(mean=[np.inf,3]),dict(indptr=[False,2,3]),dict(indices=[0.,1.,1.])])
def test_invalid_csr_rejected(change):
    kwargs=dict(mean=[2,3],indptr=[0,2,3],indices=[0,1,1],data=[1,-2,3],sources=[source()]);kwargs.update(change)
    with pytest.raises(gl.FormatError):gl.Artifact.from_arrays(**kwargs)


def test_duplicate_sources_and_resource_limits():
    s=source()
    with pytest.raises(gl.FormatError):gl.Artifact.from_arrays([0],[0,0],[],[],[s,s])
    with pytest.raises(gl.LimitError):artifact(limits=gl.Limits(max_rows=1))
    with pytest.raises(gl.LimitError):gl.Limits(max_rows=100001)
    with pytest.raises(gl.FormatError):gl.Limits(max_rows=True)


def test_empty_constant_and_metadata_contract():
    a=gl.Artifact.from_arrays([], [0], [], [], [], shape=(0,2)); assert a.rows==0
    b=gl.Artifact.from_arrays([1], [0,0], [], [], [], interpretation='affine', unit='counts')
    assert b.interpretation=='affine'
    with pytest.raises(gl.FormatError):artifact(interpretation='exact-nonlinear')
    with pytest.raises(gl.FormatError):artifact(unit='x'*1025)
