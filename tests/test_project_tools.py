"""Tests for project management tools."""

import pytest
from unittest.mock import Mock, patch
import httpx

from gitlab_mcp_server.server import (
    list_projects,
    get_project,
    create_project,
    update_project,
    delete_project,
)


@pytest.fixture
def mock_project_data():
    """Mock project data for testing."""
    return {
        "id": 123,
        "name": "Test Project",
        "path": "test-project",
        "description": "A test project",
        "web_url": "https://gitlab.example.com/user/test-project",
        "visibility": "private",
        "created_at": "2024-01-01T00:00:00Z",
        "default_branch": "main",
    }


@pytest.fixture
def mock_projects_list():
    """Mock list of projects for testing."""
    return [
        {
            "id": 123,
            "name": "Test Project 1",
            "path": "test-project-1",
            "description": "First test project",
            "web_url": "https://gitlab.example.com/user/test-project-1",
            "visibility": "private",
        },
        {
            "id": 124,
            "name": "Test Project 2",
            "path": "test-project-2",
            "description": "Second test project",
            "web_url": "https://gitlab.example.com/user/test-project-2",
            "visibility": "public",
        },
    ]


class TestListProjects:
    """Tests for list_projects tool."""
    
    def test_list_projects_default_params(self, mock_env_vars, mock_projects_list):
        """Test list_projects with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_projects_list
            
            result = list_projects()
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects",
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
    
    def test_list_projects_with_search(self, mock_env_vars, mock_projects_list):
        """Test list_projects with search parameter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_projects_list[0]]
            
            result = list_projects(search="test-project-1")
            
            # Verify API call includes search
            mock_request.assert_called_once_with(
                "GET",
                "projects",
                params={"per_page": 20, "page": 1, "search": "test-project-1"}
            )
            
            assert len(result["items"]) == 1
    
    def test_list_projects_with_pagination(self, mock_env_vars, mock_projects_list):
        """Test list_projects with custom pagination."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_projects_list
            
            result = list_projects(per_page=10, page=2)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects",
                params={"per_page": 10, "page": 2}
            )
            
            assert result["page"] == 2
            assert result["per_page"] == 10
    
    def test_list_projects_with_field_filtering(self, mock_env_vars, mock_projects_list):
        """Test list_projects with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_projects_list
            
            result = list_projects(include_fields="id,name")
            
            # Verify filtered fields
            assert len(result["items"]) == 2
            for item in result["items"]:
                assert "id" in item
                assert "name" in item
                assert "description" not in item


class TestGetProject:
    """Tests for get_project tool."""
    
    def test_get_project_valid_id(self, mock_env_vars, mock_project_data):
        """Test get_project with valid project ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_project_data
            
            result = get_project(project_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with("GET", "projects/123")
            
            # Verify response
            assert result["id"] == 123
            assert result["name"] == "Test Project"
    
    def test_get_project_invalid_id(self, mock_env_vars):
        """Test get_project with invalid project ID."""
        result = get_project(project_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_get_project_not_found(self, mock_env_vars):
        """Test get_project with non-existent project."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            # Simulate 404 error
            response = Mock()
            response.status_code = 404
            response.text = "Project not found"
            response.json.return_value = {"message": "404 Project Not Found"}
            mock_request.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=response
            )
            
            result = get_project(project_id=999)
            
            # Should return formatted error
            assert result["error"] is True
            assert result["error_type"] == "NotFoundError"
    
    def test_get_project_with_field_filtering(self, mock_env_vars, mock_project_data):
        """Test get_project with field filtering."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_project_data
            
            result = get_project(project_id=123, include_fields="id,name,web_url")
            
            # Verify filtered fields
            assert "id" in result
            assert "name" in result
            assert "web_url" in result
            assert "description" not in result


class TestCreateProject:
    """Tests for create_project tool."""
    
    def test_create_project_minimal(self, mock_env_vars, mock_project_data):
        """Test create_project with minimal parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_project_data
            
            result = create_project(name="Test Project")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects",
                json={
                    "name": "Test Project",
                    "visibility": "private",
                    "initialize_with_readme": False,
                }
            )
            
            # Verify response
            assert result["id"] == 123
            assert result["name"] == "Test Project"
    
    def test_create_project_with_all_params(self, mock_env_vars, mock_project_data):
        """Test create_project with all parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_project_data
            
            result = create_project(
                name="Test Project",
                description="A test project",
                visibility="public",
                initialize_with_readme=True
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects",
                json={
                    "name": "Test Project",
                    "description": "A test project",
                    "visibility": "public",
                    "initialize_with_readme": True,
                }
            )


class TestUpdateProject:
    """Tests for update_project tool."""
    
    def test_update_project_name(self, mock_env_vars, mock_project_data):
        """Test update_project with name change."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            updated_data = mock_project_data.copy()
            updated_data["name"] = "Updated Project"
            mock_request.return_value = updated_data
            
            result = update_project(project_id=123, name="Updated Project")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123",
                json={"name": "Updated Project"}
            )
            
            # Verify response
            assert result["name"] == "Updated Project"
    
    def test_update_project_multiple_fields(self, mock_env_vars, mock_project_data):
        """Test update_project with multiple field changes."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_project_data
            
            result = update_project(
                project_id=123,
                name="Updated Project",
                description="Updated description",
                visibility="public"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123",
                json={
                    "name": "Updated Project",
                    "description": "Updated description",
                    "visibility": "public",
                }
            )
    
    def test_update_project_invalid_id(self, mock_env_vars):
        """Test update_project with invalid project ID."""
        result = update_project(project_id=0, name="Test")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestDeleteProject:
    """Tests for delete_project tool."""
    
    def test_delete_project_success(self, mock_env_vars):
        """Test delete_project with valid project ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = None
            
            result = delete_project(project_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with("DELETE", "projects/123")
            
            # Verify response
            assert result["success"] is True
            assert "123" in result["message"]
    
    def test_delete_project_invalid_id(self, mock_env_vars):
        """Test delete_project with invalid project ID."""
        result = delete_project(project_id=-5)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_delete_project_not_found(self, mock_env_vars):
        """Test delete_project with non-existent project."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            # Simulate 404 error
            response = Mock()
            response.status_code = 404
            response.text = "Project not found"
            response.json.return_value = {"message": "404 Project Not Found"}
            mock_request.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=response
            )
            
            result = delete_project(project_id=999)
            
            # Should return formatted error
            assert result["error"] is True
            assert result["error_type"] == "NotFoundError"
