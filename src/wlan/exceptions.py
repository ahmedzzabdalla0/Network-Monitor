"""Custom exceptions for network clients."""


class NetworkClientError(Exception):
    """Base exception for all network client-related errors."""
    pass


class EncryptionError(NetworkClientError):
    """Raised when encryption/decryption operations fail."""
    pass


class AuthenticationError(NetworkClientError):
    """Raised when login or authentication fails."""
    pass


class SessionError(NetworkClientError):
    """Raised when session-related operations fail."""
    pass


class APIError(NetworkClientError):
    """Raised when API requests fail or return unexpected data."""
    pass


class DataParsingError(NetworkClientError):
    """Raised when response data cannot be parsed correctly."""
    pass
