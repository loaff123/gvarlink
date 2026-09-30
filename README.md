# GVarLink

**Keep explicitly shared gvar uncertainty sources connected across separate files and processes.**

GVarLink is a small, experimental persistence companion to [gvar](https://gvar.readthedocs.io/). gvar does the uncertainty arithmetic. GVarLink adds declared source identities, a closed numeric-only file format, bounded input admission, and reconstruction in one shared context.

It is useful when two independent jobs share a calibration or background measurement, save results separately, and later need a contrast that retains the cross-covariance. It is **not** a new covariance engine, an authentication system, or a production-security certification.

[Explore the static source-identity demo](https://gvarlink-source-identity.lyczz.chatgpt.site) · [CI runs](https://github.com/loaff123/gvarlink/actions)

The browser demo illustrates the declared-identity model; it does not run Python or validate uploaded files.

## Start in one minute

Python 3.11 or later. Install from a source checkout:

```sh
python -m pip install .
gvarlink demo ./my-demo
gvarlink inspect ./my-demo/branch-1.gvl
gvarlink verify ./my-demo/branch-1.gvl ./my-demo/branch-2.gvl
```

The demo launches two writer processes and a fresh merge process. A shared source cancels with variance **0**; distinct sources with equal labels and values have contrast variance **8**. The output directory must not already exist. No network or account is needed after installation.

## Ordinary gvar arithmetic, explicit identity

```python
import gvar as gv
from gvarlink import Source, Context, write, load_many

# Generate once for this physical measurement; distribute this declaration
# deliberately to jobs that truly share it. Labels do not identify sources.
background = Source.create("background", (1,), "one shared measurement")
ctx = Context([background])
z = ctx.primary(background)[0]
write(ctx.pack([10 + 2*z], unit="counts", interpretation="affine"), "a.gvl")
write(ctx.pack([12 + 2*z], unit="counts", interpretation="affine"), "b.gvl")

# A fresh process can run this without retaining the original Context.
shared_context, (a, b) = load_many(["a.gvl", "b.gvl"])
assert gv.mean(b[0] - a[0]) == 2
assert gv.var(b[0] - a[0]) == 0
```

For independently launched jobs, serialize `source.to_dict()` in your own agreed configuration, then use `Source.from_dict(...)`. The included demo instead transports declarations inside an empty numeric registry artifact. A **new** `Source.create(...)` generates a fresh UUID even if the label, shape, and numbers match. Reuse a UUID only when the source is scientifically the same.

## What is preserved

- Means and sparse derivatives against declared independent standard-normal coordinates
- Shared UUID/basis identity across files, and independence of different UUIDs
- Signed loadings and arbitrary whole-source-block order
- Original output shape, a unit string, and an explicit affine/linearized interpretation
- Native gvar outputs, including constant rows; ordinary `gv.evalcov` works after restore

Same UUID with changed revision, description, shape, coordinate order, or model fails closed. Display labels may differ. An unknown nonzero gvar dependency or a foreign gvar covariance factory is rejected. The adapter pins gvar **13.1.10** because its sparse extraction interfaces are version-sensitive.

## What it does not promise

- UUIDs and hashes do not verify a producer or physical identity
- Different source UUIDs declare mutually uncorrelated blocks; software cannot establish that scientifically
- `interpretation="affine"` is a caller assertion. The conservative default is `"linearized"`; expression history cannot prove affine origin
- Units are descriptive strings. Axes, edges, masks, and coverage need their own application metadata; see the [complete rebin example](examples/rebin_counts.py)
- No factor rotations, coordinate-basis migration, correlated unknown blocks, arbitrary object deserialization, recipe execution, or exact nonlinear moments
- Input admission limits do not cap Python/gvar process RSS or numerical work performed later by callers. Finite factors can overflow a later covariance calculation

## Format and limits

A `.gvl` file is one uncompressed regular file: fixed magic and header length, canonical ASCII JSON, four fixed little-endian numeric buffers, and SHA-256 integrity checks. There is no ZIP/NPY reader, pickle, embedded path, external reference, or selectable dtype. The reader validates the declared shape, byte lengths, source union, checksums, finite values and canonical CSR representation.

Defaults and hard ceilings: 64 MiB wire bytes, 1 MiB header, 100,000 output rows, 200,000 latent coordinates, 2,000,000 nonzeros, 1,024 source blocks, rank 8, JSON depth 16. `Limits(...)` can lower them. `load_many` applies aggregate rows/nonzeros/wire bytes and union-source limits before decoding an inadmissible next payload. `Context.restore` budgets are cumulative. This deliberately does not cover every problem size from the predecessor feasibility study.

Writes stage a sibling file and use atomic create-if-absent publication; existing files are preserved unless `overwrite=True`. Filesystems without safe hard-link publication fail explicitly. [Full format](docs/format-v1.md) · [safety and trust boundaries](docs/safety.md) · [API](docs/api.md)

## Choose existing tools first

If results are available together, gvar's native joint serialization may be all you need. Its documented contract preserves relationships **inside** the saved collection; separate native files are not a shared-source registry. [RMEllipse](https://pages.nist.gov/rmellipse-ipages/) already provides shared uncertainty-mechanism identity and HDF5 persistence. GVarLink does not claim to invent source identity or restart-preserving correlations.

An executed synthetic feasibility study found gvar, CoMet and Astropy capable of the numerical workflow through their respective supported/custom routes. That evidence stopped development of a proposed standalone covariance engine. This component keeps the narrow interoperability task. No CoMet adapter is claimed here. [Comparison and evidence](docs/comparison.md)

## Validation and development

```sh
python -m pip install '.[test]'
python -m pytest -q
python -m unittest discover -s validation -p 'test_*.py'
python validation/run_independent_validation.py
python examples/rebin_counts.py ./rebin-example
python -m build
```

Independent exact Fraction and matrix references, fresh-process writers/rejoin, an independently implemented standard-library reader, malformed-file rejection tests, native gvar parity, and review-found regressions are included. These are exposed development checks, not a holdout, domain-expert approval, adoption evidence, or academic-impact claim. See [validation scope/results](docs/validation.md).

## License

GPL-3.0-or-later. Dependencies retain their licenses; no dependency binaries or copied numerical implementations are bundled. See [THIRD_PARTY.md](THIRD_PARTY.md). This is an engineering license inventory, not legal clearance.
