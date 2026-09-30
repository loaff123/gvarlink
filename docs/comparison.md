# Why this component is deliberately small

A preceding original synthetic CPU experiment tested two detector reductions with independently noisy exposures, shared dark counts and eight calibration modes. It used separately authored exact Fraction/direct-coefficient oracles and a frozen numerical tolerance. Mature packages already handled the numerical problem; the planned standalone CovWeave engine was stopped.

| Route | Observed capability in that experiment | Important scope |
|---|---|---|
| gvar 13.1.10 | Full native numerical job; explicit source-registry transport proof passed fresh-process recombination | Numerical algebra belongs to gvar; cross-file registry was authored adapter code |
| RMEllipse 0.5.1 | Native shared-mechanism HDF5 save/restart/rejoin passed the small exact case | Source identity and persistence are existing functionality; no novelty claim here |
| CoMet/punpy 1.1.0 + obsarray 1.0.3 | Full numerical contract with explicit signed-source/chunk adapter; small persistence passed | Custom orchestration was material; no equivalent automatic speed comparison |
| Astropy 7.2.0 | Full numerical contract with explicit compact factors and bounded covariance chunks | No general shared-source persistence demonstrated in that test |
| gprob, physure | Selected supported small routes passed | Route-specific restrictions did not disprove every decomposition |
| ScippUncertainty/ESSreduce | Monte Carlo/conservative-bound routes were examined | Different valid output contracts; not exact-covariance failures |

This package does not repeat those performance rankings or claim a new covariance algorithm. It targets a gvar user's narrow need for separate-file identity and a closed data-only interchange boundary. If joint native gvar storage is sufficient, prefer it. If your uncertainty model is already in RMEllipse, use its existing native mechanism persistence. CoMet interoperability is deferred rather than adding an unvalidated promise.

Native gvar stores within-collection correlations and intentionally does not reconnect independently saved collections by a portable external registry. That is a documented contract, not a numerical bug. GVarLink requires callers to establish explicit source declarations up front; it cannot reconstruct missing scientific identities from an arbitrary native file.

Primary sources:
- [gvar storage contract](https://gvar.readthedocs.io/en/latest/overview.html#storing-gvar-gvars-for-later-use)
- [gvar public APIs and covariance factories](https://gvar.readthedocs.io/en/latest/gvar.html)
- [RME shared mechanisms](https://pages.nist.gov/rmellipse-ipages/v0.5.1/auto_examples/grp0_RME_gettingstarted/plot_e01_basic_uncertainty_analysis.html)
- [punpy memory and speed options](https://punpy.readthedocs.io/en/latest/content/punpy_memory_and_speed.html)
- [Astropy Covariance](https://docs.astropy.org/en/stable/api/astropy.nddata.Covariance.html)

No real-instrument data, external user adoption, human domain review, journal result or academic impact is established by these synthetic checks. A source-basis hash is an identity contract, not new scientific mathematics.
