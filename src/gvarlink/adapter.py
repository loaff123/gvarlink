"""Version-tested gvar transport. All uncertainty arithmetic remains in gvar."""
from dataclasses import replace
import importlib.metadata
import numbers
import numpy as np
from .errors import DependencyError, FormatError, LimitError, SourceConflictError
from .format import _read_with_size, _snapshot
from .limits import Limits, shape_size
from .model import Artifact, Source, reconcile, validate_sources


def _gvar():
    try:
        version=importlib.metadata.version('gvar')
    except importlib.metadata.PackageNotFoundError as error:
        raise DependencyError('install gvar==13.1.10 for this adapter') from error
    if version!='13.1.10':
        raise DependencyError(f'unsupported gvar {version}; tested sparse API requires 13.1.10')
    import gvar
    return gvar


def _values(values,limits):
    if isinstance(values,np.ndarray):
        shape_size(tuple(values.shape),'output shape',limits.max_rows,limits.max_rank)
    elif isinstance(values,(list,tuple)):
        count=0
        def visit(value,depth):
            nonlocal count
            if isinstance(value,(list,tuple)):
                if depth>limits.max_rank: raise LimitError('output rank exceeds limit')
                if len(value)>limits.max_rows: raise LimitError('output dimension exceeds limit')
                for item in value:visit(item,depth+1)
            elif isinstance(value,np.ndarray):
                raise FormatError('nested numpy arrays are unsupported; pass one ndarray or nested lists')
            else:
                count+=1
                if count>limits.max_rows:raise LimitError('output row count exceeds limit')
        visit(values,1)
    try:array=np.asarray(values,dtype=object)
    except (TypeError,ValueError) as error:raise FormatError('values must form a rectangular array') from error
    shape_size(tuple(array.shape),'output shape',limits.max_rows,limits.max_rank)
    return array


