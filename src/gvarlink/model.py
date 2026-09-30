"""Declared standard-normal bases and immutable numeric interchange objects."""
from dataclasses import dataclass
import hashlib
import json
import uuid as uuid_module
import numpy as np
from .errors import FormatError, LimitError, SourceConflictError
from .limits import Limits, checked_int, shape_size

MODEL = 'independent-standard-normal-v1'
SOURCE_KEYS = {'uuid','label','revision','description','shape','model','order','basis_hash'}


def canonical(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False,
                      sort_keys=True, separators=(',', ':')).encode('ascii')


def text_field(value, name, maximum=1024, *, empty=True):
    if type(value) is not str or len(value) > maximum or (not empty and not value):
        raise FormatError(f'{name} must be a string of length {0 if empty else 1}..{maximum}')
    if any(ord(c)<32 or 0xD800<=ord(c)<=0xDFFF for c in value):
        raise FormatError(f'{name} contains a control character or lone surrogate')
    return value


@dataclass(frozen=True)
class Source:
    uuid: str
    label: str
    shape: tuple[int, ...]
    description: str
    revision: str = '1'

    def __post_init__(self):
        try:
            valid = str(uuid_module.UUID(self.uuid)) == self.uuid
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise FormatError('source uuid must be canonical lowercase UUID')
        text_field(self.label, 'label', 256)
        text_field(self.description, 'description', 1024, empty=False)
        text_field(self.revision, 'revision', 128, empty=False)
        dims, _ = shape_size(self.shape, 'source shape', 200_000, 8, source=True)
        object.__setattr__(self, 'shape', dims)

    @classmethod
    def create(cls, label, shape, description, revision='1', uuid=None):
        return cls(str(uuid_module.uuid4()) if uuid is None else uuid,
                   label, shape, description, revision)

    @property
    def size(self):
        return shape_size(self.shape, 'source shape', 200_000, 8, source=True)[1]

    @property
    def basis(self):
        return dict(model=MODEL, order='C', revision=self.revision,
                    description=self.description, shape=list(self.shape))

    @property
    def basis_hash(self):
        return hashlib.sha256(canonical(self.basis)).hexdigest()

    def to_dict(self):
        return dict(uuid=self.uuid, label=self.label, basis_hash=self.basis_hash, **self.basis)

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict or set(value) != SOURCE_KEYS:
            raise FormatError('source fields do not match schema v1')
        if value['model'] != MODEL or value['order'] != 'C':
            raise FormatError('unsupported latent model or coordinate order')
        obj = cls(value['uuid'], value['label'], value['shape'], value['description'], value['revision'])
        if value['basis_hash'] != obj.basis_hash:
            raise FormatError('source basis fingerprint mismatch')
        return obj


def validate_sources(sources, limits):
    if not isinstance(sources, (list, tuple)):
        raise FormatError('sources must be a list or tuple')
    if len(sources)>limits.max_blocks:
        raise LimitError('source blocks exceed limit')
    seen=set(); total=0
    for source in sources:
        if not isinstance(source, Source):
            raise FormatError('sources must contain Source objects')
        if source.uuid in seen:
            raise FormatError('duplicate source UUID')
        seen.add(source.uuid)
        _, size = shape_size(source.shape, 'source shape', limits.max_coordinates, limits.max_rank, source=True)
        total += size
        if total>limits.max_coordinates:
            raise LimitError('total latent coordinates exceed limit')
    return tuple(sources), total


def reconcile(existing, incoming, limits):
    """Return the admitted union without mutating either input."""
    existing, _ = validate_sources(existing, limits)
    incoming, _ = validate_sources(incoming, limits)
    by_id={s.uuid:s for s in existing}
    result=list(existing)
    for source in incoming:
        old=by_id.get(source.uuid)
        if old is not None:
            if old.basis != source.basis:
                raise SourceConflictError(f'conflicting latent basis for UUID {source.uuid}')
        else:
            by_id[source.uuid]=source; result.append(source)
    return validate_sources(result, limits)[0]


