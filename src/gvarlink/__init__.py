"""GVarLink: explicit identity persistence around gvar, not a numerical engine."""
from .errors import GVarLinkError, FormatError, LimitError, SourceConflictError, DependencyError
from .limits import Limits
from .model import Source, Artifact

__version__ = '0.1.0'
from .format import read, write, inspect
from .adapter import Context, load_many
