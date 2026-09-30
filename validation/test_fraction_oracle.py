import importlib.util
from fractions import Fraction
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent

class ExactOracleTests(unittest.TestCase):
    def test_original_affine_model_has_frozen_hand_checks(self):
        path = HERE / 'fraction_oracle.py'
        self.assertTrue(path.exists(), 'independent Fraction oracle has not been implemented')
        spec = importlib.util.spec_from_file_location('fraction_oracle', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        answer = module.evaluate_fixture(HERE / 'fixtures' / 'branch_model.json')
        self.assertEqual(answer['contrast_covariance'][0][0], Fraction(0))
        self.assertEqual(answer['contrast_covariance'][1][1], Fraction(8))
        self.assertEqual(answer['cross_covariance'][2][2], Fraction(-1))
        self.assertEqual(answer['a_covariance'][2][2], Fraction(61, 4))
        self.assertEqual(answer['b_covariance'][2][2], Fraction(113, 16))
        self.assertEqual(answer['contrast_covariance'][2][2], Fraction(389, 16))
        self.assertEqual(answer['a_means'], list(map(Fraction, [5, 7, -3])))
        self.assertEqual(answer['contrast_means'], list(map(Fraction, [0, 0, -7])))
        self.assertEqual(answer['cross_covariance'][0][2], Fraction(-9, 2))
        self.assertEqual(answer['total_contrast_variance'], Fraction(613, 16))

if __name__ == '__main__':
    unittest.main()
