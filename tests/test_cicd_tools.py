"""Tests for CI/CD pipeline and job management tools."""

import pytest
from unittest.mock import Mock, patch
import httpx

from gitlab_mcp_server.server import (
    list_pipelines,
    get_pipeline,
    create_pipeline,
    retry_pipeline,
    cancel_pipeline,
    list_jobs,
    get_job,
    retry_job,
    cancel_job,
    get_job_log,
)


@pytest.fixture
def mock_pipeline_data():
    """Mock pipeline data for testing."""
    return {
        "id": 456,
        "status": "success",
        "ref": "main",
        "sha": "abc123def456",
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:15:00Z",
        "web_url": "https://gitlab.example.com/user/project/-/pipelines/456",
    }


@pytest.fixture
def mock_pipelines_list():
    """Mock list of pipelines for testing."""
    return [
        {
            "id": 456,
            "status": "success",
            "ref": "main",
            "created_at": "2024-01-01T10:00:00Z",
            "web_url": "https://gitlab.example.com/user/project/-/pipelines/456",
        },
        {
            "id": 457,
            "status": "failed",
            "ref": "develop",
            "created_at": "2024-01-01T11:00:00Z",
            "web_url": "https://gitlab.example.com/user/project/-/pipelines/457",
        },
    ]


@pytest.fixture
def mock_job_data():
    """Mock job data for testing."""
    return {
        "id": 789,
        "name": "test-job",
        "status": "success",
        "stage": "test",
        "created_at": "2024-01-01T10:05:00Z",
        "started_at": "2024-01-01T10:06:00Z",
        "finished_at": "2024-01-01T10:10:00Z",
        "web_url": "https://gitlab.example.com/user/project/-/jobs/789",
    }


@pytest.fixture
def mock_jobs_list():
    """Mock list of jobs for testing."""
    return [
        {
            "id": 789,
            "name": "test-job",
            "status": "success",
            "stage": "test",
            "created_at": "2024-01-01T10:05:00Z",
            "web_url": "https://gitlab.example.com/user/project/-/jobs/789",
        },
        {
            "id": 790,
            "name": "build-job",
            "status": "failed",
            "stage": "build",
            "created_at": "2024-01-01T10:02:00Z",
            "web_url": "https://gitlab.example.com/user/project/-/jobs/790",
        },
    ]


# ============================================================================
# Pipeline Management Tests
# ============================================================================

