# Development record

Plan: docs/implementation-plan.md

The component specification deliberately excludes a standalone engine or academic-impact claim.

- Model: 19 tests failed on missing public API, then 19 passed
- Format: 31 tests failed on missing reader/writer API, then aggregate suite 50 passed
- Ruling: use a single uncompressed fixed-layout file rather than ZIP/NPY to remove decompression, path extraction and dtype parser attack surfaces
- Ruling: limits may only be lowered from hard defaults in v1; explicit larger budgets require a reviewed version rather than an untested override
- Ruling: finite means/loadings do not guarantee finite later gvar covariance; transport never claims to execute or bound caller numerical computation
- Source factory uses independent standardized bases; UUID equality and uncorrelated different blocks are user declarations, not verified physics

Validation artifacts are independently authored exposed development checks. Original failures remain local execution evidence; successful tests are not a production-security proof or human domain approval.
- Independent review found factory-local derivative index aliasing: a foreign gvar factory's index0 could be interpreted as an owned source, changing variance49 to1. Added two failing regressions, checked covariance object identity, bound the original factory across global switches, then the full63-test suite passed. Cancelled zero derivatives remain admissible
- Review found aggregate row/nnz and context restore admission happened after numeric decode/copy. Two allocation-observation regressions failed; moved remaining row/nnz and union-source admission into header validation, and context admission before snapshots. Full65-test suite passed
- Nested NumPy arrays within Python lists could allocate object arrays before final size admission. Restricted pack to a top-level ndarray or rectangular nested lists/tuples; nested ndarray test failed then passed. Full66-test suite passed
- Constant-row/native covariance regression repaired; per-row derivative admission now stops before an excess retained entry. Final local suite68 passed; independent reference suite26 methods passed
- Cross-platform integration runner no longer imports Linux-only resource unconditionally; original runner retained and portability revision hashed. Mathematical fixtures/tolerances unchanged
- Clean wheel smoke initially lacked gvar because nested venv inheritance was assumed incorrectly; repaired harness installs pinned dependencies, runs outside checkout, and verifies two writer/one reader demo. Initial failure retained
