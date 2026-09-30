"""Original structural corpus; mutations are rehashed to exercise schema checks."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
CANON = lambda v: json.dumps(v, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('ascii')


def basis_hash(source):
    return hashlib.sha256(CANON({k: source[k] for k in ('revision', 'description', 'shape', 'model', 'order')})).hexdigest()


def original():
    source = {'uuid': '11111111-1111-4111-8111-111111111111', 'label': 'synthetic', 'revision': '1', 'description': 'x0,x1', 'shape': [2], 'model': 'independent-standard-normal-v1', 'order': 'C'}
    source['basis_hash'] = basis_hash(source)
    header = {'format': 'gvarlink', 'version': 1, 'shape': [2], 'unit': 'count', 'interpretation': 'affine', 'sources': [source], 'nnz': 3, 'payload_bytes': 88, 'arrays': {}}
    arrays = {'mean': struct.pack('<2d', 5, 7), 'indptr': struct.pack('<3Q', 0, 2, 3), 'indices': struct.pack('<3Q', 0, 1, 1), 'data': struct.pack('<3d', 2, -1, .5)}
    return header, arrays


def encode(header, arrays, raw_header=None):
    header = copy.deepcopy(header)
    header['arrays'] = {key: hashlib.sha256(value).hexdigest() for key, value in arrays.items()}
    encoded = CANON(header) if raw_header is None else raw_header(header)
    body = b'GVARLNK1' + struct.pack('<Q', len(encoded)) + encoded + b''.join(arrays[k] for k in ('mean', 'indptr', 'indices', 'data'))
    return body + hashlib.sha256(body).digest()


class ReferenceReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader_path = HERE / 'reference_reader.py'
        if cls.reader_path.exists():
            spec = importlib.util.spec_from_file_location('reference_reader', cls.reader_path)
            cls.r = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.r)

    def setUp(self):
        self.assertTrue(self.reader_path.exists(), 'independent data-only reader not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'fixture.gvl'

    def read_blob(self, blob, **kwargs):
        self.path.write_bytes(blob)
        return self.r.read(self.path, **kwargs)

    def test_original_read_and_identity(self):
        h, a = original()
        doc = self.read_blob(encode(h, a))
        self.assertEqual(doc['mean'], (5.0, 7.0))
        self.assertEqual(doc['indptr'], (0, 2, 3))
        self.assertEqual(doc['data'], (2.0, -1.0, .5))
        renamed = copy.deepcopy(doc)
        renamed['header']['sources'][0]['label'] = 'renamed'
        self.assertEqual(len(self.r.reconcile([doc, renamed])), 1)
        collision = copy.deepcopy(doc)
        collision['header']['sources'][0]['description'] = 'x1,x0'
        collision['header']['sources'][0]['basis_hash'] = basis_hash(collision['header']['sources'][0])
        with self.assertRaises(self.r.InvalidArtifact):
            self.r.reconcile([doc, collision])
        independent = copy.deepcopy(doc)
        independent['header']['sources'][0]['uuid'] = '22222222-2222-4222-8222-222222222222'
        self.assertEqual(len(self.r.reconcile([doc, independent])), 2)

    def test_rejects_rehashed_hostile_metadata(self):
        mutations = {
            'unknown_header': lambda h: h.update(extra=0),
            'version': lambda h: h.update(version=2),
            'boolean_version': lambda h: h.update(version=True),
            'boolean_shape': lambda h: h.update(shape=[True, 2]),
            'negative_shape': lambda h: h.update(shape=[-2]),
            'oversize_shape': lambda h: h.update(shape=[100001]),
            'shape_product': lambda h: h.update(shape=[100000,100000]),
            'too_many_dimensions': lambda h: h.update(shape=[1]*9),
            'negative_nnz': lambda h: h.update(nnz=-1),
            'boolean_nnz': lambda h: h.update(nnz=True),
            'too_many_nnz': lambda h: h.update(nnz=2000001),
            'wrong_payload': lambda h: h.update(payload_bytes=0),
            'wrong_interpretation': lambda h: h.update(interpretation='exact-nonlinear'),
            'long_string': lambda h: h.update(unit='x'*4097),
            'deep_json': lambda h: h.update(unit=[[[[[[[[[[[[[[[[['x']]]]]]]]]]]]]]]]]),
            'duplicate_uuid': lambda h: h['sources'].append(copy.deepcopy(h['sources'][0])),
            'source_unknown': lambda h: h['sources'][0].update(extra=0),
            'source_model': lambda h: h['sources'][0].update(model='pickle'),
            'source_order': lambda h: h['sources'][0].update(order='F'),
            'source_shape_zero': lambda h: h['sources'][0].update(shape=[0]),
            'source_shape_big': lambda h: h['sources'][0].update(shape=[200001]),
            'source_shape_boolean': lambda h: h['sources'][0].update(shape=[True]),
            'source_bad_uuid': lambda h: h['sources'][0].update(uuid='not-a-uuid'),
            'source_noncanonical_uuid': lambda h: h['sources'][0].update(uuid='11111111111141118111111111111111'),
            'source_bad_hash': lambda h: h['sources'][0].update(basis_hash='0'*64),
        }
        for name, mutate in mutations.items():
            with self.subTest(case=name):
                h, a = original()
                mutate(h)
                with self.assertRaises(self.r.InvalidArtifact):
                    self.read_blob(encode(h,a))

    def test_rejects_duplicate_noncanonical_and_large_integer_json(self):
        h,a = original()
        variants = [lambda h: CANON(h).replace(b'"version":1', b'"version":1,"version":1'), lambda h: json.dumps(h, sort_keys=True).encode(), lambda h: CANON(h).replace(b'"version":1', b'"version":123456789012345678901'), lambda h: CANON(h).replace(b'"version":1', b'"version":NaN')]
        for make in variants:
            with self.subTest(variant=repr(make)), self.assertRaises(self.r.InvalidArtifact):
                self.read_blob(encode(h,a,make))

    def test_rejects_rehashed_bad_csr_and_nonfinite(self):
        mutations = {
            'indptr_first': ('indptr','<3Q',(1,2,3)),
            'indptr_last': ('indptr','<3Q',(0,2,2)),
            'indptr_decreasing': ('indptr','<3Q',(0,4,3)),
            'duplicate_columns': ('indices','<3Q',(0,0,1)),
            'unsorted_columns': ('indices','<3Q',(1,0,1)),
            'outside_columns': ('indices','<3Q',(0,2,1)),
            'explicit_zero': ('data','<3d',(2,0,.5)),
            'negative_zero': ('data','<3d',(2,-0.,.5)),
            'nan_data': ('data','<3d',(2,float('nan'),.5)),
            'infinite_data': ('data','<3d',(2,float('inf'),.5)),
            'nan_mean': ('mean','<2d',(float('nan'),7)),
        }
        for name,(key,fmt,values) in mutations.items():
            with self.subTest(case=name):
                h,a = original(); a[key] = struct.pack(fmt,*values)
                with self.assertRaises(self.r.InvalidArtifact):
                    self.read_blob(encode(h,a))

    def test_rejects_corruption_truncation_trailing(self):
        h,a=original(); blob=encode(h,a)
        mutants = [b'BADMAGIC'+blob[8:], blob[:8]+struct.pack('<Q',2**64-1)+blob[16:], blob[:-1], blob+b'0', blob[:32]+bytes([blob[32]^1])+blob[33:], blob[:-40]+bytes([blob[-40]^1])+blob[-39:], blob[:-1]+bytes([blob[-1]^1])]
        for number,bad in enumerate(mutants):
            with self.subTest(case=number), self.assertRaises(self.r.InvalidArtifact):
                self.read_blob(bad)
        h,a=original()
        bad=encode(h,a,lambda h: CANON(dict(h, arrays=dict(h['arrays'],mean='0'*64))))
        with self.assertRaises(self.r.InvalidArtifact):
            self.read_blob(bad)

    def test_small_limits_and_no_hard_limit_raise(self):
        h,a=original(); blob=encode(h,a)
        for field,value in [('max_file_bytes',len(blob)-1),('max_header_bytes',10),('max_rows',1),('max_latents',1),('max_nnz',2),('max_sources',0),('max_rank',0),('max_depth',1),('max_string_chars',3)]:
            with self.subTest(field=field), self.assertRaises(self.r.InvalidArtifact):
                self.read_blob(blob, limits={field:value})
        with self.assertRaises(self.r.InvalidArtifact):
            self.read_blob(blob,limits={'max_rows':100001})

    def test_empty_and_scalar_outputs(self):
        h,a=original(); h.update(shape=[0],nnz=0,payload_bytes=8)
        a={'mean':b'','indptr':struct.pack('<Q',0),'indices':b'','data':b''}
        self.assertEqual(self.read_blob(encode(h,a))['mean'],())
        h.update(shape=[],nnz=0,payload_bytes=24)
        a['mean']=struct.pack('<d',3);a['indptr']=struct.pack('<2Q',0,0)
        self.assertEqual(self.read_blob(encode(h,a))['mean'],(3.,))

    def test_nonregular_symlink_and_fifo_rejected(self):
        with self.assertRaises(self.r.InvalidArtifact):
            self.r.read(Path(self.tmp.name))
        h,a=original(); self.path.write_bytes(encode(h,a))
        link=Path(self.tmp.name)/'link';link.symlink_to(self.path)
        with self.assertRaises(self.r.InvalidArtifact):
            self.r.read(link)
        if hasattr(os,'mkfifo'):
            fifo=Path(self.tmp.name)/'pipe';os.mkfifo(fifo)
            with self.assertRaises(self.r.InvalidArtifact):
                self.r.read(fifo)

if __name__ == '__main__':
    unittest.main()