def _array(value, dtype, maximum, name, *, integer=False):
    if not isinstance(value, (list, tuple, np.ndarray)):
        raise FormatError(f'{name} must be a numeric vector')
    if isinstance(value, np.ndarray):
        if value.ndim!=1 or value.dtype.kind not in ('iu' if integer else 'iuf'):
            raise FormatError(f'{name} must be a one-dimensional numeric vector')
        length=value.size
    else:
        length=len(value)
        # Checking before np.asarray prevents object/complex/bool coercion.
        allowed=(int, np.integer) if integer else (int,float,np.integer,np.floating)
        for item in value:
            if isinstance(item, (bool,np.bool_)) or not isinstance(item, allowed):
                raise FormatError(f'{name} has a nonnumeric or wrong-kind item')
    if length>maximum:
        raise LimitError(f'{name} length exceeds limit')
    if integer:
        for item in value:
            if int(item)<0 or int(item)>2**64-1:
                raise FormatError(f'{name} contains out-of-range unsigned integer')
    try:
        result=np.asarray(value, dtype=dtype)
    except (ValueError,TypeError,OverflowError) as error:
        raise FormatError(f'{name} cannot be represented as {dtype}') from error
    if result.ndim!=1:
        raise FormatError(f'{name} must be a vector')
    if not integer and not np.isfinite(result).all():
        raise FormatError(f'{name} must be finite')
    # Backed by immutable bytes, not merely a reversible NumPy writeable flag.
    return np.frombuffer(result.tobytes(), dtype=dtype)


@dataclass(frozen=True, init=False)
class Artifact:
    mean: np.ndarray
    indptr: np.ndarray
    indices: np.ndarray
    data: np.ndarray
    sources: tuple[Source, ...]
    shape: tuple[int, ...]
    unit: str
    interpretation: str

    @classmethod
    def from_arrays(cls, mean, indptr, indices, data, sources, *, shape=None,
                    unit='', interpretation='linearized', limits=Limits()):
        sources, coordinates=validate_sources(sources, limits)
        text_field(unit, 'unit')
        if interpretation not in ('affine','linearized'):
            raise FormatError('interpretation must be affine or linearized')
        # Inspect lengths before copying any numeric buffer.
        for value,name,maximum in [(mean,'mean',limits.max_rows),(indptr,'indptr',limits.max_rows+1),
                                  (indices,'indices',limits.max_nnz),(data,'data',limits.max_nnz)]:
            if not isinstance(value,(list,tuple,np.ndarray)):
                raise FormatError(f'{name} must be a vector')
            if isinstance(value,np.ndarray) and value.ndim!=1:
                raise FormatError(f'{name} must be a vector')
            if len(value)>maximum:
                raise LimitError(f'{name} length exceeds limit')
        shape,n=shape_size((len(mean),) if shape is None else shape, 'output shape', limits.max_rows, limits.max_rank)
        if n!=len(mean) or len(indptr)!=n+1 or len(indices)!=len(data):
            raise FormatError('array lengths do not match declared shape/nnz')
        payload=8*n+8*(n+1)+16*len(data)
        if payload>limits.max_file_bytes:
            raise LimitError('numeric payload exceeds byte limit')
        mean=_array(mean,'<f8',n,'mean')
        ptr=_array(indptr,'<u8',n+1,'indptr',integer=True)
        ix=_array(indices,'<u8',limits.max_nnz,'indices',integer=True)
        values=_array(data,'<f8',limits.max_nnz,'data')
        if ptr[0]!=0 or ptr[-1]!=len(values) or np.any(ptr[1:]<ptr[:-1]) or np.any(ptr>len(values)):
            raise FormatError('invalid CSR row pointers')
        if np.any(ix>=coordinates) or np.any(values==0):
            raise FormatError('out-of-range column or explicit zero coefficient')
        for row in range(n):
            start,end=int(ptr[row]),int(ptr[row+1])
            if np.any(ix[start+1:end]<=ix[start:end-1]) if end-start>1 else False:
                raise FormatError('CSR row columns must be strictly increasing')
        obj=object.__new__(cls)
        for name,value in [('mean',mean),('indptr',ptr),('indices',ix),('data',values),
                           ('sources',sources),('shape',shape),('unit',unit),('interpretation',interpretation)]:
            object.__setattr__(obj,name,value)
        return obj

    @property
    def rows(self): return len(self.mean)
    @property
    def nnz(self): return len(self.data)
    @property
    def coordinates(self): return sum(s.size for s in self.sources)
    @property
    def payload_bytes(self): return 8*self.rows+8*(self.rows+1)+16*self.nnz
