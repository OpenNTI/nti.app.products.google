__import__('pkg_resources').declare_namespace(__name__)  # pragma: no cover


class OAuthException(Exception):
    """
    Raised when an error occurs authorizing via OAuth
    """

class OAuthError(OAuthException):
    """
    Raised when the oauth provider returns an error from the authorization
    process.
    """

class OAuthInvalidRequest(OAuthException):
    """
    Raised when the oauth authorization process receives a bad request.
    """
