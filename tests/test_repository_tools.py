"""Tests for repository management tools."""

import pytest
from unittest.mock import Mock, patch
import httpx

from gitlab_mcp_server.server import (
    list_branches,
    get_branch,
    create_branch,
    delete_branch,
    get_file,
    create_file,
    update_file,
    delete_file,
    list_commits,
    get_commit,
    list_tags,
    create_tag,
)


# ============================================================================
# Branch Management Tests
# ============================================================================

@pytest.fixture
def mock_branch_data():
    """Mock branch data for testing."""
    return {
        "name": "main",
        "commit": {
            "id": "abc123",
            "short_id": "abc123",
            "title": "Initial commit",
        },
        "protected": True,
        "web_url": "https://gitlab.example.com/user/project/-/tree/main",
    }


@pytest.fixture
def mock_branches_list():
    """Mock list of branches for testing."""
    return [
        {
            "name": "main",
            "commit": {"id": "abc123", "short_id": "abc123"},
            "protected": True,
            "web_url": "https://gitlab.example.com/user/project/-/tree/main",
        },
        {
            "name": "develop",
            "commit": {"id": "def456", "short_id": "def456"},
            "protected": False,
            "web_url": "https://gitlab.example.com/user/project/-/tree/develop",
        },
    ]


class TestListBranches:
    """Tests for list_branches tool."""
    
    def test_list_branches_default_params(self, mock_env_vars, mock_branches_list):
        """Test list_branches with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_branches_list
            
            result = list_branches(project_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/branches",
                params={"per_page": 20, "page": 1}
            )
            
            # Verify response structure
            assert "items" in result
            assert len(result["items"]) == 2
            assert result["page"] == 1
    
    def test_list_branches_with_search(self, mock_env_vars, mock_branches_list):
        """Test list_branches with search parameter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_branches_list[0]]
            
            result = list_branches(project_id=123, search="main")
            
            # Verify API call includes search
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/branches",
                params={"per_page": 20, "page": 1, "search": "main"}
            )
    
    def test_list_branches_invalid_project_id(self, mock_env_vars):
        """Test list_branches with invalid project ID."""
        result = list_branches(project_id=-1)
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestGetBranch:
    """Tests for get_branch tool."""
    
    def test_get_branch_success(self, mock_env_vars, mock_branch_data):
        """Test get_branch with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_branch_data
            
            result = get_branch(project_id=123, branch="main")
            
            # Verify API call (branch name should be URL encoded)
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/branches/main"
            )
            
            assert result["name"] == "main"
    
    def test_get_branch_with_special_chars(self, mock_env_vars, mock_branch_data):
        """Test get_branch with branch name containing special characters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_branch_data
            
            result = get_branch(project_id=123, branch="feature/test-branch")
            
            # Verify branch name is URL encoded
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/branches/feature%2Ftest-branch"
            )
    
    def test_get_branch_empty_name(self, mock_env_vars):
        """Test get_branch with empty branch name."""
        result = get_branch(project_id=123, branch="")
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCreateBranch:
    """Tests for create_branch tool."""
    
    def test_create_branch_success(self, mock_env_vars, mock_branch_data):
        """Test create_branch with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_branch_data
            
            result = create_branch(project_id=123, branch="feature", ref="main")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/repository/branches",
                json={"branch": "feature", "ref": "main"}
            )
            
            assert result["name"] == "main"
    
    def test_create_branch_empty_ref(self, mock_env_vars):
        """Test create_branch with empty ref."""
        result = create_branch(project_id=123, branch="feature", ref="")
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestDeleteBranch:
    """Tests for delete_branch tool."""
    
    def test_delete_branch_success(self, mock_env_vars):
        """Test delete_branch with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = None
            
            result = delete_branch(project_id=123, branch="feature")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "DELETE",
                "projects/123/repository/branches/feature"
            )
            
            assert result["success"] is True
            assert "feature" in result["message"]


# ============================================================================
# File Management Tests
# ============================================================================

@pytest.fixture
def mock_file_data():
    """Mock file data for testing."""
    return {
        "file_name": "README.md",
        "file_path": "README.md",
        "size": 1024,
        "encoding": "base64",
        "content": "IyBSRUFETUU=",
        "ref": "main",
        "blob_id": "xyz789",
        "commit_id": "abc123",
    }


