"""Independent identity and transactional-registration checks via public API."""
from dataclasses import replace
import json
from pathlib import Path
import sys
import unittest

import gvar as gv
import numpy as np
import gvarlink as gl

HERE=Path(__file__).resolve().parent
UUID='55555555-5555-4555-8555-555555555555'


def source():
    return gl.Source.create('same label',[2],'ordered standardized coordinates x0,x1',uuid=UUID)


def artifact(sources,indices=(0,),data=(2.,)):
    return gl.Artifact.from_arrays([5.],[0,len(indices)],list(indices),list(data),sources,shape=[1],unit='count',interpretation='affine')


class IdentityTests(unittest.TestCase):
    def test_equal_labels_values_different_uuid_remain_independent(self):
        a=source();b=replace(a,uuid='66666666-6666-4666-8666-666666666666')
        c=gl.Context([]);x=c.restore(artifact([a]));y=c.restore(artifact([b]))
        self.assertEqual(float(gv.var(x[0]-y[0])),8.)
        self.assertEqual(float(gv.cov(x[0],y[0])),0.)

    def test_labels_can_differ_but_shared_definition_cancels(self):
        a=source();b=replace(a,label='human-readable alias')
        c=gl.Context([]);x=c.restore(artifact([a]));y=c.restore(artifact([b]))
        self.assertEqual(float(gv.var(x[0]-y[0])),0.)
        self.assertEqual(float(gv.cov(x[0],y[0])),4.)

    def test_same_uuid_definition_changes_reject_transactionally(self):
        a=source();new=replace(a,uuid='77777777-7777-4777-8777-777777777777')
        candidates=[replace(a,revision='2'),replace(a,shape=(1,2)),replace(a,description='ordered standardized coordinates x1,x0')]
        for bad in candidates:
            with self.subTest(basis=bad.basis):
                c=gl.Context([a]);before=c.sources;primary=c.primary(a).copy()
                # A new block appears before a later conflicting declaration.
                with self.assertRaises(gl.SourceConflictError):
                    c.restore(artifact([new,bad]))
                self.assertEqual(c.sources,before)
                np.testing.assert_array_equal(gv.var(c.primary(a)-primary),[0.,0.])

    def test_whole_blocks_reorder_without_coordinate_reinterpretation(self):
        a=source();b=replace(a,uuid='88888888-8888-4888-8888-888888888888')
        c=gl.Context([b,a]);value=c.restore(artifact([a,b],indices=(0,3),data=(2.,-3.)))[0]
        self.assertEqual(float(gv.cov(value,c.primary(a)[0])),2.)
        self.assertEqual(float(gv.cov(value,c.primary(b)[1])),-3.)
        self.assertEqual(float(gv.var(value)),13.)

    def test_context_coordinate_cap_does_not_partial_register(self):
        a=source();b=replace(a,uuid='99999999-9999-4999-8999-999999999999')
        c=gl.Context([a],limits=gl.Limits(max_coordinates=2));before=c.sources
        with self.assertRaises(gl.LimitError):
            c.restore(artifact([b]))
        self.assertEqual(c.sources,before)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(IdentityTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    destination=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'results'/'identity.json'
    destination.write_text(json.dumps({'successful':result.wasSuccessful(),'test_methods':result.testsRun,'failures':[(str(t),e) for t,e in result.failures],'errors':[(str(t),e) for t,e in result.errors]},indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
