import hashlib
import json
import os
import struct
from dataclasses import replace
import numpy as np
import pytest
import gvarlink as gl
from test_model import artifact


def rewrite(raw, edit=None, header_bytes=None, payload_edit=None):
    length=struct.unpack('<Q',raw[8:16])[0]
    meta=json.loads(raw[16:16+length]); payload=raw[16+length:-32]
    if edit:edit(meta)
    if payload_edit:payload=payload_edit(payload)
    header=header_bytes if header_bytes is not None else json.dumps(meta,ensure_ascii=True,sort_keys=True,separators=(',',':')).encode()
    body=b'GVARLNK1'+struct.pack('<Q',len(header))+header+payload
    return body+hashlib.sha256(body).digest()


def test_roundtrip_and_no_clobber(tmp_path):
    p=tmp_path/'x.gvl'; a=artifact();gl.write(a,p);b=gl.read(p)
    for name in ('mean','indptr','indices','data'):np.testing.assert_array_equal(getattr(a,name),getattr(b,name))
    assert a.sources==b.sources and a.interpretation==b.interpretation
    assert gl.inspect(p)['integrity']=='verified'
    old=p.read_bytes()
    with pytest.raises(FileExistsError):gl.write(a,p)
    assert old==p.read_bytes()
    gl.write(a,p,overwrite=True);assert p.read_bytes()==old
    assert not list(tmp_path.glob('.*.tmp'))


@pytest.mark.parametrize('edit',[
    lambda h:h.update(version=2),lambda h:h.update(version=True),lambda h:h.update(extra=1),
    lambda h:h.update(shape=[True]),lambda h:h.update(shape=[2**63]),lambda h:h.update(nnz=2**63),
    lambda h:h.update(payload_bytes=0),lambda h:h.update(interpretation='unknown'),
    lambda h:h['sources'].append(h['sources'][0]),lambda h:h['sources'][0].update(basis_hash='0'*64),
    lambda h:h['arrays'].update(mean='0'*64),lambda h:h.update(unit='x'*5000),
    lambda h:h['sources'][0].update(model='correlated'),lambda h:h['sources'][0].update(uuid='NO'),
])
def test_rehashed_invalid_header_rejected(tmp_path,edit):
    p=tmp_path/'x';gl.write(artifact(),p);p.write_bytes(rewrite(p.read_bytes(),edit))
    with pytest.raises(gl.GVarLinkError):gl.read(p)


@pytest.mark.parametrize('raw_header',[
    b'{"version":1,"version":1}',b'{"x":'+b'['*30+b'0'+b']'*30+b'}',
    b'{"x":1e100000000}',b'{"x":'+b'9'*100+b'}',b'{"x":NaN}',b'{} ',b'\xff',
])
def test_bounded_json_rejects_before_numeric_decode(tmp_path,raw_header):
    p=tmp_path/'x';gl.write(artifact(),p);p.write_bytes(rewrite(p.read_bytes(),header_bytes=raw_header))
    with pytest.raises(gl.GVarLinkError):gl.read(p)


@pytest.mark.parametrize('kind',['truncate','trailing','trailer','payload','magic','huge-header'])
def test_corruption(tmp_path,kind):
    p=tmp_path/'x';gl.write(artifact(),p);raw=p.read_bytes()
    if kind=='truncate':raw=raw[:-4]
    elif kind=='trailing':raw+=b'x'
    elif kind=='trailer':raw=raw[:-1]+bytes([raw[-1]^1])
    elif kind=='payload':raw=raw[:len(raw)-40]+bytes([raw[-40]^1])+raw[len(raw)-39:]
    elif kind=='magic':raw=b'BADMAGIC'+raw[8:]
    else:raw=raw[:8]+struct.pack('<Q',2**63)+raw[16:]
    p.write_bytes(raw)
    with pytest.raises(gl.GVarLinkError):gl.read(p)


def test_lowered_limits_and_no_symlink(tmp_path):
    p=tmp_path/'x';gl.write(artifact(),p)
    for limits in [gl.Limits(max_rows=1),gl.Limits(max_coordinates=1),gl.Limits(max_nnz=2),gl.Limits(max_header_bytes=10),gl.Limits(max_file_bytes=100)]:
        with pytest.raises(gl.LimitError):gl.read(p,limits=limits)
    link=tmp_path/'link'
    try:link.symlink_to(p)
    except (OSError,NotImplementedError):pytest.skip('symlink unavailable')
    with pytest.raises(gl.FormatError):gl.read(link)
    old=p.read_bytes()
    with pytest.raises((gl.FormatError,FileExistsError)):gl.write(artifact(),link)
    assert old==p.read_bytes()


def test_fifo_rejected_without_blocking(tmp_path):
    if not hasattr(os,'mkfifo'):pytest.skip('FIFO unavailable')
    p=tmp_path/'pipe';os.mkfifo(p)
    with pytest.raises(gl.FormatError):gl.read(p)


def test_write_failure_cleans_stage(tmp_path,monkeypatch):
    p=tmp_path/'out'
    def fail(*a,**k):raise OSError('simulated publication failure')
    monkeypatch.setattr(os,'link',fail)
    with pytest.raises(OSError):gl.write(artifact(),p)
    assert not p.exists() and list(tmp_path.iterdir())==[]