class TestGetFile:
    """Tests for get_file tool."""
    
    def test_get_file_success(self, mock_env_vars, mock_file_data):
        """Test get_file with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_file_data
            
            result = get_file(project_id=123, file_path="README.md")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/files/README.md",
                params={"ref": "main"}
            )
            
            assert result["file_name"] == "README.md"
    
    def test_get_file_with_custom_ref(self, mock_env_vars, mock_file_data):
        """Test get_file with custom ref."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_file_data
            
            result = get_file(project_id=123, file_path="README.md", ref="develop")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/files/README.md",
                params={"ref": "develop"}
            )
    
    def test_get_file_with_path_encoding(self, mock_env_vars, mock_file_data):
        """Test get_file with file path that needs encoding."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_file_data
            
            result = get_file(project_id=123, file_path="src/main.py")
            
            # Verify file path is URL encoded
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/files/src%2Fmain.py",
                params={"ref": "main"}
            )
    
    def test_get_file_empty_path(self, mock_env_vars):
        """Test get_file with empty file path."""
        result = get_file(project_id=123, file_path="")
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCreateFile:
    """Tests for create_file tool."""
    
    def test_create_file_success(self, mock_env_vars, mock_file_data):
        """Test create_file with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_file_data
            
            result = create_file(
                project_id=123,
                file_path="test.txt",
                branch="main",
                content="Hello World",
                commit_message="Add test file"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/repository/files/test.txt",
                json={
                    "branch": "main",
                    "content": "Hello World",
                    "commit_message": "Add test file",
                    "encoding": "text",
                }
            )
    
    def test_create_file_with_base64(self, mock_env_vars, mock_file_data):
        """Test create_file with base64 encoding."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_file_data
            
            result = create_file(
                project_id=123,
                file_path="image.png",
                branch="main",
                content="iVBORw0KGgo=",
                commit_message="Add image",
                encoding="base64"
            )
            
            # Verify encoding parameter
            call_args = mock_request.call_args
            assert call_args[1]["json"]["encoding"] == "base64"
    
    def test_create_file_empty_commit_message(self, mock_env_vars):
        """Test create_file with empty commit message."""
        result = create_file(
            project_id=123,
            file_path="test.txt",
            branch="main",
            content="Hello",
            commit_message=""
        )
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestUpdateFile:
    """Tests for update_file tool."""
    
    def test_update_file_success(self, mock_env_vars, mock_file_data):
        """Test update_file with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_file_data
            
            result = update_file(
                project_id=123,
                file_path="README.md",
                branch="main",
                content="Updated content",
                commit_message="Update README"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "PUT",
                "projects/123/repository/files/README.md",
                json={
                    "branch": "main",
                    "content": "Updated content",
                    "commit_message": "Update README",
                    "encoding": "text",
                }
            )


class TestDeleteFile:
    """Tests for delete_file tool."""
    
    def test_delete_file_success(self, mock_env_vars):
        """Test delete_file with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = None
            
            result = delete_file(
                project_id=123,
                file_path="old_file.txt",
                branch="main",
                commit_message="Remove old file"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "DELETE",
                "projects/123/repository/files/old_file.txt",
                json={
                    "branch": "main",
                    "commit_message": "Remove old file",
                }
            )
            
            assert result["success"] is True
            assert "old_file.txt" in result["message"]


# ============================================================================
# Commit and Tag Tests
# ============================================================================

@pytest.fixture
def mock_commit_data():
    """Mock commit data for testing."""
    return {
        "id": "abc123def456",
        "short_id": "abc123",
        "title": "Initial commit",
        "author_name": "John Doe",
        "created_at": "2024-01-01T00:00:00Z",
        "web_url": "https://gitlab.example.com/user/project/-/commit/abc123",
    }


@pytest.fixture
def mock_commits_list():
    """Mock list of commits for testing."""
    return [
        {
            "id": "abc123",
            "short_id": "abc123",
            "title": "First commit",
            "author_name": "John Doe",
            "created_at": "2024-01-01T00:00:00Z",
            "web_url": "https://gitlab.example.com/user/project/-/commit/abc123",
        },
        {
            "id": "def456",
            "short_id": "def456",
            "title": "Second commit",
            "author_name": "Jane Smith",
            "created_at": "2024-01-02T00:00:00Z",
            "web_url": "https://gitlab.example.com/user/project/-/commit/def456",
        },
    ]


class TestListCommits:
    """Tests for list_commits tool."""
    
    def test_list_commits_default_params(self, mock_env_vars, mock_commits_list):
        """Test list_commits with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_commits_list
            
            result = list_commits(project_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/commits",
                params={"per_page": 20, "page": 1}
            )
            
            assert "items" in result
            assert len(result["items"]) == 2
    
    def test_list_commits_with_ref(self, mock_env_vars, mock_commits_list):
        """Test list_commits with ref_name parameter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_commits_list
            
            result = list_commits(project_id=123, ref_name="develop")
            
            # Verify API call includes ref_name
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/commits",
                params={"per_page": 20, "page": 1, "ref_name": "develop"}
            )
    
    def test_list_commits_with_date_filters(self, mock_env_vars, mock_commits_list):
        """Test list_commits with date filters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_commits_list
            
            result = list_commits(
                project_id=123,
                since="2024-01-01T00:00:00Z",
                until="2024-12-31T23:59:59Z"
            )
            
            # Verify API call includes date filters
            call_args = mock_request.call_args
            assert call_args[1]["params"]["since"] == "2024-01-01T00:00:00Z"
            assert call_args[1]["params"]["until"] == "2024-12-31T23:59:59Z"


