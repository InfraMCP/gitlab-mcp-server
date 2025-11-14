"""Tests for user management tools."""

import pytest
from unittest.mock import Mock, patch
import httpx

from gitlab_mcp_server.server import (
    get_current_user,
    get_user,
    list_users,
    search_users,
)


@pytest.fixture
def mock_user_data():
    """Mock user data for testing."""
    return {
        "id": 123,
        "username": "testuser",
        "name": "Test User",
        "avatar_url": "https://gitlab.example.com/avatar.png",
        "email": "testuser@example.com",
        "state": "active",
        "web_url": "https://gitlab.example.com/testuser",
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_users_list():
    """Mock list of users for testing."""
    return [
        {
            "id": 123,
            "username": "testuser1",
            "name": "Test User 1",
            "avatar_url": "https://gitlab.example.com/avatar1.png",
            "email": "testuser1@example.com",
            "state": "active",
        },
        {
            "id": 124,
            "username": "testuser2",
            "name": "Test User 2",
            "avatar_url": "https://gitlab.example.com/avatar2.png",
            "email": "testuser2@example.com",
            "state": "active",
        },
    ]


class TestGetCurrentUser:
    """Tests for get_current_user tool."""
    
    def test_get_current_user_success(self, mock_env_vars, mock_user_data):
        """Test get_current_user with valid authentication."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_user_data
            
            result = get_current_user()
            
            # Verify API call
            mock_request.assert_called_once_with("GET", "user")
            
            # Verify response
            assert result["id"] == 123
            assert result["username"] == "testuser"
            assert result["name"] == "Test User"
    
    def test_get_current_user_with_field_filtering(self, mock_env_vars, mock_user_data):
        """Test get_current_user with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_user_data
            
            result = get_current_user(include_fields="id,username,name")
            
            # Verify filtered fields
            assert "id" in result
            assert "username" in result
            assert "name" in result
            assert "email" not in result
    
    def test_get_current_user_with_all_fields(self, mock_env_vars, mock_user_data):
        """Test get_current_user with all fields."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_user_data
            
            result = get_current_user(include_fields="all")
            
            # Verify all fields are present
            assert result == mock_user_data
    
    def test_get_current_user_authentication_error(self, mock_env_vars):
        """Test get_current_user with authentication error."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            # Simulate 401 error
            response = Mock()
            response.status_code = 401
            response.text = "Unauthorized"
            response.json.return_value = {"message": "401 Unauthorized"}
            mock_request.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=response
            )
            
            result = get_current_user()
            
            # Should return formatted error
            assert result["error"] is True
            assert result["error_type"] == "AuthenticationError"


class TestGetUser:
    """Tests for get_user tool."""
    
    def test_get_user_valid_id(self, mock_env_vars, mock_user_data):
        """Test get_user with valid user ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_user_data
            
            result = get_user(user_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with("GET", "users/123")
            
            # Verify response
            assert result["id"] == 123
            assert result["username"] == "testuser"
    
    def test_get_user_invalid_id(self, mock_env_vars):
        """Test get_user with invalid user ID."""
        result = get_user(user_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_get_user_zero_id(self, mock_env_vars):
        """Test get_user with zero user ID."""
        result = get_user(user_id=0)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_get_user_not_found(self, mock_env_vars):
        """Test get_user with non-existent user."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            # Simulate 404 error
            response = Mock()
            response.status_code = 404
            response.text = "User not found"
            response.json.return_value = {"message": "404 User Not Found"}
            mock_request.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=response
            )
            
            result = get_user(user_id=999)
            
            # Should return formatted error
            assert result["error"] is True
            assert result["error_type"] == "NotFoundError"
    
    def test_get_user_with_field_filtering(self, mock_env_vars, mock_user_data):
        """Test get_user with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_user_data
            
            result = get_user(user_id=123, include_fields="id,username,avatar_url")
            
            # Verify filtered fields
            assert "id" in result
            assert "username" in result
            assert "avatar_url" in result
            assert "email" not in result


class TestListUsers:
    """Tests for list_users tool."""
    
    def test_list_users_default_params(self, mock_env_vars, mock_users_list):
        """Test list_users with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_users_list
            
            result = list_users()
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "users",
                params={"per_page": 20, "page": 1}
            )
            
            # Verify response structure
            assert "items" in result
            assert "page" in result
            assert "per_page" in result
            assert "has_next" in result
            assert result["page"] == 1
            assert result["per_page"] == 20
            assert len(result["items"]) == 2
    
    def test_list_users_with_pagination(self, mock_env_vars, mock_users_list):
        """Test list_users with custom pagination."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_users_list
            
            result = list_users(per_page=10, page=2)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "users",
                params={"per_page": 10, "page": 2}
            )
            
            assert result["page"] == 2
            assert result["per_page"] == 10
    
    def test_list_users_with_field_filtering(self, mock_env_vars, mock_users_list):
        """Test list_users with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_users_list
            
            result = list_users(include_fields="id,username")
            
            # Verify filtered fields
            assert len(result["items"]) == 2
            for item in result["items"]:
                assert "id" in item
                assert "username" in item
                assert "email" not in item
    
    def test_list_users_invalid_pagination(self, mock_env_vars):
        """Test list_users with invalid pagination parameters."""
        result = list_users(per_page=0)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_list_users_pagination_too_large(self, mock_env_vars):
        """Test list_users with per_page exceeding maximum."""
        result = list_users(per_page=200)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestSearchUsers:
    """Tests for search_users tool."""
    
    def test_search_users_success(self, mock_env_vars, mock_users_list):
        """Test search_users with valid search query."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_users_list[0]]
            
            result = search_users(search="testuser1")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "users",
                params={"search": "testuser1", "per_page": 20, "page": 1}
            )
            
            # Verify response
            assert "items" in result
            assert len(result["items"]) == 1
            assert result["items"][0]["username"] == "testuser1"
    
    def test_search_users_with_pagination(self, mock_env_vars, mock_users_list):
        """Test search_users with custom pagination."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_users_list
            
            result = search_users(search="test", per_page=10, page=2)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "users",
                params={"search": "test", "per_page": 10, "page": 2}
            )
            
            assert result["page"] == 2
            assert result["per_page"] == 10
    
    def test_search_users_empty_query(self, mock_env_vars):
        """Test search_users with empty search query."""
        result = search_users(search="")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
        assert "empty" in result["details"].lower()
    
    def test_search_users_whitespace_only(self, mock_env_vars):
        """Test search_users with whitespace-only query."""
        result = search_users(search="   ")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_search_users_invalid_type(self, mock_env_vars):
        """Test search_users with non-string search parameter."""
        result = search_users(search=123)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_search_users_with_field_filtering(self, mock_env_vars, mock_users_list):
        """Test search_users with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_users_list
            
            result = search_users(search="test", include_fields="id,username,name")
            
            # Verify filtered fields
            assert len(result["items"]) == 2
            for item in result["items"]:
                assert "id" in item
                assert "username" in item
                assert "name" in item
                assert "email" not in item
    
    def test_search_users_no_results(self, mock_env_vars):
        """Test search_users with no matching results."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = []
            
            result = search_users(search="nonexistent")
            
            # Verify response
            assert "items" in result
            assert len(result["items"]) == 0
            assert result["has_next"] is False
    
    def test_search_users_strips_whitespace(self, mock_env_vars, mock_users_list):
        """Test search_users strips leading/trailing whitespace."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_users_list
            
            result = search_users(search="  test  ")
            
            # Verify API call has stripped search term
            mock_request.assert_called_once_with(
                "GET",
                "users",
                params={"search": "test", "per_page": 20, "page": 1}
            )
