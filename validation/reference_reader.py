"""Independent standard-library decoder of the agreed closed GVarLink v1 format.

Not a production security guarantee. No NumPy, gvar, pickle, or production import.
"""
import hashlib
import json
import math
import os
import stat
import struct
import uuid

MAGIC = b'GVARLNK1'
DEFAULT_LIMITS = {'max_header_bytes': 1 << 20, 'max_file_bytes': 64 << 20,
                  'max_rows': 100000, 'max_latents': 200000, 'max_nnz': 2000000,
                  'max_sources': 1024, 'max_rank': 8, 'max_depth': 16,
                  'max_string_chars': 4096}
HEADER_KEYS = {'format', 'version', 'shape', 'unit', 'interpretation', 'sources', 'nnz', 'payload_bytes', 'arrays'}
SOURCE_KEYS = {'uuid', 'label', 'revision', 'description', 'shape', 'model', 'order', 'basis_hash'}
BASIS_KEYS = ('revision', 'description', 'shape', 'model', 'order')
ARRAY_KEYS = ('mean', 'indptr', 'indices', 'data')


class InvalidArtifact(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise InvalidArtifact(message)


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('ascii')


def _limits(requested):
    answer = dict(DEFAULT_LIMITS)
    for name, value in (requested or {}).items():
        _require(name in answer, 'unknown resource limit')
        _require(type(value) is int and 0 <= value <= answer[name], 'limit must lower the hard ceiling')
        answer[name] = value
    return answer


def _integer(value, upper, name, minimum=0):
    _require(type(value) is int and minimum <= value <= upper, 'invalid or excessive ' + name)
    return value


def _shape(value, limit, rank, *, source=False):
    _require(type(value) is list and len(value) <= rank, 'invalid shape rank')
    product = 1
    for dimension in value:
        _integer(dimension, limit, 'dimension', minimum=1 if source else 0)
        product *= dimension
        _require(product <= limit, 'shape product exceeds limit')
    _require(product <= limit, 'scalar exceeds limit')
    return product


def _hash(value):
    _require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'noncanonical SHA-256')


def _text(value, maximum, *, nonempty=False):
    _require(type(value) is str, 'text field must be a string')
    _require(len(value) <= maximum and (not nonempty or bool(value)), 'text field length outside contract')
    for character in value:
        point = ord(character)
        _require(point >= 32 and not 0xD800 <= point <= 0xDFFF, 'control character or lone surrogate in text')


def _basis(source):
    return {key: source[key] for key in BASIS_KEYS}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def _parse_int(token):
    _require(len(token) <= 20, 'oversize JSON integer token')
    return int(token)


def _reject_number(token):
    raise InvalidArtifact('noninteger JSON number')


def _preflight_json(raw, limit):
    depth = 0
    quoted = False
    escaped = False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            _require(depth <= limit, 'JSON depth exceeds limit')
        elif byte in (93, 125):
            depth -= 1
            _require(depth >= 0, 'malformed JSON delimiters')
    _require(depth == 0 and not quoted, 'malformed JSON structure')


def _check_strings(value, limit):
    if type(value) is str:
        _require(len(value) <= limit, 'string exceeds limit')
    elif type(value) is dict:
        for key, item in value.items():
            _check_strings(key, limit)
            _check_strings(item, limit)
    elif type(value) is list:
        for item in value:
            _check_strings(item, limit)


def _header(raw, limits):
    _preflight_json(raw, limits['max_depth'])
    try:
        header = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_int=_parse_int, parse_float=_reject_number, parse_constant=_reject_number)
        _require(_canonical(header) == raw, 'header is not canonical JSON')
    except (UnicodeError, json.JSONDecodeError, OverflowError, RecursionError) as error:
        raise InvalidArtifact('invalid JSON header') from error
    _check_strings(header, limits['max_string_chars'])
    _require(type(header) is dict and set(header) == HEADER_KEYS, 'wrong header keys')
    _require(header['format'] == 'gvarlink', 'wrong format')
    _require(type(header['version']) is int and header['version'] == 1, 'unsupported format version')
    _text(header['unit'], 1024)
    _require(header['interpretation'] in ('affine', 'linearized'), 'unsupported interpretation')
    n = _shape(header['shape'], limits['max_rows'], limits['max_rank'])
    nnz = _integer(header['nnz'], limits['max_nnz'], 'nnz')
    sources = header['sources']
    _require(type(sources) is list and len(sources) <= limits['max_sources'], 'source list exceeds limit')
    total = 0
    seen = set()
    for source in sources:
        _require(type(source) is dict and set(source) == SOURCE_KEYS, 'wrong source keys')
        for key in ('uuid', 'label', 'revision', 'description'):
            _require(type(source[key]) is str, 'source field must be text')
        _text(source['label'], 256)
        _text(source['revision'], 128, nonempty=True)
        _text(source['description'], 1024, nonempty=True)
        try:
            canonical_uuid = str(uuid.UUID(source['uuid']))
        except (ValueError, AttributeError) as error:
            raise InvalidArtifact('invalid source UUID') from error
        _require(canonical_uuid == source['uuid'], 'noncanonical UUID')
        _require(canonical_uuid not in seen, 'duplicate source UUID')
        seen.add(canonical_uuid)
        _require(source['model'] == 'independent-standard-normal-v1' and source['order'] == 'C', 'unsupported source basis')
        total += _shape(source['shape'], limits['max_latents'], limits['max_rank'], source=True)
        _require(total <= limits['max_latents'], 'total coordinates exceed limit')
        _hash(source['basis_hash'])
        _require(hashlib.sha256(_canonical(_basis(source))).hexdigest() == source['basis_hash'], 'basis fingerprint differs')
    lengths = (8*n, 8*(n+1), 8*nnz, 8*nnz)
    payload_bytes = _integer(header['payload_bytes'], limits['max_file_bytes'], 'payload_bytes')
    _require(sum(lengths) == payload_bytes, 'payload length inconsistent')
    _require(type(header['arrays']) is dict and set(header['arrays']) == set(ARRAY_KEYS), 'wrong array hash keys')
    for value in header['arrays'].values():
        _hash(value)
    return header, n, nnz, total, lengths