class TestGetCommit:
    """Tests for get_commit tool."""
    
    def test_get_commit_success(self, mock_env_vars, mock_commit_data):
        """Test get_commit with valid SHA."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_commit_data
            
            result = get_commit(project_id=123, sha="abc123")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/commits/abc123"
            )
            
            assert result["id"] == "abc123def456"
    
    def test_get_commit_empty_sha(self, mock_env_vars):
        """Test get_commit with empty SHA."""
        result = get_commit(project_id=123, sha="")
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


@pytest.fixture
def mock_tag_data():
    """Mock tag data for testing."""
    return {
        "name": "v1.0.0",
        "message": "Release version 1.0.0",
        "target": "abc123",
        "commit": {
            "id": "abc123",
            "short_id": "abc123",
        },
        "release": None,
    }


@pytest.fixture
def mock_tags_list():
    """Mock list of tags for testing."""
    return [
        {
            "name": "v1.0.0",
            "message": "Release 1.0.0",
            "target": "abc123",
        },
        {
            "name": "v0.9.0",
            "message": "Release 0.9.0",
            "target": "def456",
        },
    ]


class TestListTags:
    """Tests for list_tags tool."""
    
    def test_list_tags_default_params(self, mock_env_vars, mock_tags_list):
        """Test list_tags with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_tags_list
            
            result = list_tags(project_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/tags",
                params={"per_page": 20, "page": 1}
            )
            
            assert "items" in result
            assert len(result["items"]) == 2
    
    def test_list_tags_with_search(self, mock_env_vars, mock_tags_list):
        """Test list_tags with search parameter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_tags_list[0]]
            
            result = list_tags(project_id=123, search="v1")
            
            # Verify API call includes search
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/repository/tags",
                params={"per_page": 20, "page": 1, "search": "v1"}
            )


class TestCreateTag:
    """Tests for create_tag tool."""
    
    def test_create_tag_success(self, mock_env_vars, mock_tag_data):
        """Test create_tag with valid parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_tag_data
            
            result = create_tag(
                project_id=123,
                tag_name="v1.0.0",
                ref="main",
                message="Release 1.0.0"
            )
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/repository/tags",
                json={
                    "tag_name": "v1.0.0",
                    "ref": "main",
                    "message": "Release 1.0.0",
                }
            )
            
            assert result["name"] == "v1.0.0"
    
    def test_create_tag_without_message(self, mock_env_vars, mock_tag_data):
        """Test create_tag without message."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_tag_data
            
            result = create_tag(project_id=123, tag_name="v1.0.0", ref="main")
            
            # Verify message is not included
            call_args = mock_request.call_args
            assert "message" not in call_args[1]["json"]
    
    def test_create_tag_empty_name(self, mock_env_vars):
        """Test create_tag with empty tag name."""
        result = create_tag(project_id=123, tag_name="", ref="main")
        
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
