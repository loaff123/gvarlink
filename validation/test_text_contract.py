"""Schema refinement agreed after first reader freeze; no mathematical change."""
import copy
import unittest
from test_reference_reader import ReferenceReaderTests, original, encode, basis_hash


class TextContractTests(ReferenceReaderTests):
    def test_refined_text_contract(self):
        cases=[('unit','a'*1025),('unit','line\nbreak'),('unit','\ud800'),('label','a'*257),('description',''),('description','a'*1025),('revision',''),('revision','a'*129)]
        for key,value in cases:
            with self.subTest(field=key,value_length=len(value)):
                h,a=original()
                if key=='unit':
                    h[key]=value
                else:
                    h['sources'][0][key]=value
                    h['sources'][0]['basis_hash']=basis_hash(h['sources'][0])
                with self.assertRaises(self.r.InvalidArtifact):
                    self.read_blob(encode(h,a))


if __name__=='__main__':
    unittest.main()