def _exact(stream, n):
    value = stream.read(n)
    _require(len(value) == n, 'truncated artifact')
    return value


def read(path, *, limits=None):
    """Read one local regular artifact into validated standard-library tuples."""
    limits = _limits(limits)
    try:
        before = os.lstat(path)
        _require(stat.S_ISREG(before.st_mode), 'only regular nonsymlink files accepted')
        flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            _require(stat.S_ISREG(opened.st_mode), 'opened object is not regular')
            _require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), 'path changed while opening')
            _require(48 <= opened.st_size <= limits['max_file_bytes'], 'file size exceeds admission limits')
            prefix = _exact(stream,16)
            _require(prefix[:8] == MAGIC, 'wrong magic')
            header_length = struct.unpack('<Q', prefix[8:])[0]
            _require(header_length <= limits['max_header_bytes'], 'header exceeds limit')
            _require(header_length <= opened.st_size-48, 'header exceeds file size')
            raw = _exact(stream, header_length)
            header,n,nnz,total,lengths = _header(raw, limits)
            expected_size = 16 + header_length + sum(lengths) + 32
            _require(expected_size == opened.st_size, 'file size inconsistent with declarations')
            digest = hashlib.sha256(prefix + raw)
            arrays = {}
            for name,size in zip(ARRAY_KEYS,lengths):
                data = _exact(stream,size)
                digest.update(data)
                _require(hashlib.sha256(data).hexdigest() == header['arrays'][name], 'array digest mismatch')
                arrays[name] = data
            _require(_exact(stream,32) == digest.digest(), 'whole-file digest mismatch')
            _require(stream.read(1) == b'', 'unexpected trailing bytes')
            _require(os.fstat(stream.fileno()).st_size == expected_size, 'file size changed during read')
    except OSError as error:
        raise InvalidArtifact('file could not be safely read') from error
    # No numeric sequence is unpacked until all schema, size and integrity checks pass.
    mean = tuple(item[0] for item in struct.iter_unpack('<d', arrays['mean']))
    indptr = tuple(item[0] for item in struct.iter_unpack('<Q', arrays['indptr']))
    indices = tuple(item[0] for item in struct.iter_unpack('<Q', arrays['indices']))
    data = tuple(item[0] for item in struct.iter_unpack('<d', arrays['data']))
    _require(all(map(math.isfinite,mean)) and all(math.isfinite(x) and x != 0 for x in data), 'nonfinite or explicit zero numeric value')
    _require(indptr[0] == 0 and indptr[-1] == nnz, 'invalid CSR endpoints')
    for start,end in zip(indptr,indptr[1:]):
        _require(start <= end <= nnz, 'invalid CSR row range')
        previous = -1
        for column in indices[start:end]:
            _require(previous < column < total, 'invalid CSR column ordering or bounds')
            previous = column
    return {'header':header, 'mean':mean, 'indptr':indptr, 'indices':indices, 'data':data}


def reconcile(documents):
    """Return UUID -> definition; labels may differ, ordered basis may not."""
    sources = {}
    for document in documents:
        for source in document['header']['sources']:
            previous = sources.get(source['uuid'])
            if previous is not None:
                _require(_basis(previous) == _basis(source), 'UUID basis conflict')
            else:
                sources[source['uuid']] = source
    return sources


if __name__ == '__main__':
    import sys
    doc = read(sys.argv[1])
    print(json.dumps(doc, allow_nan=False, sort_keys=True, indent=2))
