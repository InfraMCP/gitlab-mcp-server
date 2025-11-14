"""Tests for group management tools."""

import pytest
from unittest.mock import Mock, patch
import httpx

from gitlab_mcp_server.server import (
    list_groups,
    get_group,
    create_group,
    update_group,
    delete_group,
    list_group_members,
    add_group_member,
)


@pytest.fixture
def mock_group_data():
    """Mock group data for testing."""
    return {
        "id": 456,
        "name": "Test Group",
        "path": "test-group",
        "description": "A test group",
        "web_url": "https://gitlab.example.com/groups/test-group",
        "visibility": "private",
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_groups_list():
    """Mock list of groups for testing."""
    return [
        {
            "id": 456,
            "name": "Test Group 1",
            "path": "test-group-1",
            "description": "First test group",
            "web_url": "https://gitlab.example.com/groups/test-group-1",
            "visibility": "private",
        },
        {
            "id": 457,
            "name": "Test Group 2",
            "path": "test-group-2",
            "description": "Second test group",
            "web_url": "https://gitlab.example.com/groups/test-group-2",
            "visibility": "public",
        },
    ]


@pytest.fixture
def mock_member_data():
    """Mock member data for testing."""
    return {
        "id": 789,
        "username": "testuser",
        "name": "Test User",
        "avatar_url": "https://gitlab.example.com/avatar.png",
        "access_level": 30,
    }


@pytest.fixture
def mock_members_list():
    """Mock list of members for testing."""
    return [
        {
            "id": 789,
            "username": "testuser1",
            "name": "Test User 1",
            "avatar_url": "https://gitlab.example.com/avatar1.png",
            "access_level": 30,
        },
        {
            "id": 790,
            "username": "testuser2",
            "name": "Test User 2",
            "avatar_url": "https://gitlab.example.com/avatar2.png",
            "access_level": 40,
        },
    ]


class TestListGroups:
    """Tests for list_groups tool."""
    
    def test_list_groups_default_params(self, mock_env_vars, mock_groups_list):
        """Test list_groups with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_groups_list
            
            result = list_groups()
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "groups",
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
    
    def test_list_groups_with_search(self, mock_env_vars, mock_groups_list):
        """Test list_groups with search parameter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_groups_list[0]]
            
            result = list_groups(search="test-group-1")
            
            # Verify API call includes search
            mock_request.assert_called_once_with(
                "GET",
                "groups",
                params={"per_page": 20, "page": 1, "search": "test-group-1"}
            )
            
            assert len(result["items"]) == 1
    
    def test_list_groups_with_pagination(self, mock_env_vars, mock_groups_list):
        """Test list_groups with custom pagination."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_groups_list
            
            result = list_groups(per_page=10, page=2)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "groups",
                params={"per_page": 10, "page": 2}
            )
            
            assert result["page"] == 2
            assert result["per_page"] == 10
    
    def test_list_groups_with_field_filtering(self, mock_env_vars, mock_groups_list):
        """Test list_groups with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_groups_list
            
            result = list_groups(include_fields="id,name")
            
            # Verify filtered fields
            assert len(result["items"]) == 2
            for item in result["items"]:
                assert "id" in item
                assert "name" in item
                assert "description" not in item


