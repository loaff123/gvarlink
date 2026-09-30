# API contract

## Source
`Source.create(label, shape, description, revision='1', uuid=None)` generates UUID4 unless one is explicitly supplied. Shape is an ordered tuple/list of positive integers, or `()` for one scalar coordinate. Description (1–1024 characters) and revision (1–128) define the basis. Label (0–256) is display-only. Control characters and lone surrogates are refused. `basis_hash`, `size`, `basis`, `to_dict()` and `Source.from_dict()` expose the declaration. Imported fingerprint is recomputed, not trusted. Duplicate UUIDs within one artifact/context declaration are invalid even if equal.

## Context
`Context(sources=(), limits=Limits())` binds the current gvar factory once and creates mutually uncorrelated standard-normal primaries. `primary(source_or_uuid)` returns a copy of the object array with the declared source shape. This context is not thread-safe; use external synchronization.

`pack(values, unit='', interpretation='linearized')` accepts a NumPy array, real/GVar scalar, or rectangular nested lists/tuples. Nested NumPy arrays within a list are refused; pass one ndarray. It rejects nonzero dependencies outside this context and covariance-factory mismatches. Zero coefficients disappear; genuine cancellation therefore works. gvar’s disassemble and sparse-vector methods are tested for the exact pinned release. No expression callbacks, factory identifiers, or Python objects enter the file.

`restore(artifact)` reconciles the union of source declarations and returns a NumPy object array of gvar.GVar values, including constant rows. Whole-block order is remapped. Admission and reconstruction failures leave the context registry/counters unchanged; gvar factory allocations themselves cannot be rolled back. Successful restores consume cumulative row/nnz/payload budgets, since the context cannot know whether caller outputs have been freed. Start a new context for an unrelated workflow; outputs across contexts do not reconnect automatically.

`load_many(paths, limits=Limits()) -> (context, arrays)` takes a finite list/tuple, fully validates every file and the source union before constructing gvar outputs, then restores all into one context. File count is capped by max_blocks. Aggregate wire bytes, row count and nnz are bounded. Matching definitions with changed labels are allowed; the first label wins in the context registry.

## Artifact
`Artifact.from_arrays(mean, indptr, indices, data, sources, shape=None, unit='', interpretation='linearized', limits=Limits())` is the explicit numeric interchange boundary. It copies finite numeric vectors into immutable byte-backed arrays. Default output shape is `(len(mean),)`; `()` means a scalar and `(0, ...)` is empty. Integer CSR vectors must actually contain nonnegative integers; float casts/bools are not accepted. Every CSR row has strictly increasing column indices and no explicit zero coefficients. There are no transform/covariance operations on Artifact.

Artifacts expose `mean`, `indptr`, `indices`, `data`, `sources`, `shape`, `unit`, `interpretation`, `rows`, `nnz`, `coordinates`, `payload_bytes`. Treat construction as a copy; it is not a zero-copy or streaming API. Type annotations/dataclass immutability are not a defense against hostile code already executing inside Python.

## I/O and failures
`write(artifact, path, overwrite=False, limits=Limits())` validates a snapshot and stages an atomic publication. Existing destination raises `FileExistsError`. `read(path, limits=Limits())` returns a validated Artifact. `inspect(path, limits=Limits())` fully reads and verifies, then returns a JSON-compatible metadata dict; it is not a cheap header-only peek.

`GVarLinkError` subclasses `ValueError`. `FormatError` denotes invalid/unsupported data, `LimitError` admission failure, `SourceConflictError` conflicting latent definitions, and `DependencyError` unsupported gvar versions or unregistered dependencies. Ordinary filesystem errors remain OSError subclasses. CLI emits a concise error to stderr and exit2. Failed reads return no partial artifact; demo failure may leave its already-written evidence directory for inspection.

## Interpretation and units
Use affine only when all uncertainty dependencies really are affine with deterministic coefficients/masks. Native gvar nonlinear operations propagate local derivative information; pack defaults to linearized. Importing or repacking does not automatically infer scientific provenance. Always pass the artifact interpretation forward deliberately; `load_many` arrays alone do not carry the metadata. Inspect/read each artifact when interpretation or units matter. Never label a result affine just because restoring it uses a linear combination.
