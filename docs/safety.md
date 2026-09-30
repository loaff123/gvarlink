# Input safety and trust boundaries

GVarLink is experimental. Its parser deliberately has a small, closed input language, but test coverage and an independent agent review are not proof of production security. A broader independent security review has not been completed. Successful bounded-format tests and numerical review are reported separately.

## What the reader checks

- Regular local file only, with final symlinks/devices/FIFOs rejected. It lstat-checks before opening and fstat-checks the same descriptor, using nonblocking/no-follow flags when available
- Hard file/header ceilings and exact length arithmetic before reading the payload
- JSON nesting depth before parsing; bounded integer tokens, duplicate-key rejection, no floating metadata values, canonical ASCII representation, bounded strings and closed key sets
- Supported schema/model/order; recomputed basis fingerprints; canonical UUIDs; no duplicate source UUIDs; bounded declared dimension products and source union
- Fixed raw numeric buffers only: no compression, archives, NPY headers, arbitrary dtype, pickle, code import, callback or external URL lookup
- Complete-file and per-buffer SHA-256, then finite values, CSR pointer bounds, strictly sorted in-range columns and nonzero coefficients

The opened descriptor is authoritative. There is no extraction or remote fetching. Ancestor directory symlinks are ordinary filesystem path resolution; this is not a jailed-filesystem API. Concurrent same-user mutation, hostile Python objects already executing in the process, malicious gvar monkeypatches, compromised dependencies/kernel, and authenticity are outside the threat model. Checksums detect accidental modification; a forger can recompute them and lie about source identity.

## Resources

Limits reject input-driven declarations before numeric payload allocation. They are conservative admission rules, not exact working-memory accounting. JSON objects, payload byte storage, immutable copies, gvar objects, native libraries and Python overhead all consume extra memory. `load_many` retains admitted artifacts during restoration. Use OS/container limits if hard CPU/RSS enforcement is needed. Later `gv.evalcov` can allocate a dense square covariance matrix; GVarLink does not intercept it. Finite coefficients can still yield overflowing squared/cross products.

For public in-memory APIs, the caller owns the input arrays already; supported input shapes/types are bounded before package copies. gvar sparse derivative extraction may allocate arrays based on the caller’s existing GVar representation; the nnz limit bounds GVarLink’s own subsequent row-entry copies. The package does not execute untrusted serialized operations. Context restore budgets are cumulative and sources are not released individually. Context is not thread-safe.

## Writes and failures

Writer snapshots validated arrays, writes a sibling tempfile, flushes and fsyncs it, then hard-links to publish without overwrite or uses os.replace when overwrite=True. Failures clean the staging name. There is no unsafe fallback on a filesystem that lacks atomic hard links. On overwrite, destination must initially be a regular file; replacement affects the name, not a symlink target. Directory fsync/crash durability is not promised, and unusual/network filesystem behavior requires separate testing. A success is atomic publication under supported local filesystem semantics, not a guarantee against power loss.

## Scientific trust

Independent standardized source blocks, UUID reuse, coordinate order and affine interpretation are declarations from a producer. Neither hashes nor equality of values can verify them. Opposite signed observation loadings are allowed and meaningful under the same declared latent basis. Rotating/permuting coordinates is not an automatic equivalence: declare a new source or use an explicitly reviewed conversion outside v1. Keep application edges/masks/coverage with the result, and verify those separately.

No passwords, API keys, accounts or network service are required by this format or CLI. Only original synthetic fixtures are bundled.
