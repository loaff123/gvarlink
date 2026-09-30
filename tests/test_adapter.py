from dataclasses import replace
import gvar as gv
import numpy as np
import pytest
import gvarlink as gl
from test_model import source


def test_native_roundtrip_and_shared_identity(tmp_path):
    s=source();ctx=gl.Context([s]);z=ctx.primary(s)
    values=np.array([5+2*z[0]-z[1],3+z[1]],dtype=object)
    a=ctx.pack(values,unit='counts',interpretation='affine');p=tmp_path/'x';gl.write(a,p)
    restored_ctx,(x,y)=gl.load_many([p,p])
    np.testing.assert_allclose(gv.mean(x),[5,3]);np.testing.assert_allclose(gv.evalcov(x),[[5,-1],[-1,1]])
    np.testing.assert_allclose(gv.var(x-y),[0,0],atol=0)
    assert a.interpretation=='affine'


def test_independent_equal_and_reordering():
    a,b=source(1),source(1)
    ctx=gl.Context([a,b]);x=ctx.primary(a);y=ctx.primary(b)
    packed=ctx.pack([2*x[0],2*y[0]])
    other=gl.Context([b,a]);r=other.restore(packed)
    assert gv.var(r[0]-r[1])==8
    assert gv.cov(r[0],other.primary(a)[0])==2
    assert gv.cov(r[1],other.primary(b)[0])==2


def test_signed_loadings_and_context_separation():
    s=source(1);one=gl.Context([s]);two=gl.Context([s]);z=one.primary(s)[0]
    packed=one.pack([2*z,-3*z]);r=two.restore(packed)
    assert gv.cov(r[0],r[1])==-6
    assert gv.cov(z,r[0])==0


def test_conflict_and_limit_do_not_mutate_context():
    a,b=source(1),source(1);ctx=gl.Context([a],limits=gl.Limits(max_coordinates=1))
    before=ctx.sources;primary=ctx.primary(a)[0]
    incoming=gl.Artifact.from_arrays([0],[0,0],[],[],[b])
    with pytest.raises(gl.LimitError):ctx.restore(incoming)
    assert ctx.sources==before and gv.var(ctx.primary(a)[0]-primary)==0
    collision=replace(a,revision='2');other=gl.Context([collision]);bad=other.pack([other.primary(collision)[0]])
    with pytest.raises(gl.SourceConflictError):ctx.restore(bad)
    assert ctx.sources==before


def test_unknown_nonzero_dependencies_reject_cancelled_zero_allowed():
    ctx=gl.Context([]);outside=gv.gvar(0,1)
    with pytest.raises(gl.DependencyError):ctx.pack([outside])
    a=ctx.pack([outside-outside,42]);assert a.nnz==0 and a.interpretation=='linearized'
    r=ctx.restore(a);np.testing.assert_array_equal(gv.mean(r),[0,42])
    assert gv.var(r).tolist()==[0,0]


def test_scalar_empty_shape_and_nonfinite_rejected():
    ctx=gl.Context([])
    assert ctx.restore(ctx.pack(2.0)).shape==()
    assert ctx.restore(ctx.pack(np.empty((0,2),dtype=object))).shape==(0,2)
    with pytest.raises(gl.FormatError):ctx.pack([float('nan')])
    with pytest.raises(gl.FormatError):ctx.pack([True])


def test_aggregate_load_limits(tmp_path):
    s=source(1);c=gl.Context([s]);p=tmp_path/'x';gl.write(c.pack([c.primary(s)[0]]),p)
    with pytest.raises(gl.LimitError):gl.load_many([p,p],limits=gl.Limits(max_rows=1))
    with pytest.raises(gl.LimitError):gl.load_many([p,p],limits=gl.Limits(max_nnz=1))
    with pytest.raises(gl.LimitError):gl.load_many([p,p],limits=gl.Limits(max_file_bytes=p.stat().st_size+1))


def test_label_change_matches_definition():
    s=source(1);ctx=gl.Context([s]);same=replace(s,label='a different display label')
    other=gl.Context([same]);a=other.pack([other.primary(same)[0]])
    r=ctx.restore(a)
    assert gv.var(r[0]-ctx.primary(s)[0])==0


