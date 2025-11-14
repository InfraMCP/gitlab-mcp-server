"""Unit tests for error handling functionality."""

import pytest
from unittest.mock import Mock
import httpx

from gitlab_mcp_server.errors import (
    format_http_error,
    format_connection_error,
    format_timeout_error,
    format_validation_error,
    handle_gitlab_errors,
)


class TestFormatHttpError:
    """Tests for format_http_error() function."""
    
    def test_format_401_authentication_error(self):
        """Test format_http_error() with 401 status code."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.side_effect = Exception("No JSON")
        
        # Create HTTPStatusError
        error = httpx.HTTPStatusError(
            "Unauthorized",
            request=Mock(),
            response=mock_response
        )
        
        # Format error
        result = format_http_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "AuthenticationError"
        assert result["message"] == "Authentication failed"
        assert "Unauthorized" in result["details"]
        assert "GITLAB_TOKEN" in result["action"]
        assert "personal_access_tokens" in result["action"]
    
    def test_format_403_authorization_error(self):
        """Test format_http_error() with 403 status code."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.json.return_value = {"message": "Access denied"}
        
        # Create HTTPStatusError
        error = httpx.HTTPStatusError(
            "Forbidden",
            request=Mock(),
            response=mock_response
        )
        
        # Format error
        result = format_http_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "AuthorizationError"
        assert result["message"] == "Access forbidden"
        assert "Access denied" in result["details"]
        assert "permission" in result["action"]
        assert "token scopes" in result["action"]
    
    def test_format_404_not_found_error(self):
        """Test format_http_error() with 404 status code."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.return_value = {"message": "Project not found"}
        
        # Create HTTPStatusError
        error = httpx.HTTPStatusError(
            "Not Found",
            request=Mock(),
            response=mock_response
        )
        
        # Format error
        result = format_http_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "NotFoundError"
        assert result["message"] == "Resource not found"
        assert "Project not found" in result["details"]
        assert "Verify" in result["action"]
    
    def test_format_422_validation_error(self):
        """Test format_http_error() with 422 status code."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.text = "Unprocessable Entity"
        mock_response.json.return_value = {"message": "Name is required"}
        
        # Create HTTPStatusError
        error = httpx.HTTPStatusError(
            "Unprocessable Entity",
            request=Mock(),
            response=mock_response
        )
        
        # Format error
        result = format_http_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
        assert result["message"] == "Invalid request parameters"
        assert "Name is required" in result["details"]
        assert "parameters" in result["action"]
    
    def test_format_429_rate_limit_error(self):
        """Test format_http_error() with 429 status code."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_response.json.return_value = {"message": "Rate limit exceeded"}
        
        # Create HTTPStatusError
        error = httpx.HTTPStatusError(
            "Too Many Requests",
            request=Mock(),
            response=mock_response
        )
        
        # Format error
        result = format_http_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "RateLimitError"
        assert result["message"] == "Rate limit exceeded"
        assert "Rate limit exceeded" in result["details"]
        assert "Wait" in result["action"]
    
    def test_format_500_server_error(self):
        """Test format_http_error() with 500 status code."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = Exception("No JSON")
        
        # Create HTTPStatusError
        error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=Mock(),
            response=mock_response
        )
        
        # Format error
        result = format_http_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "ServerError"
        assert "500" in result["message"]
        assert "Internal Server Error" in result["details"]
        assert "server encountered an error" in result["action"]
    
    def test_format_503_server_error(self):
        """Test format_http_error() with 503 status code."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_response.json.side_effect = Exception("No JSON")
        
        # Create HTTPStatusError
        error = httpx.HTTPStatusError(
            "Service Unavailable",
            request=Mock(),
            response=mock_response
        )
        
        # Format error
        result = format_http_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "ServerError"
        assert "503" in result["message"]
        assert "Service Unavailable" in result["details"]
    
    def test_format_other_http_error(self):
        """Test format_http_error() with other status codes."""
        # Create mock response
        mock_response = Mock()
        mock_response.status_code = 418
        mock_response.text = "I'm a teapot"
        mock_response.json.side_effect = Exception("No JSON")
        
        # Create HTTPStatusError
        error = httpx.HTTPStatusError(
            "I'm a teapot",
            request=Mock(),
            response=mock_response
        )
        
        # Format error
        result = format_http_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "HTTPError"
        assert "418" in result["message"]
        assert "I'm a teapot" in result["details"]
        assert "API documentation" in result["action"]


class TestFormatConnectionError:
    """Tests for format_connection_error() function."""
    
    def test_format_connection_error(self):
        """Test format_connection_error() formats correctly."""
        # Create ConnectError
        error = httpx.ConnectError("Connection refused")
        
        # Format error
        result = format_connection_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "ConnectionError"
        assert result["message"] == "Failed to connect to GitLab"
        assert "Connection refused" in result["details"]
        assert "network connection" in result["action"]
        assert "GITLAB_URL" in result["action"]


class TestFormatTimeoutError:
    """Tests for format_timeout_error() function."""
    
    def test_format_timeout_error(self):
        """Test format_timeout_error() formats correctly."""
        # Create TimeoutException
        error = httpx.TimeoutException("Request timeout after 30s")
        
        # Format error
        result = format_timeout_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "TimeoutError"
        assert result["message"] == "Request timeout"
        assert "timeout after 30s" in result["details"]
        assert "slow or unreachable" in result["action"]


class TestFormatValidationError:
    """Tests for format_validation_error() function."""
    
    def test_format_validation_error(self):
        """Test format_validation_error() formats correctly."""
        # Create ValueError
        error = ValueError("project_id must be a positive integer")
        
        # Format error
        result = format_validation_error(error)
        
        # Verify result
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
        assert result["message"] == "Invalid input"
        assert "positive integer" in result["details"]
        assert "input parameters" in result["action"]


class TestHandleGitlabErrorsDecorator:
    """Tests for handle_gitlab_errors() decorator."""
    
    def test_decorator_success_no_error(self):
        """Test decorator allows successful function execution."""
        @handle_gitlab_errors
        def successful_function():
            return {"success": True, "data": "test"}
        
        result = successful_function()
        
        assert result == {"success": True, "data": "test"}
    
    def test_decorator_catches_http_status_error(self):
        """Test decorator catches HTTPStatusError."""
        @handle_gitlab_errors
        def function_with_http_error():
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_response.json.side_effect = Exception("No JSON")
            
            raise httpx.HTTPStatusError(
                "Not Found",
                request=Mock(),
                response=mock_response
            )
        
        result = function_with_http_error()
        
        assert result["error"] is True
        assert result["error_type"] == "NotFoundError"
        assert "Resource not found" in result["message"]
    
    def test_decorator_catches_connect_error(self):
        """Test decorator catches ConnectError."""
        @handle_gitlab_errors
        def function_with_connect_error():
            raise httpx.ConnectError("Connection refused")
        
        result = function_with_connect_error()
        
        assert result["error"] is True
        assert result["error_type"] == "ConnectionError"
        assert "Failed to connect" in result["message"]
    
    def test_decorator_catches_timeout_exception(self):
        """Test decorator catches TimeoutException."""
        @handle_gitlab_errors
        def function_with_timeout():
            raise httpx.TimeoutException("Request timeout")
        
        result = function_with_timeout()
        
        assert result["error"] is True
        assert result["error_type"] == "TimeoutError"
        assert "Request timeout" in result["message"]
    
    def test_decorator_catches_value_error(self):
        """Test decorator catches ValueError."""
        @handle_gitlab_errors
        def function_with_value_error():
            raise ValueError("Invalid parameter")
        
        result = function_with_value_error()
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
        assert "Invalid input" in result["message"]
        assert "Invalid parameter" in result["details"]
    
    def test_decorator_catches_unexpected_error(self):
        """Test decorator catches unexpected exceptions."""
        @handle_gitlab_errors
        def function_with_unexpected_error():
            raise RuntimeError("Something went wrong")
        
        result = function_with_unexpected_error()
        
        assert result["error"] is True
        assert result["error_type"] == "UnexpectedError"
        assert "unexpected error" in result["message"]
        assert "Something went wrong" in result["details"]
        assert "report this error" in result["action"]
    
    def test_decorator_with_function_arguments(self):
        """Test decorator works with function arguments."""
        @handle_gitlab_errors
        def function_with_args(a, b, c=None):
            if c is None:
                raise ValueError("c is required")
            return a + b + c
        
        # Test success case
        result = function_with_args(1, 2, c=3)
        assert result == 6
        
        # Test error case
        result = function_with_args(1, 2)
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""
        @handle_gitlab_errors
        def test_function():
            """Test docstring."""
            pass
        
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring."
    
    def test_all_error_responses_have_required_fields(self):
        """Test all error responses include required fields."""
        required_fields = ["error", "error_type", "message", "details", "action"]
        
        # Test with different error types
        error_functions = [
            lambda: httpx.HTTPStatusError("", request=Mock(), response=Mock(status_code=401, text="", json=lambda: {})),
            lambda: httpx.ConnectError(""),
            lambda: httpx.TimeoutException(""),
            lambda: ValueError(""),
            lambda: RuntimeError(""),
        ]
        
        for error_func in error_functions:
            @handle_gitlab_errors
            def test_func():
                raise error_func()
            
            result = test_func()
            
            # Verify all required fields are present
            for field in required_fields:
                assert field in result, f"Missing field: {field}"
            
            # Verify error is True
            assert result["error"] is True
