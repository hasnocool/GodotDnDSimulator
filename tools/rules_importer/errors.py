# tools/rules_importer/errors.py
"""Rules-import pipeline exceptions."""


class RulesImportError(Exception):
    """Base class for deterministic rules import failures."""


class SourcePolicyError(RulesImportError):
    """Raised when a source is unknown, disallowed, or violates its policy."""


class SourceChangedError(RulesImportError):
    """Raised when a pinned upstream source changes unexpectedly."""


class ExtractionError(RulesImportError):
    """Raised when source extraction cannot produce a valid intermediate form."""


class CompilationError(RulesImportError):
    """Raised when normalized content cannot be compiled deterministically."""
