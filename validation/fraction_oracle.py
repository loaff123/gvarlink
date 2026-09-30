"""Independent exact affine/matrix oracle; only Python standard library.

This intentionally imports neither the production transport nor a numerical engine.
"""
from fractions import Fraction
import json
from pathlib import Path


def _dot(left, right):
    return sum((value * right.get(key, 0) for key, value in left.items()), Fraction(0))


def covariance(left, right):
    return [[_dot(a, b) for b in right] for a in left]


def evaluate_fixture(path):
    model = json.loads(Path(path).read_text(encoding='utf-8'))
    branches = {}
    for name, branch in model['branches'].items():
        rows = []
        for factor_row in branch['factors']:
            row = {}
            for source_name, coefficients in factor_row.items():
                source_uuid = model['sources'][source_name]['uuid']
                row.update({(source_uuid, i): Fraction(value) for i, value in enumerate(coefficients) if Fraction(value)})
            rows.append(row)
        branches[name] = (list(map(Fraction, branch['means'])), rows)
    a_means, a = branches['a']
    b_means, b = branches['b']
    difference = []
    for left, right in zip(a, b):
        keys = left.keys() | right.keys()
        difference.append({key: left.get(key, 0) - right.get(key, 0) for key in keys})
    dcov = covariance(difference, difference)
    return {
        'a_means': a_means,
        'b_means': b_means,
        'a_covariance': covariance(a, a),
        'b_covariance': covariance(b, b),
        'cross_covariance': covariance(a, b),
        'joint_covariance': covariance(a + b, a + b),
        'contrast_means': [x - y for x, y in zip(a_means, b_means)],
        'contrast_covariance': dcov,
        'total_contrast_variance': sum((sum(row) for row in dcov), Fraction(0)),
    }


def encode_fractions(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, list):
        return [encode_fractions(item) for item in value]
    if isinstance(value, dict):
        return {key: encode_fractions(item) for key, item in value.items()}
    return value


if __name__ == '__main__':
    import sys
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / 'fixtures' / 'branch_model.json'
    print(json.dumps(encode_fractions(evaluate_fixture(path)), sort_keys=True, indent=2))