class Context:
    """One intentionally shared stochastic world, with bounded declared sources.

    Restoring more artifacts into this context reconnects matching UUID/basis
    declarations. Separate contexts remain independent. Restore budgets are
    cumulative because the context cannot know when caller outputs are freed.
    This class is not thread-safe; use separate contexts or external locking.
    """
    def __init__(self,sources=(),*,limits=Limits()):
        self.limits=limits
        self._gv=_gvar()
        self._factory=self._gv.gvar
        self._sources=()
        self._primary=np.empty(0,dtype=object)
        self._offsets={}
        self._derivative_ids={}
        self._rows=self._nnz=self._bytes=0
        self._zero=None
        admitted,_=validate_sources(sources,limits)
        state=self._prepare_sources(admitted)
        self._commit_sources(state)

    @property
    def sources(self):return self._sources

    def _prepare_sources(self,sources):
        # Called only after full declaration/aggregate admission.
        new=sources[len(self._sources):]
        primary=[self._primary];offsets=dict(self._offsets);ids=dict(self._derivative_ids)
        offset=len(self._primary)
        for source in new:
            vector=self._factory(np.zeros(source.size),np.ones(source.size))
            primary.append(vector)
            offsets[source.uuid]=(offset,source)
            for local,value in enumerate(vector):
                _,deriv=self._gv.disassemble([value])[0]
                raw=deriv.indices();coef=deriv.values()
                if len(raw)!=1 or len(coef)!=1 or coef[0]!=1:
                    raise DependencyError('unexpected gvar primary derivative representation')
                ids[int(raw[0])]=offset+local
            offset+=source.size
        return sources,np.concatenate(primary),offsets,ids

    def _commit_sources(self,state):
        self._sources,self._primary,self._offsets,self._derivative_ids=state

    def primary(self,source):
        key=source.uuid if isinstance(source,Source) else source
        try:offset,declared=self._offsets[key]
        except (KeyError,TypeError) as error:raise DependencyError('source is not registered in this context') from error
        if isinstance(source,Source) and source.basis!=declared.basis:
            raise SourceConflictError(f'conflicting latent basis for UUID {key}')
        # A caller may edit the returned object array without changing registry slots.
        return self._primary[offset:offset+declared.size].copy().reshape(declared.shape)

    def pack(self,values,*,unit='',interpretation='linearized'):
        array=_values(values,self.limits)
        mean=[];indptr=[0];indices=[];data=[]
        for value in array.flat:
            if isinstance(value,self._gv.GVar):
                nominal,deriv=self._gv.disassemble([value])[0]
                entries=[]
                for index,coefficient in zip(deriv.indices(),deriv.values()):
                    if coefficient==0:continue
                    if len(data)+len(entries)>=self.limits.max_nnz:
                        raise LimitError('derivative nnz exceeds limit')
                    if value.cov is not self._factory.cov:
                        raise DependencyError('nonzero dependency belongs to a different gvar covariance factory')
                    column=self._derivative_ids.get(int(index))
                    if column is None:
                        raise DependencyError('nonzero dependency on an unregistered gvar primary')
                    entries.append((column,float(coefficient)))
                entries.sort()
            elif isinstance(value,numbers.Real) and not isinstance(value,(bool,np.bool_)):
                nominal=float(value);entries=[]
            else:
                raise FormatError('values must contain real scalars or gvar.GVar objects')
            if len(data)+len(entries)>self.limits.max_nnz:
                raise LimitError('derivative nnz exceeds limit')
            mean.append(float(nominal))
            for column,coefficient in entries:indices.append(column);data.append(coefficient)
            indptr.append(len(data))
        return Artifact.from_arrays(mean,indptr,indices,data,self.sources,shape=tuple(array.shape),
                                    unit=unit,interpretation=interpretation,limits=self.limits)

    def restore(self,artifact):
        if not isinstance(artifact,Artifact): raise FormatError('expected Artifact')
        admitted=reconcile(self.sources,artifact.sources,self.limits)
        rows=self._rows+artifact.rows;nnz=self._nnz+artifact.nnz;byte_count=self._bytes+artifact.payload_bytes
        if rows>self.limits.max_rows or nnz>self.limits.max_nnz or byte_count>self.limits.max_file_bytes:
            raise LimitError('cumulative restored outputs exceed context limits')
        a=_snapshot(artifact,self.limits)
        # Prepare without modifying this context. gvar global allocation is not transactional.
        state=self._prepare_sources(admitted)
        _,primaries,offsets,_=state
        mapping=np.empty(a.coordinates,dtype=np.int64)
        start=0
        for source in a.sources:
            target=offsets[source.uuid][0]
            mapping[start:start+source.size]=np.arange(target,target+source.size)
            start+=source.size
        result=np.empty(a.rows,dtype=object)
        zero=self._zero
        for row in range(a.rows):
            begin,end=int(a.indptr[row]),int(a.indptr[row+1])
            if begin==end:
                if zero is None: zero=0*self._factory(0.,0.)
                result[row]=zero+float(a.mean[row])
            else:
                result[row]=self._gv.gvar_function(primaries[mapping[a.indices[begin:end]]],
                                                  float(a.mean[row]),a.data[begin:end])
        self._commit_sources(state)
        self._rows,self._nnz,self._bytes=rows,nnz,byte_count
        self._zero=zero
        return result.reshape(a.shape)


def load_many(paths,*,limits=Limits()):
    """Validate a bounded collection entirely, then restore into one shared context.

    Returns ``(context, list_of_arrays)``. Limits apply to summed wire bytes,
    output rows, nnz and the union of unique latent coordinates/blocks.
    """
    if not isinstance(paths,(list,tuple)):
        raise FormatError('paths must be a bounded list or tuple')
    if len(paths)>limits.max_blocks:
        raise LimitError('file count exceeds block-count limit')
    artifacts=[];sources=();wire_bytes=rows=nnz=0
    for path in paths:
        remaining=limits.max_file_bytes-wire_bytes
        a,size=_read_with_size(path,limits=replace(limits,max_file_bytes=remaining,
                                max_rows=limits.max_rows-rows,max_nnz=limits.max_nnz-nnz),
                               existing_sources=sources)
        wire_bytes+=size;rows+=a.rows;nnz+=a.nnz
        if rows>limits.max_rows or nnz>limits.max_nnz:
            raise LimitError('aggregate outputs exceed limits')
        sources=reconcile(sources,a.sources,limits)
        artifacts.append(a)
    context=Context(sources,limits=limits)
    return context,[context.restore(a) for a in artifacts]
