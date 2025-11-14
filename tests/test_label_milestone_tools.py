"""Tests for label and milestone management tools."""

import pytest
from unittest.mock import Mock, patch
import httpx

from gitlab_mcp_server.server import (
    list_labels,
    create_label,
    update_label,
    delete_label,
    list_milestones,
    create_milestone,
    update_milestone,
    close_milestone,
)


@pytest.fixture
def mock_label_data():
    """Mock label data for testing."""
    return {
        "id": 1,
        "name": "bug",
        "color": "#FF0000",
        "description": "Bug reports",
        "open_issues_count": 5,
        "closed_issues_count": 10,
    }


@pytest.fixture
def mock_labels_list():
    """Mock list of labels for testing."""
    return [
        {
            "id": 1,
            "name": "bug",
            "color": "#FF0000",
            "description": "Bug reports",
        },
        {
            "id": 2,
            "name": "feature",
            "color": "#00FF00",
            "description": "Feature requests",
        },
    ]


@pytest.fixture
def mock_milestone_data():
    """Mock milestone data for testing."""
    return {
        "id": 1,
        "iid": 1,
        "title": "v1.0",
        "description": "First release",
        "state": "active",
        "due_date": "2024-12-31",
        "start_date": "2024-01-01",
        "web_url": "https://gitlab.example.com/project/milestones/1",
    }


@pytest.fixture
def mock_milestones_list():
    """Mock list of milestones for testing."""
    return [
        {
            "id": 1,
            "iid": 1,
            "title": "v1.0",
            "state": "active",
            "due_date": "2024-12-31",
        },
        {
            "id": 2,
            "iid": 2,
            "title": "v2.0",
            "state": "active",
            "due_date": "2025-06-30",
        },
    ]


# ============================================================================
# Label Management Tests
# ============================================================================