def test_foreign_factory_indices_cannot_alias_owned_sources():
    old=gv.gvar
    gv.switch_gvar()
    try:
        s=source(1);ctx=gl.Context([s]);foreign=gv.gvar_factory()(100,7)
        assert gv.disassemble([ctx.primary(s)[0]])[0][1].indices()[0]==gv.disassemble([foreign])[0][1].indices()[0]
        with pytest.raises(gl.DependencyError):ctx.pack([foreign])
        # Zero derivatives do not carry covariance-world identity.
        assert ctx.pack([foreign-foreign]).nnz==0
    finally:gv.restore_gvar()
    assert gv.gvar is old


def test_context_binds_factory_before_global_switch():
    a,b=source(1),source(1);ctx=gl.Context([a]);owned=ctx.primary(a)[0]
    gv.switch_gvar()
    try:
        artifact=gl.Artifact.from_arrays([0],[0,1],[0],[1],[b])
        restored=ctx.restore(artifact)[0]
        assert gv.var(owned+restored)==2
        assert gv.var(ctx.restore(ctx.pack([owned+restored]))[0])==2
    finally:gv.restore_gvar()


def test_aggregate_admission_precedes_numeric_decoding(tmp_path,monkeypatch):
    s=source(1);c=gl.Context([s]);p=tmp_path/'x';gl.write(c.pack([c.primary(s)[0]]),p)
    calls=[];original=np.frombuffer
    def observe(*args,**kwargs):
        calls.append(1);return original(*args,**kwargs)
    monkeypatch.setattr(np,'frombuffer',observe)
    gl.read(p);one_file_calls=len(calls);calls.clear()
    with pytest.raises(gl.LimitError):gl.load_many([p,p],limits=gl.Limits(max_rows=1))
    assert len(calls)==one_file_calls


def test_context_budget_admission_precedes_numeric_copy(monkeypatch):
    s=source(1);a=gl.Artifact.from_arrays([0],[0,1],[0],[1],[s])
    ctx=gl.Context([s],limits=gl.Limits(max_rows=1));ctx.restore(a)
    calls=[];original=np.frombuffer
    def observe(*args,**kwargs):
        calls.append(1);return original(*args,**kwargs)
    monkeypatch.setattr(np,'frombuffer',observe)
    with pytest.raises(gl.LimitError):ctx.restore(a)
    assert calls==[]


def test_nested_numpy_arrays_rejected_before_object_conversion(monkeypatch):
    ctx=gl.Context([],limits=gl.Limits(max_rows=1));nested=[np.zeros(1000)]
    calls=[];original=np.asarray
    def observe(*args,**kwargs):
        if args and args[0] is nested:calls.append(1)
        return original(*args,**kwargs)
    monkeypatch.setattr(np,'asarray',observe)
    with pytest.raises(gl.FormatError):ctx.pack(nested)
    assert calls==[]


def test_restored_constants_work_with_native_covariance_and_repack():
    s=source(1);ctx=gl.Context([s]);a=ctx.pack([ctx.primary(s)[0],3.0])
    restored=ctx.restore(a)
    np.testing.assert_array_equal(gv.evalcov(restored),[[1,0],[0,0]])
    again=ctx.pack(restored)
    np.testing.assert_array_equal(again.indptr,a.indptr)
    np.testing.assert_array_equal(again.indices,a.indices)
    np.testing.assert_array_equal(again.data,a.data)
    constants=gl.Context([]);b=constants.pack([3,4]);values=constants.restore(b)
    np.testing.assert_array_equal(gv.evalcov(values),np.zeros((2,2)))
    assert constants.pack(values).nnz==0


def test_pack_stops_at_nnz_budget_before_later_dependency_lookup():
    s=source(1);ctx=gl.Context([s],limits=gl.Limits(max_nnz=1))
    known=ctx.primary(s)[0];later=gv.gvar(0,1)
    with pytest.raises(gl.LimitError):ctx.pack([known+later])
