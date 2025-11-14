"""Tests for merge request management tools."""

import pytest
from unittest.mock import Mock, patch
import httpx

from gitlab_mcp_server.server import (
    list_merge_requests,
    get_merge_request,
    create_merge_request,
    update_merge_request,
    merge_merge_request,
    approve_merge_request,
    get_merge_request_changes,
    add_merge_request_comment,
    list_merge_request_comments,
)


@pytest.fixture
def mock_merge_request_data():
    """Mock merge request data for testing."""
    return {
        "id": 789,
        "iid": 1,
        "title": "Test MR",
        "state": "opened",
        "source_branch": "feature-branch",
        "target_branch": "main",
        "author": {
            "id": 10,
            "username": "testuser",
            "name": "Test User",
        },
        "created_at": "2024-01-01T00:00:00Z",
        "web_url": "https://gitlab.example.com/user/test-project/-/merge_requests/1",
        "description": "This is a test merge request",
        "labels": ["enhancement"],
    }


@pytest.fixture
def mock_merge_requests_list():
    """Mock list of merge requests for testing."""
    return [
        {
            "id": 789,
            "iid": 1,
            "title": "Test MR 1",
            "state": "opened",
            "source_branch": "feature-1",
            "target_branch": "main",
            "author": {"id": 10, "username": "testuser"},
            "web_url": "https://gitlab.example.com/user/test-project/-/merge_requests/1",
        },
        {
            "id": 790,
            "iid": 2,
            "title": "Test MR 2",
            "state": "merged",
            "source_branch": "feature-2",
            "target_branch": "main",
            "author": {"id": 11, "username": "anotheruser"},
            "web_url": "https://gitlab.example.com/user/test-project/-/merge_requests/2",
        },
    ]


@pytest.fixture
def mock_comment_data():
    """Mock comment data for testing."""
    return {
        "id": 999,
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
            "id": 999,
            "body": "First comment",
            "author": {"id": 10, "username": "testuser"},
            "created_at": "2024-01-01T12:00:00Z",
        },
        {
            "id": 1000,
            "body": "Second comment",
            "author": {"id": 11, "username": "anotheruser"},
            "created_at": "2024-01-01T13:00:00Z",
        },
    ]


@pytest.fixture
def mock_changes_data():
    """Mock changes/diff data for testing."""
    return {
        "id": 789,
        "iid": 1,
        "changes": [
            {
                "old_path": "file1.py",
                "new_path": "file1.py",
                "diff": "@@ -1,3 +1,4 @@\n+new line\n old line",
            }
        ],
    }


class TestListMergeRequests:
    """Tests for list_merge_requests tool."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_list_merge_requests_success(self, mock_make_request, mock_merge_requests_list):
        """Test successful listing of merge requests."""
        mock_make_request.return_value = mock_merge_requests_list
        
        result = list_merge_requests(project_id=123)
        
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["per_page"] == 20
        mock_make_request.assert_called_once()
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_list_merge_requests_with_state_filter(self, mock_make_request, mock_merge_requests_list):
        """Test listing merge requests with state filter."""
        mock_make_request.return_value = mock_merge_requests_list
        
        result = list_merge_requests(project_id=123, state="opened")
        
        assert "items" in result
        mock_make_request.assert_called_once()
        call_args = mock_make_request.call_args
        assert call_args[1]["params"]["state"] == "opened"
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_list_merge_requests_with_pagination(self, mock_make_request, mock_merge_requests_list):
        """Test listing merge requests with pagination."""
        mock_make_request.return_value = mock_merge_requests_list
        
        result = list_merge_requests(project_id=123, page=2, per_page=10)
        
        assert result["page"] == 2
        assert result["per_page"] == 10
    
    def test_list_merge_requests_invalid_project_id(self):
        """Test listing merge requests with invalid project_id."""
        result = list_merge_requests(project_id=-1)
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestGetMergeRequest:
    """Tests for get_merge_request tool."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_get_merge_request_success(self, mock_make_request, mock_merge_request_data):
        """Test successful retrieval of merge request."""
        mock_make_request.return_value = mock_merge_request_data
        
        result = get_merge_request(project_id=123, mr_iid=1)
        
        assert result["id"] == 789
        assert result["iid"] == 1
        assert result["title"] == "Test MR"
        mock_make_request.assert_called_once_with("GET", "projects/123/merge_requests/1")
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_get_merge_request_with_field_filtering(self, mock_make_request, mock_merge_request_data):
        """Test getting merge request with field filtering."""
        mock_make_request.return_value = mock_merge_request_data
        
        result = get_merge_request(project_id=123, mr_iid=1, include_fields="id,title")
        
        assert "id" in result
        assert "title" in result
        assert "description" not in result
    
    def test_get_merge_request_invalid_mr_iid(self):
        """Test getting merge request with invalid mr_iid."""
        result = get_merge_request(project_id=123, mr_iid=0)
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCreateMergeRequest:
    """Tests for create_merge_request tool."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_create_merge_request_success(self, mock_make_request, mock_merge_request_data):
        """Test successful creation of merge request."""
        mock_make_request.return_value = mock_merge_request_data
        
        result = create_merge_request(
            project_id=123,
            source_branch="feature-branch",
            target_branch="main",
            title="Test MR"
        )
        
        assert result["id"] == 789
        assert result["title"] == "Test MR"
        mock_make_request.assert_called_once()
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_create_merge_request_with_description(self, mock_make_request, mock_merge_request_data):
        """Test creating merge request with description."""
        mock_make_request.return_value = mock_merge_request_data
        
        result = create_merge_request(
            project_id=123,
            source_branch="feature-branch",
            target_branch="main",
            title="Test MR",
            description="Test description"
        )
        
        assert result["id"] == 789
        call_args = mock_make_request.call_args
        assert call_args[1]["json"]["description"] == "Test description"
    
    def test_create_merge_request_invalid_branch_name(self):
        """Test creating merge request with invalid branch name."""
        result = create_merge_request(
            project_id=123,
            source_branch="",
            target_branch="main",
            title="Test MR"
        )
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestUpdateMergeRequest:
    """Tests for update_merge_request tool."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_update_merge_request_success(self, mock_make_request, mock_merge_request_data):
        """Test successful update of merge request."""
        updated_data = mock_merge_request_data.copy()
        updated_data["title"] = "Updated MR"
        mock_make_request.return_value = updated_data
        
        result = update_merge_request(project_id=123, mr_iid=1, title="Updated MR")
        
        assert result["title"] == "Updated MR"
        mock_make_request.assert_called_once()
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_update_merge_request_multiple_fields(self, mock_make_request, mock_merge_request_data):
        """Test updating merge request with multiple fields."""
        mock_make_request.return_value = mock_merge_request_data
        
        result = update_merge_request(
            project_id=123,
            mr_iid=1,
            title="Updated MR",
            description="Updated description",
            state_event="close"
        )
        
        call_args = mock_make_request.call_args
        assert call_args[1]["json"]["title"] == "Updated MR"
        assert call_args[1]["json"]["description"] == "Updated description"
        assert call_args[1]["json"]["state_event"] == "close"


