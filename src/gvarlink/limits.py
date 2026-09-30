"""Input admission limits. These are not an operating-system memory sandbox."""
from dataclasses import dataclass, fields
from .errors import FormatError, LimitError

@dataclass(frozen=True)
class Limits:
    max_header_bytes: int = 1_048_576
    max_file_bytes: int = 67_108_864
    max_rows: int = 100_000
    max_coordinates: int = 200_000
    max_nnz: int = 2_000_000
    max_blocks: int = 1_024
    max_rank: int = 8
    max_json_depth: int = 16

    def __post_init__(self):
        for f in fields(self):
            value = getattr(self, f.name)
            if type(value) is not int or value < 0:
                raise FormatError(f'{f.name} must be a nonnegative integer')
            if value > f.default:
                raise LimitError(f'{f.name} exceeds hard ceiling {f.default}')


def checked_int(value, name, maximum, minimum=0):
    if type(value) is not int or value < minimum:
        raise FormatError(f'{name} must be an integer >= {minimum}')
    if value > maximum:
        raise LimitError(f'{name} exceeds {maximum}')
    return value


def shape_size(shape, name, maximum, rank, *, source=False):
    if not isinstance(shape, (list, tuple)):
        raise FormatError(f'{name} must be a list or tuple')
    if len(shape) > rank:
        raise LimitError(f'{name} rank exceeds {rank}')
    # Validate every dimension before multiplying (even after a zero dimension).
    dims = tuple(checked_int(x, name, maximum, 1 if source else 0) for x in shape)
    total = 1
    for dim in dims:
        total *= dim
        if total > maximum:
            raise LimitError(f'{name} product exceeds {maximum}')
    if total > maximum:
        raise LimitError(f'{name} product exceeds {maximum}')
    return dims, total
