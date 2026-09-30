"""Apply the independent rehashed structural corpus to the candidate public reader."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import gvarlink as gl
import test_reference_reader as reference
import test_text_contract as text_contract

HERE=Path(__file__).resolve().parent


def read_candidate(path,*,limits=None):
    rename={'max_latents':'max_coordinates','max_sources':'max_blocks','max_depth':'max_json_depth'}
    changes={rename.get(key,key):value for key,value in (limits or {}).items()}
    return gl.read(path,limits=gl.Limits(**changes))


class CandidateCorpus(reference.ReferenceReaderTests):
    @classmethod
    def setUpClass(cls):
        cls.reader_path=HERE/'reference_reader.py'
        cls.r=SimpleNamespace(read=read_candidate,InvalidArtifact=gl.GVarLinkError)

    test_refined_text_contract=text_contract.TextContractTests.test_refined_text_contract

    def test_production_small_limits(self):
        h,a=reference.original();blob=reference.encode(h,a)
        for field,value in [('max_file_bytes',len(blob)-1),('max_header_bytes',10),('max_rows',1),('max_latents',1),('max_nnz',2),('max_sources',0),('max_rank',0),('max_depth',1)]:
            with self.subTest(field=field),self.assertRaises(gl.GVarLinkError):
                self.read_blob(blob,limits={field:value})
        with self.assertRaises(gl.GVarLinkError):
            self.read_blob(blob,limits={'max_rows':100001})


class RecordingResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.cases=[]
    def addSubTest(self,test,subtest,error):
        super().addSubTest(test,subtest,error)
        self.cases.append({'test':test._testMethodName,'case':str(subtest),'passed':error is None})


if __name__=='__main__':
    names=['test_rejects_rehashed_hostile_metadata','test_rejects_duplicate_noncanonical_and_large_integer_json',
           'test_rejects_rehashed_bad_csr_and_nonfinite','test_rejects_corruption_truncation_trailing',
           'test_nonregular_symlink_and_fifo_rejected','test_refined_text_contract','test_production_small_limits']
    suite=unittest.TestSuite(CandidateCorpus(name) for name in names)
    result=unittest.TextTestRunner(verbosity=2,resultclass=RecordingResult).run(suite)
    report={'successful':result.wasSuccessful(),'test_methods':result.testsRun,'subcases':result.cases,
            'failures':[(str(test),trace) for test,trace in result.failures],
            'errors':[(str(test),trace) for test,trace in result.errors]}
    destination=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'results'/'production-corpus.json'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
