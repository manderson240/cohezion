"""Error definitions for Kyutai MCP Server."""


class KyutaiError(Exception):
    """Base exception for Kyutai MCP errors."""

    pass


class ConfigError(KyutaiError):
    """Configuration error."""

    pass


class ServiceError(KyutaiError):
    """Service runtime error."""

    pass


class ModelError(KyutaiError):
    """Model-specific error."""

    pass


class AudioError(KyutaiError):
    """Audio processing error."""

    pass


class VoiceError(KyutaiError):
    """Voice-related error."""

    pass
