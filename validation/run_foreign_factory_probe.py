"""Numerical regression discovered by independent review, 2026-09-30.

Derivative coordinate integers are local to a gvar covariance factory.
"""
import json
from pathlib import Path
import sys
import gvar as gv
import gvarlink as gl

s=gl.Source.create('owned',[1],'owned standardized coordinate',uuid='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa')
context=gl.Context([s])
owned=context.primary(s)[0]
foreign=gv.gvar_factory()(0,3)
report={'owned_derivative_indices':gv.disassemble([owned])[0][1].indices().tolist(),
        'foreign_derivative_indices':gv.disassemble([foreign])[0][1].indices().tolist(),
        'foreign_variance':float(gv.var(foreign))}
try:
    artifact=context.pack([foreign])
except gl.DependencyError as error:
    report.update(passed=True,rejected_as='DependencyError',message=str(error))
else:
    restored=context.restore(artifact)[0]
    report.update(passed=False,accepted_foreign_dependency=True,serialized_coefficients=artifact.data.tolist(),restored_variance=float(gv.var(restored)))
output=Path(sys.argv[1])
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
