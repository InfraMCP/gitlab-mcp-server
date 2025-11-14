"""Unit tests for configuration and HTTP client functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from gitlab_mcp_server.server import (
    get_gitlab_config,
    make_request,
    validate_gitlab_connection,
)


class TestGetGitlabConfig:
    """Tests for get_gitlab_config() function."""
    
    def test_valid_environment_variables(self, mock_env_vars):
        """Test get_gitlab_config() with valid environment variables."""
        config = get_gitlab_config()
        
        assert config["base_url"] == "https://gitlab.example.com"
        assert config["token"] == "glpat-test-token-1234567890"
        assert config["verify_ssl"] is True
    
    def test_missing_gitlab_token(self, monkeypatch):
        """Test get_gitlab_config() with missing GITLAB_TOKEN."""
        # Clear all GitLab environment variables
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)
        monkeypatch.delenv("GITLAB_URL", raising=False)
        monkeypatch.delenv("GITLAB_VERIFY_SSL", raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            get_gitlab_config()
        
        assert "GITLAB_TOKEN environment variable is required" in str(exc_info.value)
        assert "personal_access_tokens" in str(exc_info.value)
    
    def test_invalid_url_format_no_protocol(self, monkeypatch):
        """Test get_gitlab_config() with invalid URL format (no protocol)."""
        monkeypatch.setenv("GITLAB_TOKEN", "glpat-test-token")
        monkeypatch.setenv("GITLAB_URL", "gitlab.example.com")
        
        with pytest.raises(ValueError) as exc_info:
            get_gitlab_config()
        
        assert "must start with http:// or https://" in str(exc_info.value)
    
    def test_default_url(self, monkeypatch):
        """Test get_gitlab_config() defaults to gitlab.com when URL not provided."""
        monkeypatch.setenv("GITLAB_TOKEN", "glpat-test-token")
        monkeypatch.delenv("GITLAB_URL", raising=False)
        
        config = get_gitlab_config()
        
        assert config["base_url"] == "https://gitlab.com"
    
    def test_url_trailing_slash_removed(self, monkeypatch):
        """Test get_gitlab_config() removes trailing slashes from URL."""
        monkeypatch.setenv("GITLAB_TOKEN", "glpat-test-token")
        monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com/")
        
        config = get_gitlab_config()
        
        assert config["base_url"] == "https://gitlab.example.com"
    
    def test_verify_ssl_default_true(self, monkeypatch):
        """Test get_gitlab_config() defaults verify_ssl to true."""
        monkeypatch.setenv("GITLAB_TOKEN", "glpat-test-token")
        monkeypatch.delenv("GITLAB_VERIFY_SSL", raising=False)
        
        config = get_gitlab_config()
        
        assert config["verify_ssl"] is True
    
    def test_verify_ssl_false(self, monkeypatch):
        """Test get_gitlab_config() with verify_ssl set to false."""
        monkeypatch.setenv("GITLAB_TOKEN", "glpat-test-token")
        monkeypatch.setenv("GITLAB_VERIFY_SSL", "false")
        
        config = get_gitlab_config()
        
        assert config["verify_ssl"] is False
    
    def test_verify_ssl_various_values(self, monkeypatch):
        """Test get_gitlab_config() with various verify_ssl values."""
        monkeypatch.setenv("GITLAB_TOKEN", "glpat-test-token")
        
        # Test true values
        for value in ["true", "True", "TRUE", "1", "yes", "Yes"]:
            monkeypatch.setenv("GITLAB_VERIFY_SSL", value)
            config = get_gitlab_config()
            assert config["verify_ssl"] is True, f"Failed for value: {value}"
        
        # Test false values
        for value in ["false", "False", "FALSE", "0", "no", "No"]:
            monkeypatch.setenv("GITLAB_VERIFY_SSL", value)
            config = get_gitlab_config()
            assert config["verify_ssl"] is False, f"Failed for value: {value}"


class TestMakeRequest:
    """Tests for make_request() function."""
    
    @patch("gitlab_mcp_server.server.httpx.Client")
    def test_make_request_get_success(self, mock_client_class, mock_env_vars):
        """Test make_request() with successful GET request."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {"id": 1, "name": "Test Project"}
        mock_response.raise_for_status = Mock()
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Make request
        result = make_request("GET", "projects/1")
        
        # Verify result
        assert result == {"id": 1, "name": "Test Project"}
        
        # Verify client was called correctly
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args.kwargs["method"] == "GET"
        assert call_args.kwargs["url"] == "https://gitlab.example.com/api/v4/projects/1"
        assert call_args.kwargs["headers"]["PRIVATE-TOKEN"] == "glpat-test-token-1234567890"
        assert call_args.kwargs["headers"]["Content-Type"] == "application/json"
        assert "gitlab-mcp-server" in call_args.kwargs["headers"]["User-Agent"]
    
    @patch("gitlab_mcp_server.server.httpx.Client")
    def test_make_request_with_params(self, mock_client_class, mock_env_vars):
        """Test make_request() with query parameters."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Make request with params
        result = make_request("GET", "projects", params={"per_page": 10, "page": 1})
        
        # Verify params were passed
        call_args = mock_client.request.call_args
        assert call_args.kwargs["params"] == {"per_page": 10, "page": 1}
    
    @patch("gitlab_mcp_server.server.httpx.Client")
    def test_make_request_post_with_json(self, mock_client_class, mock_env_vars):
        """Test make_request() with POST and JSON body."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {"id": 2, "name": "New Project"}
        mock_response.raise_for_status = Mock()
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Make POST request
        json_data = {"name": "New Project", "visibility": "private"}
        result = make_request("POST", "projects", json=json_data)
        
        # Verify result
        assert result == {"id": 2, "name": "New Project"}
        
        # Verify JSON was passed
        call_args = mock_client.request.call_args
        assert call_args.kwargs["method"] == "POST"
        assert call_args.kwargs["json"] == json_data
    
    @patch("gitlab_mcp_server.server.httpx.Client")
    def test_make_request_http_error(self, mock_client_class, mock_env_vars):
        """Test make_request() raises HTTPStatusError on HTTP errors."""
        # Setup mock response with error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Verify exception is raised
        with pytest.raises(httpx.HTTPStatusError):
            make_request("GET", "projects/999999")
    
    @patch("gitlab_mcp_server.server.httpx.Client")
    def test_make_request_timeout(self, mock_client_class, mock_env_vars):
        """Test make_request() raises TimeoutException on timeout."""
        # Setup mock client to raise timeout
        mock_client = MagicMock()
        mock_client.request.side_effect = httpx.TimeoutException("Request timeout")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Verify exception is raised
        with pytest.raises(httpx.TimeoutException):
            make_request("GET", "projects")
    
    @patch("gitlab_mcp_server.server.httpx.Client")
    def test_make_request_connection_error(self, mock_client_class, mock_env_vars):
        """Test make_request() raises ConnectError on connection failure."""
        # Setup mock client to raise connection error
        mock_client = MagicMock()
        mock_client.request.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Verify exception is raised
        with pytest.raises(httpx.ConnectError):
            make_request("GET", "projects")
    
    @patch("gitlab_mcp_server.server.httpx.Client")
    def test_make_request_respects_verify_ssl(self, mock_client_class, monkeypatch):
        """Test make_request() respects verify_ssl configuration."""
        # Setup environment with SSL verification disabled
        monkeypatch.setenv("GITLAB_TOKEN", "glpat-test-token")
        monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com")
        monkeypatch.setenv("GITLAB_VERIFY_SSL", "false")
        
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        
        # Setup mock client
        mock_client = MagicMock()
        mock_client.request.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Make request
        make_request("GET", "version")
        
        # Verify client was created with verify=False
        mock_client_class.assert_called_once()
        call_args = mock_client_class.call_args
        assert call_args.kwargs["verify"] is False
        assert call_args.kwargs["timeout"] == 30.0


