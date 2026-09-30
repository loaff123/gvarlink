# Development validation

Original synthetic data only. Frozen specification/protocol is in validation/PROTOCOL.md; numeric tolerances preceded candidate results. These are exposed development tests, not a held-out study or human domain review.

## Executed locally

- 68 package tests cover the model, file format, gvar adapter, cumulative limits, three-process CLI demo and conservative rebin example
- Independent Fraction oracle: exact means and complete small within/cross/joint/contrast covariance matrices
- Two fresh writers and a third fresh merge process; independently decoded numeric coefficients match exact fixture values; every numerical category passes frozen tolerance
- Native gvar joint JSON serialization parity also passes. This exercises gvar's own documented within-collection contract
- Independent standard-library reader and rehashed malformed-input corpus; same/independent source identity and basis collisions; no executable-data loader
- Independent numerical reviewer:100 seeded dyadic cases with constant rows, source-block permutations and repacking matched covariance exactly
- Review-found factory-local index aliasing, global factory switch, constant-row interoperability, aggregate allocation ordering and nested-array admission bugs repaired with failed-before/passed-after regressions

These specific tests do not establish production security. A separately attempted broader filesystem/security review remained incomplete after a tool-level restriction with no exact denied operation visible to that reviewer. It was not bypassed or retried through another route. See validation/REVIEW.md and docs/safety.md.

## Larger transport check

SCALE_PROTOCOL.md and scale_check.py were hashed before execution. Two writer processes each produced32768 gvar values against65536 private coordinates,4096 common dark coordinates and8 common signed modes. The union held135176 coordinates and720896 nonzero entries.

Observed Linux shared-host results (single requested BLAS/OMP thread):

| Stage | Wire bytes | Wall seconds | Peak RSS |
|---|---:|---:|---:|
| First writer | 6292754 | 1.80 | 90.5MiB |
| Second writer | 6292754 | 1.90 | 89.7MiB |
| Fresh common-context merge/check | 12585508 total | 31.50 | 120.7MiB |

Every mean and marginal variance passed. Selected32×32 within/cross covariance matched the direct coefficient oracle with maximum absolute error0. Branch total variances were68096 each; contrast-total variance5120. This is a bounded transport demonstration, not a timing ranking, original detector benchmark, or guarantee on other hardware. No full65536² covariance was requested. The180-second wall limit was configured per worker; OS memory/CPU sandboxing was not claimed for this scale run.

## Cross-platform and package verification

CI defines Python3.11–3.14 on Linux, macOS and Windows. Until the final remote run succeeds, those combinations are configured targets, not locally verified results. POSIX symlink/FIFO tests skip where the OS/account cannot create them. Integration runner requests Linux resource limits only; other systems record them as unavailable and retain wall timeouts.

Build with `python -m build --no-isolation`, then `python validation/wheel_smoke.py`. The wheel smoke installs into an isolated environment populated from the retained dependency pins, clears PYTHONPATH, runs outside the checkout and executes the real three-process demo. Source/distribution archives contain original source/tests/docs, not dependency binaries.

## Reproduction

```sh
python -m pip install -r requirements-validation.txt
python -m pip install -e .
python -m pytest -q
python -m unittest discover -s validation -p 'test_*.py'
python validation/run_independent_validation.py
PYTHONPATH=src python validation/run_identity_validation.py
PYTHONPATH=src python validation/run_production_corpus.py
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python validation/scale_check.py /tmp/new-gvarlink-scale
```

Use a new directory for scale checks. Retained reports record original return codes/commands/failures. Historical freeze manifests intentionally fingerprint the versions preceding later documented runner/text-contract fixes; use the revision notes rather than treating every historical manifest as the current source. Generated binary artifacts are not included in the GitHub text tree; their exact hashes and original fixture are recorded, and the scripts regenerate them. Small raw artifact copies may be present in a local development directory. Current-source manifests must be regenerated after source edits.

The initial wheel-smoke harness incorrectly assumed a nested venv inherited packages installed only in the parent venv; gvar was missing. That failure is retained. The repaired smoke creates a fresh venv and installs the pinned dependencies before testing the wheel; no package logic changed.
