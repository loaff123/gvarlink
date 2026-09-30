# Independent agent security/numerical review

2026-09-30. This is an independent agent development review, not a human scientific-domain review, a holdout, a penetration test, or a production-security certification. The reviewer owns only validation files; production repairs belong to the implementation author.

## Scope and attribution

Reviewed the proposed component specification, the prior covariance-feasibility REPORT.md, and later the model, format, and adapter source. Independently authored an exact Fraction/matrix fixture, a standard-library format reader, structural adversarial cases, fresh-process drivers, and identity checks. Original synthetic data only.

The earlier competing evidence remains decisive: gvar already supplies numerical propagation and joint native persistence; RMEllipse already supports shared-mechanism native restart. GVarLink's contribution is a deliberately bounded declared-identity numeric envelope around gvar. It does not establish new covariance mathematics, a newly invented source-identity concept, external adoption demand, or superiority to these alternatives.

## Findings and disposition

### N1: derivative indices are local to a gvar covariance factory (repaired and independently verified)

The first adapter indexed registered primaries only by the integer returned by gvar.disassemble. A new gvar.gvar_factory creates a different covariance matrix whose integer indices restart at zero. In a fresh process, a registered standard-normal coordinate and a foreign coordinate with standard deviation 3 both use derivative index 0. pack accepted the foreign value, serialized coefficient 1, and restore changed its variance from 9 to 1. This violates the nonzero-outside-dependency rejection contract.

Evidence: run_foreign_factory_probe.py; foreign-factory-probe-freeze.sha256; results/foreign-factory-before.json (observed failing result). Required repair: validate covariance-factory identity as well as derivative integer identity before exporting nonzero dependencies. The repaired adapter now rejects this input with DependencyError; the unchanged independent probe passes in results/foreign-factory-after.json.

### N2: global gvar factory switching can silently alias registered sources (repaired and independently verified)

Context captured the gvar module but read its mutable global gvar factory each time a source was added. Calling gvar.switch_gvar between context creation and adding a second source caused the two independent coordinates to live in different covariance worlds. pack([old,new]) exported indices [1,1] instead of [0,1]. Required repair: bind the context's factory at construction and use it for all later primaries, combined with N1's input-factory validation. The repaired adapter retains one covariance world and exports the expected [0,1] indices; the unchanged independent probe passes in results/factory-switch-after.json.

