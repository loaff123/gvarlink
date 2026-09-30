# Dependency attribution and license inventory

Original GVarLink source and original synthetic examples: GPL-3.0-or-later.

- [gvar](https://github.com/gplepage/gvar), G. Peter Lepage and contributors: installed13.1.10 metadata declares GPL-3.0+; installed LICENSE.txt is GPLv3. Exact dependency pin due to sparse serialization API sensitivity
- [NumPy](https://numpy.org/), NumPy developers: BSD-3-Clause primary project license; binary distributions have additional bundled-library notices
- [SciPy](https://scipy.org/), SciPy developers: BSD-3-Clause primary project license; gvar dependency and binary distributions have their own bundled-library notices
- [mpmath](https://mpmath.org/): BSD-3-Clause; gvar dependency
- [pytest](https://pytest.org/): MIT; development only
- [build](https://build.pypa.io/): MIT; development only
- [setuptools](https://setuptools.pypa.io/): MIT; build backend

No dependency implementation code or binary is vendored in this repository or its source archive. Dependency installers obtain their own distributions and notices. The copied LICENSE text is the standard GNU GPL license, not gvar program code. This inventory is based on installed distribution metadata/licenses and official project sources; it is not a legal opinion or a claim that every downstream distribution arrangement has been cleared.

The predecessor experiment and this package credit native gvar arithmetic and RMEllipse’s existing source-preserving restart. No endorsement by those projects, NIST, OpenAI, or any institution is implied.