class TestListPipelines:
    """Tests for list_pipelines tool."""
    
    def test_list_pipelines_default_params(self, mock_env_vars, mock_pipelines_list):
        """Test list_pipelines with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_pipelines_list
            
            result = list_pipelines(project_id=123)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/pipelines",
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
    
    def test_list_pipelines_with_ref_filter(self, mock_env_vars, mock_pipelines_list):
        """Test list_pipelines with ref filter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_pipelines_list[0]]
            
            result = list_pipelines(project_id=123, ref="main")
            
            # Verify API call includes ref
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/pipelines",
                params={"per_page": 20, "page": 1, "ref": "main"}
            )
            
            assert len(result["items"]) == 1
    
    def test_list_pipelines_with_status_filter(self, mock_env_vars, mock_pipelines_list):
        """Test list_pipelines with status filter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_pipelines_list[1]]
            
            result = list_pipelines(project_id=123, status="failed")
            
            # Verify API call includes status
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/pipelines",
                params={"per_page": 20, "page": 1, "status": "failed"}
            )
            
            assert len(result["items"]) == 1
    
    def test_list_pipelines_invalid_status(self, mock_env_vars):
        """Test list_pipelines with invalid status."""
        result = list_pipelines(project_id=123, status="invalid_status")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_list_pipelines_invalid_project_id(self, mock_env_vars):
        """Test list_pipelines with invalid project ID."""
        result = list_pipelines(project_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestGetPipeline:
    """Tests for get_pipeline tool."""
    
    def test_get_pipeline_valid_id(self, mock_env_vars, mock_pipeline_data):
        """Test get_pipeline with valid pipeline ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_pipeline_data
            
            result = get_pipeline(project_id=123, pipeline_id=456)
            
            # Verify API call
            mock_request.assert_called_once_with("GET", "projects/123/pipelines/456")
            
            # Verify response
            assert result["id"] == 456
            assert result["status"] == "success"
    
    def test_get_pipeline_invalid_project_id(self, mock_env_vars):
        """Test get_pipeline with invalid project ID."""
        result = get_pipeline(project_id=0, pipeline_id=456)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_get_pipeline_invalid_pipeline_id(self, mock_env_vars):
        """Test get_pipeline with invalid pipeline ID."""
        result = get_pipeline(project_id=123, pipeline_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCreatePipeline:
    """Tests for create_pipeline tool."""
    
    def test_create_pipeline_minimal(self, mock_env_vars, mock_pipeline_data):
        """Test create_pipeline with minimal parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_pipeline_data
            
            result = create_pipeline(project_id=123, ref="main")
            
            # Verify API call
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/pipeline",
                json={"ref": "main"}
            )
            
            # Verify response
            assert result["id"] == 456
            assert result["ref"] == "main"
    
    def test_create_pipeline_with_variables(self, mock_env_vars, mock_pipeline_data):
        """Test create_pipeline with variables."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_pipeline_data
            
            variables = {"ENV": "production", "DEBUG": "false"}
            result = create_pipeline(project_id=123, ref="main", variables=variables)
            
            # Verify API call includes variables
            mock_request.assert_called_once_with(
                "POST",
                "projects/123/pipeline",
                json={
                    "ref": "main",
                    "variables": [
                        {"key": "ENV", "value": "production"},
                        {"key": "DEBUG", "value": "false"},
                    ]
                }
            )
    
    def test_create_pipeline_invalid_ref(self, mock_env_vars):
        """Test create_pipeline with invalid ref."""
        result = create_pipeline(project_id=123, ref="")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestRetryPipeline:
    """Tests for retry_pipeline tool."""
    
    def test_retry_pipeline_success(self, mock_env_vars, mock_pipeline_data):
        """Test retry_pipeline with valid pipeline ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            retried_data = mock_pipeline_data.copy()
            retried_data["status"] = "running"
            mock_request.return_value = retried_data
            
            result = retry_pipeline(project_id=123, pipeline_id=456)
            
            # Verify API call
            mock_request.assert_called_once_with("POST", "projects/123/pipelines/456/retry")
            
            # Verify response
            assert result["id"] == 456
            assert result["status"] == "running"
    
    def test_retry_pipeline_invalid_id(self, mock_env_vars):
        """Test retry_pipeline with invalid pipeline ID."""
        result = retry_pipeline(project_id=123, pipeline_id=0)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCancelPipeline:
    """Tests for cancel_pipeline tool."""
    
    def test_cancel_pipeline_success(self, mock_env_vars, mock_pipeline_data):
        """Test cancel_pipeline with valid pipeline ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            canceled_data = mock_pipeline_data.copy()
            canceled_data["status"] = "canceled"
            mock_request.return_value = canceled_data
            
            result = cancel_pipeline(project_id=123, pipeline_id=456)
            
            # Verify API call
            mock_request.assert_called_once_with("POST", "projects/123/pipelines/456/cancel")
            
            # Verify response
            assert result["id"] == 456
            assert result["status"] == "canceled"
    
    def test_cancel_pipeline_invalid_id(self, mock_env_vars):
        """Test cancel_pipeline with invalid pipeline ID."""
        result = cancel_pipeline(project_id=123, pipeline_id=-5)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


# ============================================================================
# Job Management Tests
# ============================================================================

class TestListJobs:
    """Tests for list_jobs tool."""
    
    def test_list_jobs_default_params(self, mock_env_vars, mock_jobs_list):
        """Test list_jobs with default parameters."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_jobs_list
            
            result = list_jobs(project_id=123, pipeline_id=456)
            
            # Verify API call
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/pipelines/456/jobs",
                params={"per_page": 20, "page": 1}
            )
            
            # Verify response structure
            assert "items" in result
            assert "page" in result
            assert "per_page" in result
            assert len(result["items"]) == 2
    
    def test_list_jobs_with_scope_filter(self, mock_env_vars, mock_jobs_list):
        """Test list_jobs with scope filter."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = [mock_jobs_list[1]]
            
            result = list_jobs(project_id=123, pipeline_id=456, scope="failed")
            
            # Verify API call includes scope
            mock_request.assert_called_once_with(
                "GET",
                "projects/123/pipelines/456/jobs",
                params={"per_page": 20, "page": 1, "scope": "failed"}
            )
            
            assert len(result["items"]) == 1
    
    def test_list_jobs_invalid_scope(self, mock_env_vars):
        """Test list_jobs with invalid scope."""
        result = list_jobs(project_id=123, pipeline_id=456, scope="invalid_scope")
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_list_jobs_invalid_pipeline_id(self, mock_env_vars):
        """Test list_jobs with invalid pipeline ID."""
        result = list_jobs(project_id=123, pipeline_id=0)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestGetJob:
    """Tests for get_job tool."""
    
    def test_get_job_valid_id(self, mock_env_vars, mock_job_data):
        """Test get_job with valid job ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            mock_request.return_value = mock_job_data
            
            result = get_job(project_id=123, job_id=789)
            
            # Verify API call
            mock_request.assert_called_once_with("GET", "projects/123/jobs/789")
            
            # Verify response
            assert result["id"] == 789
            assert result["name"] == "test-job"
            assert result["status"] == "success"
    
    def test_get_job_invalid_job_id(self, mock_env_vars):
        """Test get_job with invalid job ID."""
        result = get_job(project_id=123, job_id=-1)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestRetryJob:
    """Tests for retry_job tool."""
    
    def test_retry_job_success(self, mock_env_vars, mock_job_data):
        """Test retry_job with valid job ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            retried_data = mock_job_data.copy()
            retried_data["status"] = "pending"
            mock_request.return_value = retried_data
            
            result = retry_job(project_id=123, job_id=789)
            
            # Verify API call
            mock_request.assert_called_once_with("POST", "projects/123/jobs/789/retry")
            
            # Verify response
            assert result["id"] == 789
            assert result["status"] == "pending"
    
    def test_retry_job_invalid_id(self, mock_env_vars):
        """Test retry_job with invalid job ID."""
        result = retry_job(project_id=123, job_id=0)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestCancelJob:
    """Tests for cancel_job tool."""
    
    def test_cancel_job_success(self, mock_env_vars, mock_job_data):
        """Test cancel_job with valid job ID."""
        with patch("gitlab_mcp_server.server.make_request") as mock_request:
            canceled_data = mock_job_data.copy()
            canceled_data["status"] = "canceled"
            mock_request.return_value = canceled_data
            
            result = cancel_job(project_id=123, job_id=789)
            
            # Verify API call
            mock_request.assert_called_once_with("POST", "projects/123/jobs/789/cancel")
            
            # Verify response
            assert result["id"] == 789
            assert result["status"] == "canceled"
    
    def test_cancel_job_invalid_id(self, mock_env_vars):
        """Test cancel_job with invalid job ID."""
        result = cancel_job(project_id=123, job_id=-10)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"


class TestGetJobLog:
    """Tests for get_job_log tool."""
    
    def test_get_job_log_success(self, mock_env_vars):
        """Test get_job_log with valid job ID."""
        mock_log_text = "Job log output\nLine 2\nLine 3"
        
        with patch("gitlab_mcp_server.server.httpx.Client") as mock_client_class:
            # Mock the context manager and response
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = mock_log_text
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client
            
            result = get_job_log(project_id=123, job_id=789)
            
            # Verify response
            assert "log" in result
            assert result["log"] == mock_log_text
            assert result["job_id"] == 789
            assert result["project_id"] == 123
    
    def test_get_job_log_invalid_job_id(self, mock_env_vars):
        """Test get_job_log with invalid job ID."""
        result = get_job_log(project_id=123, job_id=0)
        
        # Should return validation error
        assert result["error"] is True
        assert result["error_type"] == "ValidationError"
    
    def test_get_job_log_not_found(self, mock_env_vars):
        """Test get_job_log with non-existent job."""
        with patch("gitlab_mcp_server.server.httpx.Client") as mock_client_class:
            # Mock 404 error
            mock_client = Mock()
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Job not found"
            mock_response.json.return_value = {"message": "404 Job Not Found"}
            
            def raise_status():
                raise httpx.HTTPStatusError(
                    "404 Not Found",
                    request=Mock(),
                    response=mock_response
                )
            
            mock_response.raise_for_status = raise_status
            mock_client.get.return_value = mock_response
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client
            
            result = get_job_log(project_id=123, job_id=999)
            
            # Should return formatted error
            assert result["error"] is True
            assert result["error_type"] == "NotFoundError"
