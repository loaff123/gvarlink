"""Typed failure modes; failed reads never return partial artifacts."""

class GVarLinkError(ValueError):
    """Base class for an invalid or unsupported operation."""

class FormatError(GVarLinkError):
    """A declaration or artifact violates the closed contract."""

class LimitError(GVarLinkError):
    """Admission would exceed a caller limit or hard ceiling."""

class SourceConflictError(GVarLinkError):
    """One UUID refers to different latent basis declarations."""

class DependencyError(GVarLinkError):
    """Unsupported gvar version or unregistered stochastic dependency."""
