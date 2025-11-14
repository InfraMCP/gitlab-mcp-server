"""Tests for issue management tools."""

import pytest
from unittest.mock import Mock, patch
import httpx

from gitlab_mcp_server.server import (
    list_issues,
    get_issue,
    create_issue,
    update_issue,
    close_issue,
    reopen_issue,
    add_issue_comment,
    list_issue_comments,
)


@pytest.fixture
def mock_issue_data():
    """Mock issue data for testing."""
    return {
        "id": 456,
        "iid": 1,
        "title": "Test Issue",
        "state": "opened",
        "author": {
            "id": 10,
            "username": "testuser",
            "name": "Test User",
        },
        "created_at": "2024-01-01T00:00:00Z",
        "web_url": "https://gitlab.example.com/user/test-project/-/issues/1",
        "description": "This is a test issue",
        "labels": ["bug", "priority::high"],
    }


@pytest.fixture
def mock_issues_list():
    """Mock list of issues for testing."""
    return [
        {
            "id": 456,
            "iid": 1,
            "title": "Test Issue 1",
            "state": "opened",
            "author": {"id": 10, "username": "testuser"},
            "created_at": "2024-01-01T00:00:00Z",
            "web_url": "https://gitlab.example.com/user/test-project/-/issues/1",
        },
        {
            "id": 457,
            "iid": 2,
            "title": "Test Issue 2",
            "state": "closed",
            "author": {"id": 11, "username": "anotheruser"},
            "created_at": "2024-01-02T00:00:00Z",
            "web_url": "https://gitlab.example.com/user/test-project/-/issues/2",
        },
    ]


@pytest.fixture
def mock_comment_data():
    """Mock comment data for testing."""
    return {
        "id": 789,
        "body": "This is a test comment",
        "author": {
            "id": 10,
            "username": "testuser",
            "name": "Test User",
        },
        "created_at": "2024-01-01T12:00:00Z",
    }


@pytest.fixture
def mock_comments_list():
    """Mock list of comments for testing."""
    return [
        {
            "id": 789,
            "body": "First comment",
            "author": {"id": 10, "username": "testuser"},
            "created_at": "2024-01-01T12:00:00Z",
        },
        {
            "id": 790,
            "body": "Second comment",
            "author": {"id": 11, "username": "anotheruser"},
            "created_at": "2024-01-01T13:00:00Z",
        },
    ]


class TestListIssues:
    """Tests for list_issues tool."""
    
    def test_list_issues_default_params(self, mock_env_vars, mock_issues_list):
        """Test list_issues with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_issues_list
            
            result = list_issues(project_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/issues",
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
    
    def test_list_issues_with_state_filter(self, mock_env_vars, mock_issues_list):
        """Test list_issues with state filter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_issues_list[0]]
            
            result = list_issues(project_id=123, state="opened")
            
            # Verify API call includes state filter
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/issues",
                params={"per_page": 20, "page": 1, "state": "opened"}
            )
            
            assert len(result["items"]) == 1
    
    def test_list_issues_with_labels_filter(self, mock_env_vars, mock_issues_list):
        """Test list_issues with labels filter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_issues_list
            
            result = list_issues(project_id=123, labels="bug,priority::high")
            
            # Verify API call includes labels filter
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/issues",
                params={"per_page": 20, "page": 1, "labels": "bug,priority::high"}
            )
    
    def test_list_issues_with_pagination(self, mock_env_vars, mock_issues_list):
        """Test list_issues with custom pagination."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_issues_list
            
            result = list_issues(project_id=123, per_page=10, page=2)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/issues",
                params={"per_page": 10, "page": 2}
            )
            
            assert result["page"] == 2
            assert result["per_page"] == 10
    
    def test_list_issues_invalid_project_id(self, mock_env_vars):
        """Test list_issues with invalid project ID."""
        result = list_issues(project_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestGetIssue:
    """Tests for get_issue tool."""
    
    def test_get_issue_valid_params(self, mock_env_vars, mock_issue_data):
        """Test get_issue with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_issue_data
            
            result = get_issue(project_id=123, issue_iid=1)
            
            # Verify API call
            mock_request.assert_called_once_with("GET", "projects/123/issues/1")
            
            # Verify response
            assert result["id"] == 456
            assert result["iid"] == 1
            assert result["title"] == "Test Issue"
    
    def test_get_issue_invalid_project_id(self, mock_env_vars):
        """Test get_issue with invalid project ID."""
        result = get_issue(project_id=0, issue_iid=1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_get_issue_invalid_issue_iid(self, mock_env_vars):
        """Test get_issue with invalid issue IID."""
        result = get_issue(project_id=123, issue_iid=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_get_issue_not_found(self, mock_env_vars):
        """Test get_issue with non-existent issue."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            # Simulate 404 error
            response = Mock()
            response.status_code = 404
            response.text = "Issue not found"
            response.json.return_value = {"message": "404 Issue Not Found"}
            mock_request.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=response
            )
            
            result = get_issue(project_id=123, issue_iid=999)
            
            # Should return formatted error
            assert result["error"] is True
            assert result["error_type"] == "NotFoundError"


