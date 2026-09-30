"""Context lifetime regression: external gvar factory switching must not remap IDs."""
import json
from pathlib import Path
import sys
import gvar as gv
import gvarlink as gl

one=gl.Source.create('one',[1],'coordinate one',uuid='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb')
two=gl.Source.create('two',[1],'coordinate two',uuid='cccccccc-cccc-4ccc-8ccc-cccccccccccc')
context=gl.Context([one]);owned=context.primary(one)[0]
report={}
gv.switch_gvar()
try:
    added=context.restore(gl.Artifact.from_arrays([0.],[0,1],[0],[1.],[two]))[0]
    artifact=context.pack([owned,added])
    report={'serialized_indices':artifact.indices.tolist(),'expected_indices':[0,1],
            'same_covariance_world':owned.cov is added.cov}
    report['passed']=report['serialized_indices']==[0,1] and report['same_covariance_world']
except Exception as error:
    report={'passed':False,'error_type':type(error).__name__,'error':str(error)}
finally:
    gv.restore_gvar()
Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
