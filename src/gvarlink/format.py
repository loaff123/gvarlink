"""Closed, uncompressed numeric v1 format. Hashes detect corruption, not forgery."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import tempfile
import numpy as np
from .errors import FormatError, LimitError
from .limits import Limits, checked_int, shape_size
from .model import Artifact, Source, canonical, text_field, validate_sources, reconcile

MAGIC=b'GVARLNK1'
HEADER_KEYS={'format','version','shape','unit','interpretation','sources','nnz','payload_bytes','arrays'}
ARRAY_NAMES=('mean','indptr','indices','data')


def _json_depth(raw, limit):
    depth=0; quoted=False; escaped=False
    for byte in raw:
        if quoted:
            if escaped: escaped=False
            elif byte==92: escaped=True
            elif byte==34: quoted=False
        elif byte==34: quoted=True
        elif byte in (123,91):
            depth+=1
            if depth>limit: raise LimitError('JSON depth exceeds limit')
        elif byte in (125,93): depth-=1
    if depth!=0 or quoted:
        raise FormatError('unbalanced JSON')


def _pairs(pairs):
    obj={}
    for key,value in pairs:
        if key in obj: raise FormatError('duplicate JSON key')
        obj[key]=value
    return obj


def _integer(token):
    if len(token)>20: raise LimitError('JSON integer token exceeds 20 characters')
    return int(token)


def _not_numeric(token):
    raise FormatError('header permits integer numbers only')


def _tree(value):
    if isinstance(value,str):
        if len(value)>4096: raise LimitError('JSON string exceeds 4096 characters')
    elif isinstance(value,dict):
        for k,v in value.items(): _tree(k);_tree(v)
    elif isinstance(value,list):
        for v in value: _tree(v)


def decode_header(raw, limits):
    _json_depth(raw,limits.max_json_depth)
    try:
        value=json.loads(raw,object_pairs_hook=_pairs,parse_int=_integer,
                         parse_float=_not_numeric,parse_constant=_not_numeric)
        _tree(value)
        if canonical(value)!=raw: raise FormatError('header is not canonical ASCII JSON')
    except (UnicodeDecodeError,json.JSONDecodeError,RecursionError,ValueError) as error:
        if isinstance(error,(FormatError,LimitError)): raise
        raise FormatError('invalid canonical JSON header') from error
    if type(value) is not dict or set(value)!=HEADER_KEYS:
        raise FormatError('header fields do not match v1 schema')
    if value['format']!='gvarlink' or type(value['version']) is not int or value['version']!=1:
        raise FormatError('unsupported format or schema version')
    shape,n=shape_size(value['shape'],'output shape',limits.max_rows,limits.max_rank)
    nnz=checked_int(value['nnz'],'nnz',limits.max_nnz)
    text_field(value['unit'],'unit')
    if value['interpretation'] not in ('affine','linearized'):
        raise FormatError('unsupported interpretation')
    if type(value['sources']) is not list:
        raise FormatError('sources must be a list')
    if len(value['sources'])>limits.max_blocks:
        raise LimitError('source block count exceeds limit')
    sources=tuple(Source.from_dict(s) for s in value['sources'])
    validate_sources(sources,limits)
    payload=8*n+8*(n+1)+16*nnz
    checked_int(value['payload_bytes'],'payload_bytes',limits.max_file_bytes)
    if value['payload_bytes']!=payload:
        raise FormatError('payload byte count mismatch')
    hashes=value['arrays']
    if type(hashes) is not dict or set(hashes)!=set(ARRAY_NAMES):
        raise FormatError('array checksum fields do not match schema')
    for digest in hashes.values():
        if type(digest) is not str or re.fullmatch('[0-9a-f]{64}',digest) is None:
            raise FormatError('malformed SHA-256 digest')
    return value, sources, n, nnz


def _open_regular(path):
    """Open once, refusing a final symlink and nonregular objects before read."""
    before=os.lstat(path)
    if not stat.S_ISREG(before.st_mode):
        raise FormatError('input must be a regular file, not a symlink/device/FIFO')
    flags=os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NONBLOCK',0)|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(path,flags)
    try:
        after=os.fstat(fd)
        if not stat.S_ISREG(after.st_mode) or (before.st_dev,before.st_ino)!=(after.st_dev,after.st_ino):
            raise FormatError('input changed during opening or is not regular')
        return os.fdopen(fd,'rb'),after.st_size
    except BaseException:
        os.close(fd);raise


def _read_with_size(path, *, limits=Limits(), existing_sources=()):
    """Validate one local file before creating numeric arrays; no executable loader."""
    stream,size=_open_regular(path)
    with stream:
        if size>limits.max_file_bytes: raise LimitError('file exceeds byte limit')
        if size<48: raise FormatError('file too short')
        prefix=stream.read(16)
        if len(prefix)!=16 or prefix[:8]!=MAGIC: raise FormatError('bad magic or truncated prefix')
        length=struct.unpack('<Q',prefix[8:])[0]
        if length>limits.max_header_bytes: raise LimitError('header exceeds byte limit')
        if 16+length+32>size: raise FormatError('declared header exceeds file')
        raw=stream.read(length)
        if len(raw)!=length: raise FormatError('truncated header')
        meta,sources,n,nnz=decode_header(raw,limits)
        reconcile(existing_sources,sources,limits)
        expected=16+length+meta['payload_bytes']+32
        if expected>limits.max_file_bytes: raise LimitError('declared file exceeds byte limit')
        if expected!=size: raise FormatError('file size does not match payload declaration')
        # Payload is raw bounded bytes. Array construction follows both digest checks.
        payload=stream.read(meta['payload_bytes'])
        trailer=stream.read(32)
        if len(payload)!=meta['payload_bytes'] or len(trailer)!=32 or stream.read(1):
            raise FormatError('truncated or trailing payload')
        whole=hashlib.sha256(prefix);whole.update(raw);whole.update(payload)
        if whole.digest()!=trailer: raise FormatError('whole-file checksum mismatch')
        lengths=(8*n,8*(n+1),8*nnz,8*nnz)
        buffers=[];offset=0
        view=memoryview(payload)
        for name,length in zip(ARRAY_NAMES,lengths):
            chunk=view[offset:offset+length];offset+=length
            if hashlib.sha256(chunk).hexdigest()!=meta['arrays'][name]:
                raise FormatError(f'{name} checksum mismatch')
            buffers.append(chunk)
        arrays=[np.frombuffer(b,dtype=d) for b,d in zip(buffers,('<f8','<u8','<u8','<f8'))]
        return (Artifact.from_arrays(*arrays,sources,shape=tuple(meta['shape']),unit=meta['unit'],
                                     interpretation=meta['interpretation'],limits=limits), size)


def read(path, *, limits=Limits()):
    """Read and validate a bounded numeric artifact without executing data."""
    return _read_with_size(path, limits=limits)[0]


def _snapshot(artifact,limits):
    if not isinstance(artifact,Artifact): raise FormatError('expected Artifact')
    return Artifact.from_arrays(artifact.mean,artifact.indptr,artifact.indices,artifact.data,
                                artifact.sources,shape=artifact.shape,unit=artifact.unit,
                                interpretation=artifact.interpretation,limits=limits)


def write(artifact, path, *, overwrite=False, limits=Limits()):
    """Stage and atomically publish one artifact; fail rather than silently clobber."""
    if type(overwrite) is not bool: raise FormatError('overwrite must be bool')
    a=_snapshot(artifact,limits)
    buffers=[getattr(a,name).tobytes() for name in ARRAY_NAMES]
    meta=dict(format='gvarlink',version=1,shape=list(a.shape),unit=a.unit,
              interpretation=a.interpretation,sources=[s.to_dict() for s in a.sources],
              nnz=a.nnz,payload_bytes=a.payload_bytes,
              arrays={n:hashlib.sha256(b).hexdigest() for n,b in zip(ARRAY_NAMES,buffers)})
    header=canonical(meta)
    if len(header)>limits.max_header_bytes: raise LimitError('header exceeds byte limit')
    if 16+len(header)+a.payload_bytes+32>limits.max_file_bytes:
        raise LimitError('file exceeds byte limit')
    # Enforce lowered depth and all reader metadata limits on writer output too.
    decode_header(header,limits)
    destination=Path(path)
    if destination.exists() or destination.is_symlink():
        if not overwrite: raise FileExistsError(str(destination))
        if not stat.S_ISREG(destination.lstat().st_mode):
            raise FormatError('overwrite destination must be a regular file')
    fd,temp=tempfile.mkstemp(prefix=f'.{destination.name}.',suffix='.tmp',dir=destination.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            digest=hashlib.sha256()
            for piece in (MAGIC+struct.pack('<Q',len(header)),header,*buffers):
                stream.write(piece);digest.update(piece)
            stream.write(digest.digest());stream.flush();os.fsync(stream.fileno())
        if overwrite:
            os.replace(temp,destination)
        else:
            # link is atomic create-if-absent on supported local filesystems.
            # No rename fallback: Windows/POSIX overwrite semantics differ.
            os.link(temp,destination)
            os.unlink(temp)
    finally:
        try:os.unlink(temp)
        except FileNotFoundError:pass


def inspect(path, *, limits=Limits()):
    """Fully verify a file and return bounded metadata, not just a header peek."""
    a=read(path,limits=limits)
    return dict(format='gvarlink',version=1,integrity='verified',shape=list(a.shape),
                rows=a.rows,nnz=a.nnz,coordinates=a.coordinates,
                sources=[s.to_dict() for s in a.sources],unit=a.unit,
                interpretation=a.interpretation,payload_bytes=a.payload_bytes)
