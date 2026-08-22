# engine/src/godot_dnd_engine/errors.py
"""Domain exceptions raised by the headless simulation engine."""


class EngineError(Exception):
    """Base class for deterministic engine errors."""


class ValidationError(EngineError, ValueError):
    """Raised when untrusted or malformed input fails validation."""


class SequenceError(EngineError):
    """Raised when an event or command does not match expected sequence state."""


class UnsupportedCommandError(EngineError):
    """Raised when a command type is not implemented by this engine version."""