class TestValidateGitlabConnection:
    """Tests for validate_gitlab_connection() function."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_validate_connection_success(self, mock_make_request, mock_env_vars, capsys):
        """Test validate_gitlab_connection() with successful validation."""
        # Setup mock responses
        mock_make_request.side_effect = [
            {"version": "16.5.1"},  # version endpoint
            {"username": "testuser"},  # user endpoint
            [],  # projects endpoint
        ]
        
        # Validate connection
        result = validate_gitlab_connection()
        
        # Verify result
        assert result is True
        
        # Verify output messages
        captured = capsys.readouterr()
        assert "Connected to GitLab 16.5.1" in captured.out
        assert "Authenticated as: testuser" in captured.out
        assert "Token has read access" in captured.out
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_validate_connection_limited_permissions(self, mock_make_request, mock_env_vars, capsys):
        """Test validate_gitlab_connection() with limited permissions."""
        # Setup mock responses
        mock_response_403 = Mock()
        mock_response_403.status_code = 403
        
        mock_make_request.side_effect = [
            {"version": "16.5.1"},  # version endpoint
            {"username": "testuser"},  # user endpoint
            httpx.HTTPStatusError("Forbidden", request=Mock(), response=mock_response_403),  # projects endpoint
        ]
        
        # Validate connection
        result = validate_gitlab_connection()
        
        # Verify result
        assert result is True
        
        # Verify warning message
        captured = capsys.readouterr()
        assert "Token has limited permissions" in captured.out
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_validate_connection_auth_failure(self, mock_make_request, mock_env_vars):
        """Test validate_gitlab_connection() with authentication failure."""
        # Setup mock response with 401 error
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.text = "Unauthorized"
        
        mock_make_request.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response_401
        )
        
        # Verify exception is raised
        with pytest.raises(ValueError) as exc_info:
            validate_gitlab_connection()
        
        assert "Authentication failed" in str(exc_info.value)
        assert "invalid or expired" in str(exc_info.value)
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_validate_connection_network_error(self, mock_make_request, mock_env_vars):
        """Test validate_gitlab_connection() with connection error."""
        # Setup mock to raise connection error
        mock_make_request.side_effect = httpx.ConnectError("Connection refused")
        
        # Verify exception is raised
        with pytest.raises(ValueError) as exc_info:
            validate_gitlab_connection()
        
        assert "Failed to connect to GitLab" in str(exc_info.value)
        assert "network connection" in str(exc_info.value)
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_validate_connection_timeout(self, mock_make_request, mock_env_vars):
        """Test validate_gitlab_connection() with timeout."""
        # Setup mock to raise timeout
        mock_make_request.side_effect = httpx.TimeoutException("Request timeout")
        
        # Verify exception is raised
        with pytest.raises(ValueError) as exc_info:
            validate_gitlab_connection()
        
        assert "Connection timeout" in str(exc_info.value)
        assert "slow or unreachable" in str(exc_info.value)
    
    def test_validate_connection_missing_token(self, monkeypatch):
        """Test validate_gitlab_connection() with missing token."""
        # Clear token
        monkeypatch.delenv("GITLAB_TOKEN", raising=False)
        
        # Verify exception is raised
        with pytest.raises(ValueError) as exc_info:
            validate_gitlab_connection()
        
        assert "Configuration error" in str(exc_info.value)
        assert "GITLAB_TOKEN" in str(exc_info.value)