class TestCreateIssue:
    """Tests for create_issue tool."""
    
    def test_create_issue_minimal(self, mock_env_vars, mock_issue_data):
        """Test create_issue with minimal parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_issue_data
            
            result = create_issue(project_id=123, title="Test Issue")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/issues",
                json={"title": "Test Issue"}
            )
            
            # Verify response
            assert result["id"] == 456
            assert result["title"] == "Test Issue"
    
    def test_create_issue_with_all_params(self, mock_env_vars, mock_issue_data):
        """Test create_issue with all parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_issue_data
            
            result = create_issue(
                project_id=123,
                title="Test Issue",
                description="This is a test issue",
                labels="bug,priority::high",
                assignee_ids=[10, 11]
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/issues",
                json={
                    "title": "Test Issue",
                    "description": "This is a test issue",
                    "labels": "bug,priority::high",
                    "assignee_ids": [10, 11],
                }
            )
    
    def test_create_issue_invalid_project_id(self, mock_env_vars):
        """Test create_issue with invalid project ID."""
        result = create_issue(project_id=-1, title="Test")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestUpdateIssue:
    """Tests for update_issue tool."""
    
    def test_update_issue_title(self, mock_env_vars, mock_issue_data):
        """Test update_issue with title change."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            updated_data = mock_issue_data.copy()
            updated_data["title"] = "Updated Issue"
            mock_request.return_value = updated_data
            
            result = update_issue(project_id=123, issue_iid=1, title="Updated Issue")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/issues/1",
                json={"title": "Updated Issue"}
            )
            
            # Verify response
            assert result["title"] == "Updated Issue"
    
    def test_update_issue_multiple_fields(self, mock_env_vars, mock_issue_data):
        """Test update_issue with multiple field changes."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_issue_data
            
            result = update_issue(
                project_id=123,
                issue_iid=1,
                title="Updated Issue",
                description="Updated description",
                labels="bug"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/issues/1",
                json={
                    "title": "Updated Issue",
                    "description": "Updated description",
                    "labels": "bug",
                }
            )
    
    def test_update_issue_invalid_params(self, mock_env_vars):
        """Test update_issue with invalid parameters."""
        result = update_issue(project_id=0, issue_iid=1, title="Test")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCloseIssue:
    """Tests for close_issue tool."""
    
    def test_close_issue_success(self, mock_env_vars, mock_issue_data):
        """Test close_issue with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            closed_data = mock_issue_data.copy()
            closed_data["state"] = "closed"
            mock_request.return_value = closed_data
            
            result = close_issue(project_id=123, issue_iid=1)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/issues/1",
                json={"state_event": "close"}
            )
            
            # Verify response
            assert result["state"] == "closed"
    
    def test_close_issue_invalid_params(self, mock_env_vars):
        """Test close_issue with invalid parameters."""
        result = close_issue(project_id=123, issue_iid=0)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestReopenIssue:
    """Tests for reopen_issue tool."""
    
    def test_reopen_issue_success(self, mock_env_vars, mock_issue_data):
        """Test reopen_issue with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            reopened_data = mock_issue_data.copy()
            reopened_data["state"] = "opened"
            mock_request.return_value = reopened_data
            
            result = reopen_issue(project_id=123, issue_iid=1)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/issues/1",
                json={"state_event": "reopen"}
            )
            
            # Verify response
            assert result["state"] == "opened"
    
    def test_reopen_issue_invalid_params(self, mock_env_vars):
        """Test reopen_issue with invalid parameters."""
        result = reopen_issue(project_id=-1, issue_iid=1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestAddIssueComment:
    """Tests for add_issue_comment tool."""
    
    def test_add_issue_comment_success(self, mock_env_vars, mock_comment_data):
        """Test add_issue_comment with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_comment_data
            
            result = add_issue_comment(
                project_id=123,
                issue_iid=1,
                body="This is a test comment"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/issues/1/notes",
                json={"body": "This is a test comment"}
            )
            
            # Verify response
            assert result["id"] == 789
            assert result["body"] == "This is a test comment"
    
    def test_add_issue_comment_invalid_params(self, mock_env_vars):
        """Test add_issue_comment with invalid parameters."""
        result = add_issue_comment(project_id=0, issue_iid=1, body="Test")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestListIssueComments:
    """Tests for list_issue_comments tool."""
    
    def test_list_issue_comments_default_params(self, mock_env_vars, mock_comments_list):
        """Test list_issue_comments with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_comments_list
            
            result = list_issue_comments(project_id=123, issue_iid=1)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/issues/1/notes",
                params={"per_page": 20, "page": 1}
            )
            
            # Verify response structure
            assert "items" in result
            assert "page" in result
            assert "per_page" in result
            assert "has_next" in result
            assert len(result["items"]) == 2
    
    def test_list_issue_comments_with_pagination(self, mock_env_vars, mock_comments_list):
        """Test list_issue_comments with custom pagination."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_comments_list
            
            result = list_issue_comments(project_id=123, issue_iid=1, per_page=10, page=2)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/issues/1/notes",
                params={"per_page": 10, "page": 2}
            )
            
            assert result["page"] == 2
            assert result["per_page"] == 10
    
    def test_list_issue_comments_invalid_params(self, mock_env_vars):
        """Test list_issue_comments with invalid parameters."""
        result = list_issue_comments(project_id=123, issue_iid=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
