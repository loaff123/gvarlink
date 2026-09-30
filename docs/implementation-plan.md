# GVarLink Implementation Plan

Implementation sequence with independent format/oracle and numerical review.

**Goal:** Preserve explicitly shared gvar sources across separately authored artifacts with bounded numeric-only parsing.
**Architecture:** Immutable source and numeric artifact model; fixed binary envelope; gvar context adapter; thin CLI/examples. Numerical propagation remains in gvar.
**Tech stack:** Python 3.11-3.14, NumPy, gvar 13.1.10 (pinned derivative API), pytest. GPL-3.0-or-later.
**Spec:** design.md

## Global constraints
Defaults: 1MiB header, 64MiB file/payload aggregate, 100000 rows, 200000 coordinates, 2000000 nnz, 1024 blocks, rank8, JSON depth16. Independent standardized latent basis only; same UUID/different definition rejects. No pickle, NPY/archive reader, executable metadata, remote references or covariance engine. Original synthetic data only. Record finite-only and floating-point semantics. Core file limits are not an OS RSS limit. No outward communications beyond authorized publication of original work.

## Review focus
- Cumulative load_many/context limits, not just per-file, must reject before gvar construction (Tasks 1/3)
- Symlink/FIFO devices and path replacement must not bypass regular-file check; no-clobber races must not overwrite (Task 2)
- Failed source collision/resource admission must leave context unchanged (Task 3)
- Unknown nonzero dependencies reject; cancelled zero dependencies are harmless (Task 3)
- False affine claims and independently forged matching declarations are scientific trust boundaries, documented rather than falsely solved (Tasks 3/4)

### Task 1: immutable identity/numeric contract
Files: src/gvarlink/{model,errors,limits,__init__}.py; tests/test_model.py; pyproject.toml
Interfaces: Source.create(label,shape,description,revision='1',uuid=None), source.to_dict/from_dict, source.basis_hash; Artifact.from_arrays(mean,indptr,indices,data,sources,shape=None,unit='',interpretation='linearized',limits=Limits()); Limits; FormatError/LimitError/SourceConflictError/DependencyError.
- [ ] Write failing tests for UUID identity, basis collision, source reorder, malformed dimensions/CSR, finite values, readonly independent copies and limits
- [ ] Run red test and retain output
- [ ] Implement validation before allocation with exact bounded products, immutable fields and buffer-backed arrays
- [ ] Run full tests and commit working model

### Task 2: data-only envelope
Files: src/gvarlink/format.py, tests/test_format.py, docs/format-v1.md
Interfaces: write(artifact,path,overwrite=False,limits=Limits()), read(path,limits=Limits()), inspect(path,limits=Limits()). Envelope magic/length/JSON/four arrays/final hash fixed by spec.
- [ ] Write failing tests for roundtrip, independent-reader parity, integrity/schema/duplicates/depth/string/length/type/CSR/payload failures, path/symlink/FIFO and no-clobber behavior
- [ ] Run red tests
- [ ] Implement closed metadata reader, early admission, descriptor-only regular I/O, streamed hashing and immutable numeric parsing; stage/flush/no-clobber publish writer
- [ ] Run suite, independent corpus and commit

### Task 3: gvar compatibility
Files: src/gvarlink/adapter.py, tests/test_adapter.py, tests/test_process.py
Interfaces: Context(sources=(),limits=Limits()), primary(source), pack(values,unit='',interpretation='linearized'), restore(artifact), load_many(paths,limits=Limits()). Return (context, restored arrays) from load_many.
- [ ] Write failing independent gvar/parity tests for shared vs independent identical values, signed loadings, block order, unknown dependency, failed transaction, first-order label and two writers/fresh reader subprocesses
- [ ] Run red tests
- [ ] Implement sparse public disassemble plus tested sparse-vector extraction, standard-normal primary creation and gvar_function restore; reject unsupported gvar version, preflight all merges and totals
- [ ] Run suite and independent rational/matrix oracle; commit

### Task 4: complete user workflow
Files: src/gvarlink/cli.py, examples/{branches,rebin_counts}.py, README.md, docs/{safety,comparison,api,validation}.md, LICENSE, THIRD_PARTY.md, .github/workflows/ci.yml
- [ ] Write failing CLI/example tests from clean install, exact masked-counts conservation and complete branch/cancel workflow
- [ ] Run red tests
- [ ] Implement inspect/verify/demo CLI, complete examples, explicit scientific/format limits and fair alternatives guide
- [ ] Validate wheel/sdist outside source, bounded large serialization, full independent review; record findings and fix regression-backed defects
- [ ] Run final Linux full suite/build plus exact remote tree and macOS/Windows/Linux CI before release completion claim; retain not-run/failed evidence honestly

### Task 5: bounded public delivery
- [ ] Original source/docs/synthetic evidence only; small connector batches, no dependency binaries or huge artifacts
- [ ] Verify exact remote source manifest and final CI commit; static explanatory demo using supported Sites workflow and Library artifact
- [ ] Return concise package outcome and verified links; do not count as a substantial project or claim adoption/academic impact