class TestGetGroup:
    """Tests for get_group tool."""
    
    def test_get_group_valid_id(self, mock_env_vars, mock_group_data):
        """Test get_group with valid group ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_group_data
            
            result = get_group(group_id=456)
            
            # Verify API call
            mock_request.assert_called_once_with("GET", "groups/456")
            
            # Verify response
            assert result["id"] == 456
            assert result["name"] == "Test Group"
    
    def test_get_group_invalid_id(self, mock_env_vars):
        """Test get_group with invalid group ID."""
        result = get_group(group_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_get_group_not_found(self, mock_env_vars):
        """Test get_group with non-existent group."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            # Simulate 404 error
            response = Mock()
            response.status_code = 404
            response.text = "Group not found"
            response.json.return_value = {"message": "404 Group Not Found"}
            mock_request.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=response
            )
            
            result = get_group(group_id=999)
            
            # Should return formatted error
            assert result["error"] is True
            assert result["error_type"] == "NotFoundError"
    
    def test_get_group_with_field_filtering(self, mock_env_vars, mock_group_data):
        """Test get_group with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_group_data
            
            result = get_group(group_id=456, include_fields="id,name,web_url")
            
            # Verify filtered fields
            assert "id" in result
            assert "name" in result
            assert "web_url" in result
            assert "description" not in result


class TestCreateGroup:
    """Tests for create_group tool."""
    
    def test_create_group_minimal(self, mock_env_vars, mock_group_data):
        """Test create_group with minimal parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_group_data
            
            result = create_group(name="Test Group", path="test-group")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "groups",
                json={
                    "name": "Test Group",
                    "path": "test-group",
                    "visibility": "private",
                }
            )
            
            # Verify response
            assert result["id"] == 456
            assert result["name"] == "Test Group"
    
    def test_create_group_with_all_params(self, mock_env_vars, mock_group_data):
        """Test create_group with all parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_group_data
            
            result = create_group(
                name="Test Group",
                path="test-group",
                description="A test group",
                visibility="public"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "groups",
                json={
                    "name": "Test Group",
                    "path": "test-group",
                    "description": "A test group",
                    "visibility": "public",
                }
            )
    
    def test_create_group_invalid_name(self, mock_env_vars):
        """Test create_group with invalid name."""
        result = create_group(name="", path="test-group")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_create_group_invalid_path(self, mock_env_vars):
        """Test create_group with invalid path."""
        result = create_group(name="Test Group", path="")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_create_group_invalid_visibility(self, mock_env_vars):
        """Test create_group with invalid visibility."""
        result = create_group(name="Test Group", path="test-group", visibility="invalid")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestUpdateGroup:
    """Tests for update_group tool."""
    
    def test_update_group_name(self, mock_env_vars, mock_group_data):
        """Test update_group with name change."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            updated_data = mock_group_data.copy()
            updated_data["name"] = "Updated Group"
            mock_request.return_value = updated_data
            
            result = update_group(group_id=456, name="Updated Group")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "groups/456",
                json={"name": "Updated Group"}
            )
            
            # Verify response
            assert result["name"] == "Updated Group"
    
    def test_update_group_multiple_fields(self, mock_env_vars, mock_group_data):
        """Test update_group with multiple field changes."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_group_data
            
            result = update_group(
                group_id=456,
                name="Updated Group",
                description="Updated description",
                visibility="public"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "groups/456",
                json={
                    "name": "Updated Group",
                    "description": "Updated description",
                    "visibility": "public",
                }
            )
    
    def test_update_group_invalid_id(self, mock_env_vars):
        """Test update_group with invalid group ID."""
        result = update_group(group_id=0, name="Test")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_update_group_invalid_visibility(self, mock_env_vars):
        """Test update_group with invalid visibility."""
        result = update_group(group_id=456, visibility="invalid")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestDeleteGroup:
    """Tests for delete_group tool."""
    
    def test_delete_group_success(self, mock_env_vars):
        """Test delete_group with valid group ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = None
            
            result = delete_group(group_id=456)
            
            # Verify API call
            mock_request.assert_called_once_with("DELETE", "groups/456")
            
            # Verify response
            assert result["success"] is True
            assert "456" in result["message"]
    
    def test_delete_group_invalid_id(self, mock_env_vars):
        """Test delete_group with invalid group ID."""
        result = delete_group(group_id=-5)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_delete_group_not_found(self, mock_env_vars):
        """Test delete_group with non-existent group."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            # Simulate 404 error
            response = Mock()
            response.status_code = 404
            response.text = "Group not found"
            response.json.return_value = {"message": "404 Group Not Found"}
            mock_request.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=response
            )
            
            result = delete_group(group_id=999)
            
            # Should return formatted error
            assert result["error"] is True
            assert result["error_type"] == "NotFoundError"


class TestListGroupMembers:
    """Tests for list_group_members tool."""
    
    def test_list_group_members_default_params(self, mock_env_vars, mock_members_list):
        """Test list_group_members with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_members_list
            
            result = list_group_members(group_id=456)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "groups/456/members",
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
    
    def test_list_group_members_with_pagination(self, mock_env_vars, mock_members_list):
        """Test list_group_members with custom pagination."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_members_list
            
            result = list_group_members(group_id=456, per_page=10, page=2)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "groups/456/members",
                params={"per_page": 10, "page": 2}
            )
            
            assert result["page"] == 2
            assert result["per_page"] == 10
    
    def test_list_group_members_invalid_group_id(self, mock_env_vars):
        """Test list_group_members with invalid group ID."""
        result = list_group_members(group_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_list_group_members_with_field_filtering(self, mock_env_vars, mock_members_list):
        """Test list_group_members with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_members_list
            
            result = list_group_members(group_id=456, include_fields="id,username")
            
            # Verify filtered fields
            assert len(result["items"]) == 2
            for item in result["items"]:
                assert "id" in item
                assert "username" in item
                assert "avatar_url" not in item


class TestAddGroupMember:
    """Tests for add_group_member tool."""
    
    def test_add_group_member_default_access(self, mock_env_vars, mock_member_data):
        """Test add_group_member with default access level."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_member_data
            
            result = add_group_member(group_id=456, user_id=789)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "groups/456/members",
                json={"user_id": 789, "access_level": 30}
            )
            
            # Verify response
            assert result["id"] == 789
            assert result["username"] == "testuser"
    
    def test_add_group_member_custom_access(self, mock_env_vars, mock_member_data):
        """Test add_group_member with custom access level."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_member_data
            
            result = add_group_member(group_id=456, user_id=789, access_level=40)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "groups/456/members",
                json={"user_id": 789, "access_level": 40}
            )
    
    def test_add_group_member_invalid_group_id(self, mock_env_vars):
        """Test add_group_member with invalid group ID."""
        result = add_group_member(group_id=-1, user_id=789)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_add_group_member_invalid_user_id(self, mock_env_vars):
        """Test add_group_member with invalid user ID."""
        result = add_group_member(group_id=456, user_id=0)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_add_group_member_invalid_access_level(self, mock_env_vars):
        """Test add_group_member with invalid access level."""
        result = add_group_member(group_id=456, user_id=789, access_level=99)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
        assert "10=Guest, 20=Reporter, 30=Developer, 40=Maintainer, 50=Owner" in result["details"]
    
    def test_add_group_member_with_field_filtering(self, mock_env_vars, mock_member_data):
        """Test add_group_member with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_member_data
            
            result = add_group_member(group_id=456, user_id=789, include_fields="id,username")
            
            # Verify filtered fields
            assert "id" in result
            assert "username" in result
            assert "avatar_url" not in result
