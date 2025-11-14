"""Error handling utilities for GitLab MCP Server."""

from typing import Any, Callable, TypeVar
from functools import wraps
import logging
import httpx

# Type variable for generic function signatures
F = TypeVar('F', bound=Callable[..., Any])

# Logger for error tracking
logger = logging.getLogger(__name__)


def format_http_error(error: httpx.HTTPStatusError) -> dict[str, Any]:
    """Format HTTP status errors into standardized error responses.

    Maps HTTP status codes to specific error types:
    - 401: AuthenticationError
    - 403: AuthorizationError
    - 404: NotFoundError
    - 422: ValidationError
    - 429: RateLimitError
    - 5xx: ServerError

    Args:
        error: HTTPStatusError from httpx

    Returns:
        dict: Standardized error response with fields:
            - error: True
            - error_type: Specific error type
            - message: Human-readable error message
            - details: Additional error details
            - action: Suggested action to resolve the error
    """
    # pylint: disable=too-many-return-statements
    status_code = error.response.status_code

    # Extract response body if available
    try:
        response_body = error.response.json()
        details = response_body.get("message", error.response.text)
    except Exception:  # pylint: disable=broad-exception-caught
        # JSON decode error, missing key, missing attribute, or other JSON parsing issues
        details = error.response.text

    # Map status codes to error types and messages
    if status_code == 401:
        return {
            "error": True,
            "error_type": "AuthenticationError",
            "message": "Authentication failed",
            "details": details,
            "action": (
                "Check your GITLAB_TOKEN. Generate a new token at "
                "https://gitlab.com/-/profile/personal_access_tokens"
            )
        }
    if status_code == 403:
        return {
            "error": True,
            "error_type": "AuthorizationError",
            "message": "Access forbidden",
            "details": details,
            "action": (
                "Your token does not have permission for this operation. "
                "Check token scopes."
            )
        }
    if status_code == 404:
        return {
            "error": True,
            "error_type": "NotFoundError",
            "message": "Resource not found",
            "details": details,
            "action": "Verify the resource ID or path is correct."
        }
    if status_code == 422:
        return {
            "error": True,
            "error_type": "ValidationError",
            "message": "Invalid request parameters",
            "details": details,
            "action": "Check the request parameters and try again."
        }
    if status_code == 429:
        return {
            "error": True,
            "error_type": "RateLimitError",
            "message": "Rate limit exceeded",
            "details": details,
            "action": "Wait before making more requests. Check rate limit headers."
        }
    if 500 <= status_code < 600:
        return {
            "error": True,
            "error_type": "ServerError",
            "message": f"GitLab server error ({status_code})",
            "details": details,
            "action": (
                "The GitLab server encountered an error. Try again later or "
                "contact your GitLab administrator."
            )
        }
    return {
        "error": True,
        "error_type": "HTTPError",
        "message": f"HTTP error {status_code}",
        "details": details,
        "action": "Check the GitLab API documentation for this endpoint."
    }


def format_connection_error(error: httpx.ConnectError) -> dict[str, Any]:
    """Format connection errors into standardized error responses.

    Args:
        error: ConnectError from httpx

    Returns:
        dict: Standardized error response
    """
    return {
        "error": True,
        "error_type": "ConnectionError",
        "message": "Failed to connect to GitLab",
        "details": str(error),
        "action": (
            "Check your network connection and GITLAB_URL setting. "
            "Verify the GitLab instance is accessible."
        )
    }


def format_timeout_error(error: httpx.TimeoutException) -> dict[str, Any]:
    """Format timeout errors into standardized error responses.

    Args:
        error: TimeoutException from httpx

    Returns:
        dict: Standardized error response
    """
    return {
        "error": True,
        "error_type": "TimeoutError",
        "message": "Request timeout",
        "details": str(error),
        "action": (
            "The GitLab instance is slow or unreachable. "
            "Try again later or increase the timeout."
        )
    }


def format_validation_error(error: ValueError) -> dict[str, Any]:
    """Format validation errors into standardized error responses.

    Args:
        error: ValueError from validation functions

    Returns:
        dict: Standardized error response
    """
    return {
        "error": True,
        "error_type": "ValidationError",
        "message": "Invalid input",
        "details": str(error),
        "action": "Check the input parameters and try again."
    }



def handle_gitlab_errors(func: F) -> F:
    """Decorator to handle GitLab API errors and format them consistently.

    Catches common exceptions and formats them into standardized error responses:
    - httpx.HTTPStatusError -> format_http_error()
    - httpx.ConnectError -> format_connection_error()
    - httpx.TimeoutException -> format_timeout_error()
    - ValueError -> format_validation_error()
    - Exception -> UnexpectedError

    Args:
        func: Function to wrap with error handling

    Returns:
        Wrapped function that returns error dict on exception
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            logger.warning(
                "HTTP error in %s: %s", func.__name__, e.response.status_code
            )
            return format_http_error(e)
        except httpx.ConnectError as e:
            logger.error("Connection error in %s: %s", func.__name__, e)
            return format_connection_error(e)
        except httpx.TimeoutException as e:
            logger.warning("Timeout in %s: %s", func.__name__, e)
            return format_timeout_error(e)
        except ValueError as e:
            logger.warning("Validation error in %s: %s", func.__name__, e)
            return format_validation_error(e)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Catch-all for unexpected errors
            logger.exception("Unexpected error in %s: %s", func.__name__, e)
            return {
                "error": True,
                "error_type": "UnexpectedError",
                "message": "An unexpected error occurred",
                "details": str(e),
                "action": "Please report this error with the details above."
            }

    return wrapper