Evidence: run_factory_switch_probe.py; factory-switch-probe-freeze.sha256; results/factory-switch-before.json. The official gvar API documents that values from different factory covariance matrices must not be mixed, and exposes the GVar.cov attribute. [gvar factory contract](https://gvar.readthedocs.io/en/latest/gvar.html#gvar.gvar_factory), [GVar.cov](https://gvar.readthedocs.io/en/latest/gvar.html#gvar.GVar.cov)

### S1: close the exact schema and preflight boundary (addressed in current finite tests)

Initial design needed exact canonical JSON bytes/field sets, recomputed complete basis hashes, bool-versus-int rejection, duplicate UUID rejection, bounded integer tokens/depth/strings, and regular-descriptor open behavior. These were agreed before reader implementation in SCHEMA.md and the text refinement in REVISIONS.md. Independent rehashed structural tests currently pass against production. Metadata and raw payload bytes are bounded and integrity-checked before NumPy decoding. No pickle/archive/decompression/recipe path is present in the format reader.

### N3: finite coefficients do not guarantee finite downstream covariance (documented boundary)

The transport checks finite means and coefficients. Squaring a very large finite coefficient in later gvar covariance arithmetic can overflow. The component must not claim finite covariance for all accepted files or infer scientific correctness from finite arrays. No nonlinear moment correction or covariance computation is part of the transport contract.

### S2: identity and integrity do not authenticate scientific claims (documented boundary)

A hostile producer can recompute every hash and reuse a declared UUID for a different physical acquisition. Checksums detect corruption; canonical declaration matching detects inconsistent declarations. Neither authenticates a producer nor establishes physical source identity. Users must authenticate artifacts and deliberately assign/share UUIDs. Labels never establish identity. Changed local coordinate ordering requires a different basis declaration and cannot be inferred/aligned automatically.

### S3: admission budgets do not bound the entire numerical runtime (documented boundary)

The finite file/header/shape/nnz budgets are admission checks, not RSS guarantees or an OS sandbox. gvar's global covariance allocations are outside registry transaction rollback. Input descriptors stay authoritative and final symlinks/FIFOs are rejected, but the implementation does not promise defense against malicious same-user OS mutation. Hard-link publication/no-clobber behavior and lack of directory fsync need platform/local-filesystem caveats. Larger workload validation is recorded separately in docs/validation.md.

## Final disposition

Both blocking numerical findings were repaired by the implementer and independently rerun using unchanged frozen probes. No blocking finding remains in this review's finite scope. This does not replace a broader security assessment, human domain review, downstream workload validation, or release-specific CI. A separately requested broader security review did not complete; no result from it is claimed here.

After the repairs, the complete current production test suite passes: 67 tests. Independent structural corpus, five identity methods, exact three-process integration and reference-reader self-tests also pass again. The after-fix numerical integration still has maximum absolute error 0 across every production merged category, with exact decoded factors. The native baseline maximum remains 5.684341886080802e-14. Source hashes reviewed at this checkpoint are recorded in reviewed-source.sha256. Later source edits require fresh verification.

After-fix evidence: results/integration-after-fix/validation.json; results/production-corpus-after.json; results/identity-after.json; results/full-suite-after.txt; results/reference-suite-after.txt. Initial passing results and subsequent discovered failures remain retained rather than being overwritten.

## Validation observed

- Fraction oracle hand checks: shared cancellation 0; independent-equal contrast variance 8; signed cross-covariance -1; row-two contrast variance 389/16; total contrast variance 613/16
- Two fresh writers plus a fresh merge process completed under requested 512 MiB address-space/20-second CPU bounds and 30-second wall timeout; no timeout or budget exhaustion occurred. These are requested process limits, not a calibrated enforcement proof
- Reader-decoded means and every CSR factor match the original rational fixture exactly, including permuted whole-block order
- The production merged result exactly matches all dyadic reference means and complete within/cross/joint/contrast covariance entries on this fixture (maximum absolute error 0)
- Trusted native gvar joint JSON roundtrip passes the same frozen tolerance; maximum observed category error 5.684341886080802e-14
- Separate contexts have exactly zero cross-covariance
- Five independent identity/transaction tests pass, including equal-valued distinct UUIDs, label aliasing, same-UUID revision/shape/coordinate-description collisions, block permutation, and a new block appearing before a rejected later conflict
- Seven independent production-reader test methods pass, with 63 recorded mutation/limit subcases plus direct corruption/nonregular-file assertions. Mutations are rehashed where appropriate; checksum failures do not mask all structural checks
- Production pytest at this stage: 58 passed. This result predates N1/N2 repair and is not a claim that the subsequently found bugs were absent
- Reference self-tests include intentionally repeated inherited methods; method count is not treated as independent statistical evidence

## Reproduction

From the repository root, with the local validation interpreter:

    python -m unittest discover -s validation -p 'test_*.py'
    PYTHONPATH=src .venv/bin/python validation/run_production_corpus.py
    .venv/bin/python validation/run_independent_validation.py validation/results/new-run
    PYTHONPATH=src .venv/bin/python validation/run_identity_validation.py
    PYTHONPATH=src .venv/bin/python validation/run_foreign_factory_probe.py validation/results/new-foreign.json
    PYTHONPATH=src .venv/bin/python validation/run_factory_switch_probe.py validation/results/new-switch.json
    .venv/bin/pytest -q

Use a fresh destination for integration: the no-clobber writer correctly refuses an existing artifact. Protocol/fixture/reader/corpus/probe manifests precede their corresponding candidate results. Original failing results remain retained. Text bounds were narrowed transparently after the first reader self-tests; history/reference_reader.v1.py retains the first reader snapshot whose digest appears in reader-freeze.sha256. No expected matrices or tolerances were changed.

## Additional numerical/public-API review

A separate read-only review found and verified fixes for these additional issues:

- Restoring zero-derivative rows as Python floats broke native `gvar.evalcov`. A failing regression now verifies lazy cached zero-derivative GVars for constants, including repack; full67-test suite passed after repair
- Aggregate row/nnz admission and source union checks moved before numeric decoding of the next file; cumulative Context checks moved before snapshot copying. Two allocation-observation regressions failed before repair and passed after
- Nested NumPy arrays within Python lists are rejected before object-array conversion; pass a single ndarray or rectangular nested lists
- Per-row nnz checks now run before each retained derivative entry, rather than after constructing the row. A failing limit-before-later-dependency regression closed it; gvar's extraction itself can still allocate against existing in-memory input

The reviewer exercised100 original seeded dyadic affine cases with constant rows, block permutations and repacking; full covariance matrices matched exactly. It also ran30 selected model/adapter tests with3 file-related tests deliberately excluded. A broader independent filesystem/security review has not been completed. This incomplete broader review is not covered by the successful independent finite format corpus.
