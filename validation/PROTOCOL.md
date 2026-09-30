# GVarLink independent development validation protocol

Frozen before candidate implementation results, 2026-09-30. This is an independent agent-authored development check, not a holdout, human domain review, penetration test, or proof of production security.

## Attribution and scope

The predecessor covariance-feasibility REPORT.md establishes that gvar already performs the numerical propagation and that RMEllipse already preserves shared mechanism identities across native restart. This work tests a narrow declared-identity numeric transport companion. No new covariance mathematics, source-identity invention, external demand, or human expert review is claimed. Only original deterministic synthetic fixtures are used.

## Exact fixture, oracle, and stopping condition

The original synthetic fixture `fixtures/branch_model.json` defines two three-row affine branches using independent standardized latent coordinates. They share two dark coordinates and one calibration coordinate, have independent but equal-valued exposure sources, and declare whole blocks in different orders. All means and factors are dyadic rational numbers, so input binary64 values are exact. A standalone standard-library Fraction oracle computes means, complete within/cross/joint covariance, paired contrasts, and total contrast variance directly from the fixture. It does not import production or gvar. Its source-coordinate identity map is UUID plus ordered local coordinate, with complete basis declarations checked separately.

Expected hand checks: shared row-zero contrast has variance 0; independent-equal row-one contrast has variance 8; signed cross-covariance A[2],B[2] is -1; A[2] variance is 61/4; B[2] variance is 113/16; row-two contrast variance is 389/16. Full matrices are generated with exact Fraction multiplication and summation, never inferred from candidate outputs. Every matrix/mean element must pass absolute error <= 5e-12 * max(1, largest absolute reference entry in that category). Expected zero entries must pass absolute error <= 5e-12. No tolerance changes after candidate results.

Separate fresh processes must write each branch, then a third fresh process must merge them. An independent standard-library reader must decode the production artifacts without importing gvar, NumPy, or production source. Decoded means/CSR factors must match the direct fixture after explicit whole-block permutation. Source-label changes do not change identity. Equal-valued different UUIDs remain independent. Same UUID with reordered shape/basis/revision fails closed. Separate contexts intentionally do not establish correlation.

## Input rejection and bounded tests

Freeze format details with the implementer before writing the independent reader; a separately hashed schema addendum may refine representation without changing expected mathematics. Reject unknown fields/version/model, duplicated keys or UUIDs, wrong basis fingerprint, UUID spelling errors, booleans in integer fields, impossible or oversize dimension products, non-finite numeric data, malformed or noncanonical CSR (indptr endpoints/length/order, out-of-range indices, duplicate/unsorted row columns, explicit zero factors), array checksum failures, full checksum failure, truncated/trailing files, oversized header/file, excessively deep JSON, oversized strings/integer tokens, and nonregular paths. Validate declared lengths and counts before numeric unpacking; no pickle, archive, decompression, executable metadata, or user-selected dtypes.

Adversarial fixtures are authored in the test harness from one valid synthetic artifact, with hashes recomputed for structural attacks so corruption checks do not hide schema failures. Exercise deliberately small caller limits for rows, columns, nnz, sources, bytes, and JSON depth. No malicious internet samples or external writes. Report which cases passed and retain failures; do not describe finite cases as complete security coverage.

## Evidence discipline

Create SHA-256 manifests for this protocol, exact fixture/oracle/tests, schema addendum and independent reader before recording their respective candidate results. Changes remain append-only in revision notes, with old manifests retained. Run reference tests before candidate compatibility tests. Record tool/interpreter/dependency versions, exact commands, return codes and observed duration where available. Full repository tests must be run at completion; independent checks do not replace them. Stop only after the agreed tests pass or a concrete blocker is reported; do not hide failed attempts. Resource budgets are admission limits, not an interpreter/RSS guarantee.
