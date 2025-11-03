"""Custom exceptions for Zyxel router client."""


class ZyxelRouterError(Exception):
    """Base exception for all Zyxel router-related errors."""
    pass


class EncryptionError(ZyxelRouterError):
    """Raised when encryption/decryption operations fail."""
    pass


class AuthenticationError(ZyxelRouterError):
    """Raised when login or authentication fails."""
    pass


class SessionError(ZyxelRouterError):
    """Raised when session-related operations fail."""
    pass


class APIError(ZyxelRouterError):
    """Raised when API requests fail or return unexpected data."""
    pass


class DataParsingError(ZyxelRouterError):
    """Raised when response data cannot be parsed correctly."""
    pass