class TestListLabels:
    """Tests for list_labels tool."""
    
    def test_list_labels_default_params(self, mock_env_vars, mock_labels_list):
        """Test list_labels with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_labels_list
            
            result = list_labels(project_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/labels",
                params={"per_page": 20, "page": 1}
            )
            
            # Verify response structure
            assert "items" in result
            assert "page" in result
            assert "per_page" in result
            assert result["page"] == 1
            assert len(result["items"]) == 2
    
    def test_list_labels_with_search(self, mock_env_vars, mock_labels_list):
        """Test list_labels with search parameter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_labels_list[0]]
            
            result = list_labels(project_id=123, search="bug")
            
            # Verify API call includes search
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/labels",
                params={"per_page": 20, "page": 1, "search": "bug"}
            )
            
            assert len(result["items"]) == 1
    
    def test_list_labels_invalid_project_id(self, mock_env_vars):
        """Test list_labels with invalid project ID."""
        result = list_labels(project_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCreateLabel:
    """Tests for create_label tool."""
    
    def test_create_label_minimal(self, mock_env_vars, mock_label_data):
        """Test create_label with minimal parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_label_data
            
            result = create_label(
                project_id=123,
                name="bug",
                color="#FF0000"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/labels",
                json={
                    "name": "bug",
                    "color": "#FF0000",
                }
            )
            
            # Verify response
            assert result["id"] == 1
            assert result["name"] == "bug"
    
    def test_create_label_with_description(self, mock_env_vars, mock_label_data):
        """Test create_label with description."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_label_data
            
            result = create_label(
                project_id=123,
                name="bug",
                color="#FF0000",
                description="Bug reports"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/labels",
                json={
                    "name": "bug",
                    "color": "#FF0000",
                    "description": "Bug reports",
                }
            )
    
    def test_create_label_invalid_project_id(self, mock_env_vars):
        """Test create_label with invalid project ID."""
        result = create_label(project_id=0, name="bug", color="#FF0000")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestUpdateLabel:
    """Tests for update_label tool."""
    
    def test_update_label_name(self, mock_env_vars, mock_label_data):
        """Test update_label with name change."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            updated_data = mock_label_data.copy()
            updated_data["name"] = "critical-bug"
            mock_request.return_value = updated_data
            
            result = update_label(
                project_id=123,
                label_id=1,
                new_name="critical-bug"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/labels/1",
                json={"new_name": "critical-bug"}
            )
    
    def test_update_label_multiple_fields(self, mock_env_vars, mock_label_data):
        """Test update_label with multiple field changes."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_label_data
            
            result = update_label(
                project_id=123,
                label_id=1,
                new_name="critical-bug",
                color="#CC0000",
                description="Critical bugs"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/labels/1",
                json={
                    "new_name": "critical-bug",
                    "color": "#CC0000",
                    "description": "Critical bugs",
                }
            )
    
    def test_update_label_invalid_id(self, mock_env_vars):
        """Test update_label with invalid label ID."""
        result = update_label(project_id=123, label_id=-1, name="bug")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestDeleteLabel:
    """Tests for delete_label tool."""
    
    def test_delete_label_success(self, mock_env_vars):
        """Test delete_label with valid label ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = None
            
            result = delete_label(project_id=123, label_id=1)
            
            # Verify API call
            mock_request.assert_called_once_with("DELETE", "projects/123/labels/1")
            
            # Verify response
            assert result["success"] is True
            assert "1" in result["message"]
    
    def test_delete_label_invalid_id(self, mock_env_vars):
        """Test delete_label with invalid label ID."""
        result = delete_label(project_id=123, label_id=0)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


# ============================================================================
# Milestone Management Tests
# ============================================================================

class TestListMilestones:
    """Tests for list_milestones tool."""
    
    def test_list_milestones_default_params(self, mock_env_vars, mock_milestones_list):
        """Test list_milestones with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_milestones_list
            
            result = list_milestones(project_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/milestones",
                params={"per_page": 20, "page": 1}
            )
            
            # Verify response structure
            assert "items" in result
            assert "page" in result
            assert len(result["items"]) == 2
    
    def test_list_milestones_with_state_filter(self, mock_env_vars, mock_milestones_list):
        """Test list_milestones with state filter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_milestones_list
            
            result = list_milestones(project_id=123, state="active")
            
            # Verify API call includes state
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/milestones",
                params={"per_page": 20, "page": 1, "state": "active"}
            )
    
    def test_list_milestones_with_search(self, mock_env_vars, mock_milestones_list):
        """Test list_milestones with search parameter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_milestones_list[0]]
            
            result = list_milestones(project_id=123, search="v1")
            
            # Verify API call includes search
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/milestones",
                params={"per_page": 20, "page": 1, "search": "v1"}
            )
    
    def test_list_milestones_invalid_state(self, mock_env_vars):
        """Test list_milestones with invalid state."""
        result = list_milestones(project_id=123, state="invalid")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCreateMilestone:
    """Tests for create_milestone tool."""
    
    def test_create_milestone_minimal(self, mock_env_vars, mock_milestone_data):
        """Test create_milestone with minimal parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_milestone_data
            
            result = create_milestone(project_id=123, title="v1.0")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/milestones",
                json={"title": "v1.0"}
            )
            
            # Verify response
            assert result["id"] == 1
            assert result["title"] == "v1.0"
    
    def test_create_milestone_with_all_params(self, mock_env_vars, mock_milestone_data):
        """Test create_milestone with all parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_milestone_data
            
            result = create_milestone(
                project_id=123,
                title="v1.0",
                description="First release",
                due_date="2024-12-31",
                start_date="2024-01-01"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/milestones",
                json={
                    "title": "v1.0",
                    "description": "First release",
                    "due_date": "2024-12-31",
                    "start_date": "2024-01-01",
                }
            )
    
    def test_create_milestone_invalid_project_id(self, mock_env_vars):
        """Test create_milestone with invalid project ID."""
        result = create_milestone(project_id=-1, title="v1.0")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestUpdateMilestone:
    """Tests for update_milestone tool."""
    
    def test_update_milestone_title(self, mock_env_vars, mock_milestone_data):
        """Test update_milestone with title change."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            updated_data = mock_milestone_data.copy()
            updated_data["title"] = "v1.1"
            mock_request.return_value = updated_data
            
            result = update_milestone(
                project_id=123,
                milestone_id=1,
                title="v1.1"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/milestones/1",
                json={"title": "v1.1"}
            )
    
    def test_update_milestone_multiple_fields(self, mock_env_vars, mock_milestone_data):
        """Test update_milestone with multiple field changes."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_milestone_data
            
            result = update_milestone(
                project_id=123,
                milestone_id=1,
                title="v1.1",
                description="Updated release",
                due_date="2025-01-31"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/milestones/1",
                json={
                    "title": "v1.1",
                    "description": "Updated release",
                    "due_date": "2025-01-31",
                }
            )
    
    def test_update_milestone_invalid_id(self, mock_env_vars):
        """Test update_milestone with invalid milestone ID."""
        result = update_milestone(project_id=123, milestone_id=0, title="v1.0")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCloseMilestone:
    """Tests for close_milestone tool."""
    
    def test_close_milestone_success(self, mock_env_vars, mock_milestone_data):
        """Test close_milestone with valid milestone ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            closed_data = mock_milestone_data.copy()
            closed_data["state"] = "closed"
            mock_request.return_value = closed_data
            
            result = close_milestone(project_id=123, milestone_id=1)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/milestones/1",
                json={"state_event": "close"}
            )
            
            # Verify response
            assert result["state"] == "closed"
    
    def test_close_milestone_invalid_id(self, mock_env_vars):
        """Test close_milestone with invalid milestone ID."""
        result = close_milestone(project_id=123, milestone_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