class TestMergeMergeRequest:
    """Tests for merge_merge_request tool."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_merge_merge_request_success(self, mock_make_request):
        """Test successful merging of merge request."""
        merge_result = {"state": "merged", "merged_by": {"username": "testuser"}}
        mock_make_request.return_value = merge_result
        
        result = merge_merge_request(project_id=123, mr_iid=1)
        
        assert result["state"] == "merged"
        mock_make_request.assert_called_once_with(
            "PUT",
            "projects/123/merge_requests/1/merge",
            json={}
        )
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_merge_merge_request_with_message(self, mock_make_request):
        """Test merging merge request with custom message."""
        merge_result = {"state": "merged"}
        mock_make_request.return_value = merge_result
        
        result = merge_merge_request(
            project_id=123,
            mr_iid=1,
            merge_commit_message="Custom merge message"
        )
        
        call_args = mock_make_request.call_args
        assert call_args[1]["json"]["merge_commit_message"] == "Custom merge message"


class TestApproveMergeRequest:
    """Tests for approve_merge_request tool."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_approve_merge_request_success(self, mock_make_request):
        """Test successful approval of merge request."""
        approval_result = {"approved": True, "approved_by": [{"username": "testuser"}]}
        mock_make_request.return_value = approval_result
        
        result = approve_merge_request(project_id=123, mr_iid=1)
        
        assert result["approved"] is True
        mock_make_request.assert_called_once_with(
            "POST",
            "projects/123/merge_requests/1/approve"
        )


class TestGetMergeRequestChanges:
    """Tests for get_merge_request_changes tool."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_get_merge_request_changes_success(self, mock_make_request, mock_changes_data):
        """Test successful retrieval of merge request changes."""
        mock_make_request.return_value = mock_changes_data
        
        result = get_merge_request_changes(project_id=123, mr_iid=1)
        
        assert result["id"] == 789
        assert "changes" in result
        assert len(result["changes"]) == 1
        mock_make_request.assert_called_once_with(
            "GET",
            "projects/123/merge_requests/1/changes"
        )


class TestAddMergeRequestComment:
    """Tests for add_merge_request_comment tool."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_add_merge_request_comment_success(self, mock_make_request, mock_comment_data):
        """Test successful addition of merge request comment."""
        mock_make_request.return_value = mock_comment_data
        
        result = add_merge_request_comment(
            project_id=123,
            mr_iid=1,
            body="Test comment"
        )
        
        assert result["id"] == 999
        assert result["body"] == "This is a test comment"
        mock_make_request.assert_called_once()


class TestListMergeRequestComments:
    """Tests for list_merge_request_comments tool."""
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_list_merge_request_comments_success(self, mock_make_request, mock_comments_list):
        """Test successful listing of merge request comments."""
        mock_make_request.return_value = mock_comments_list
        
        result = list_merge_request_comments(project_id=123, mr_iid=1)
        
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["per_page"] == 20
        mock_make_request.assert_called_once()
    
    @patch("gitlab_mcp_server.server.make_request")
    def test_list_merge_request_comments_with_pagination(self, mock_make_request, mock_comments_list):
        """Test listing merge request comments with pagination."""
        mock_make_request.return_value = mock_comments_list
        
        result = list_merge_request_comments(project_id=123, mr_iid=1, page=2, per_page=10)
        
        assert result["page"] == 2
        assert result["per_page"] == 10
