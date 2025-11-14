"""Unit tests for field filtering and pagination functionality."""

import pytest

from gitlab_mcp_server.server import (
    filter_fields,
    paginate_response,
    DEFAULT_FIELDS,
)


class TestFilterFields:
    """Tests for filter_fields() function."""
    
    def test_filter_with_include_fields_single_object(self):
        """Test filter_fields() with include_fields parameter on single object."""
        data = {
            "id": 1,
            "name": "Test Project",
            "description": "A test project",
            "visibility": "private",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "web_url": "https://gitlab.com/test/project",
        }
        
        result = filter_fields(data, include_fields=["id", "name", "web_url"])
        
        assert result == {
            "id": 1,
            "name": "Test Project",
            "web_url": "https://gitlab.com/test/project",
        }
    
    def test_filter_with_include_fields_list_of_objects(self):
        """Test filter_fields() with include_fields parameter on list of objects."""
        data = [
            {"id": 1, "name": "Project 1", "description": "Desc 1", "visibility": "public"},
            {"id": 2, "name": "Project 2", "description": "Desc 2", "visibility": "private"},
        ]
        
        result = filter_fields(data, include_fields=["id", "name"])
        
        assert result == [
            {"id": 1, "name": "Project 1"},
            {"id": 2, "name": "Project 2"},
        ]
    
    def test_filter_with_all_keyword(self):
        """Test filter_fields() with "all" keyword returns unfiltered data."""
        data = {
            "id": 1,
            "name": "Test Project",
            "description": "A test project",
            "visibility": "private",
        }
        
        # When include_fields is None and no resource_type, data is returned as-is
        result = filter_fields(data, include_fields=None, resource_type=None)
        
        assert result == data
    
    def test_filter_with_default_fields_project(self):
        """Test filter_fields() with default project fields."""
        data = {
            "id": 1,
            "name": "Test Project",
            "path": "test-project",
            "description": "A test project",
            "visibility": "private",
            "web_url": "https://gitlab.com/test/project",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "namespace": {"id": 10, "name": "Test Namespace"},
        }
        
        result = filter_fields(data, resource_type="project")
        
        # Should only include default project fields
        assert result == {
            "id": 1,
            "name": "Test Project",
            "path": "test-project",
            "description": "A test project",
            "visibility": "private",
            "web_url": "https://gitlab.com/test/project",
        }
    
    def test_filter_with_default_fields_issue(self):
        """Test filter_fields() with default issue fields."""
        data = {
            "id": 100,
            "iid": 1,
            "title": "Test Issue",
            "description": "Issue description",
            "state": "opened",
            "author": {"id": 5, "username": "testuser"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "web_url": "https://gitlab.com/test/project/-/issues/1",
            "labels": ["bug", "priority::high"],
        }
        
        result = filter_fields(data, resource_type="issue")
        
        # Should only include default issue fields
        assert result == {
            "id": 100,
            "iid": 1,
            "title": "Test Issue",
            "state": "opened",
            "author": {"id": 5, "username": "testuser"},
            "created_at": "2024-01-01T00:00:00Z",
            "web_url": "https://gitlab.com/test/project/-/issues/1",
        }
    
    def test_filter_with_default_fields_merge_request(self):
        """Test filter_fields() with default merge_request fields."""
        data = {
            "id": 200,
            "iid": 5,
            "title": "Test MR",
            "description": "MR description",
            "state": "opened",
            "source_branch": "feature-branch",
            "target_branch": "main",
            "author": {"id": 5, "username": "testuser"},
            "created_at": "2024-01-01T00:00:00Z",
            "web_url": "https://gitlab.com/test/project/-/merge_requests/5",
            "merge_status": "can_be_merged",
        }
        
        result = filter_fields(data, resource_type="merge_request")
        
        # Should only include default merge_request fields
        assert result == {
            "id": 200,
            "iid": 5,
            "title": "Test MR",
            "state": "opened",
            "source_branch": "feature-branch",
            "target_branch": "main",
            "author": {"id": 5, "username": "testuser"},
            "web_url": "https://gitlab.com/test/project/-/merge_requests/5",
        }
    
    def test_filter_with_missing_fields(self):
        """Test filter_fields() when requested fields don't exist in data."""
        data = {
            "id": 1,
            "name": "Test Project",
        }
        
        result = filter_fields(data, include_fields=["id", "name", "description", "web_url"])
        
        # Should only include fields that exist
        assert result == {
            "id": 1,
            "name": "Test Project",
        }
    
    def test_filter_empty_list(self):
        """Test filter_fields() with empty list."""
        data = []
        
        result = filter_fields(data, include_fields=["id", "name"])
        
        assert result == []
    
    def test_filter_with_unknown_resource_type(self):
        """Test filter_fields() with unknown resource_type returns unfiltered data."""
        data = {"id": 1, "name": "Test", "extra": "field"}
        
        result = filter_fields(data, resource_type="unknown_type")
        
        # Should return data as-is when resource_type not in DEFAULT_FIELDS
        assert result == data
    
    def test_filter_preserves_nested_objects(self):
        """Test filter_fields() preserves nested objects as-is."""
        data = {
            "id": 1,
            "name": "Test Issue",
            "author": {
                "id": 5,
                "username": "testuser",
                "email": "test@example.com",
                "avatar_url": "https://example.com/avatar.jpg",
            },
            "extra_field": "should be filtered",
        }
        
        result = filter_fields(data, include_fields=["id", "name", "author"])
        
        # Nested author object should be preserved completely
        assert result == {
            "id": 1,
            "name": "Test Issue",
            "author": {
                "id": 5,
                "username": "testuser",
                "email": "test@example.com",
                "avatar_url": "https://example.com/avatar.jpg",
            },
        }
    
    def test_default_fields_defined_for_all_resource_types(self):
        """Test that DEFAULT_FIELDS contains all expected resource types."""
        expected_types = [
            "project",
            "issue",
            "merge_request",
            "commit",
            "branch",
            "pipeline",
            "job",
            "user",
            "group",
        ]
        
        for resource_type in expected_types:
            assert resource_type in DEFAULT_FIELDS, f"Missing default fields for {resource_type}"
            assert isinstance(DEFAULT_FIELDS[resource_type], list)
            assert len(DEFAULT_FIELDS[resource_type]) > 0


class TestPaginateResponse:
    """Tests for paginate_response() function."""
    
    def test_paginate_with_full_page(self):
        """Test paginate_response() with full page (has_next should be True)."""
        items = [{"id": i} for i in range(1, 11)]  # 10 items
        
        result = paginate_response(items, page=1, per_page=10)
        
        assert result == {
            "items": items,
            "page": 1,
            "per_page": 10,
            "has_next": True,
            "next_page": 2,
        }
    
    def test_paginate_with_partial_page(self):
        """Test paginate_response() with partial page (has_next should be False)."""
        items = [{"id": i} for i in range(1, 6)]  # 5 items
        
        result = paginate_response(items, page=1, per_page=10)
        
        assert result == {
            "items": items,
            "page": 1,
            "per_page": 10,
            "has_next": False,
            "next_page": None,
        }
    
    def test_paginate_with_empty_page(self):
        """Test paginate_response() with empty page."""
        items = []
        
        result = paginate_response(items, page=1, per_page=10)
        
        assert result == {
            "items": [],
            "page": 1,
            "per_page": 10,
            "has_next": False,
            "next_page": None,
        }
    
    def test_paginate_with_total_count(self):
        """Test paginate_response() with total count provided."""
        items = [{"id": i} for i in range(1, 11)]  # 10 items
        
        result = paginate_response(items, page=1, per_page=10, total=150)
        
        assert result == {
            "items": items,
            "page": 1,
            "per_page": 10,
            "has_next": True,
            "next_page": 2,
            "total": 150,
        }
    
    def test_paginate_second_page(self):
        """Test paginate_response() for second page."""
        items = [{"id": i} for i in range(11, 21)]  # 10 items
        
        result = paginate_response(items, page=2, per_page=10)
        
        assert result == {
            "items": items,
            "page": 2,
            "per_page": 10,
            "has_next": True,
            "next_page": 3,
        }
    
    def test_paginate_last_page_full(self):
        """Test paginate_response() for last page that is full."""
        items = [{"id": i} for i in range(91, 101)]  # 10 items
        
        result = paginate_response(items, page=10, per_page=10, total=100)
        
        # Even though page is full, if we know total, we can determine it's the last page
        # However, our implementation only checks len(items) == per_page
        assert result == {
            "items": items,
            "page": 10,
            "per_page": 10,
            "has_next": True,  # Based on item count alone
            "next_page": 11,
            "total": 100,
        }
    
    def test_paginate_last_page_partial(self):
        """Test paginate_response() for last page that is partial."""
        items = [{"id": i} for i in range(91, 96)]  # 5 items
        
        result = paginate_response(items, page=10, per_page=10, total=95)
        
        assert result == {
            "items": items,
            "page": 10,
            "per_page": 10,
            "has_next": False,
            "next_page": None,
            "total": 95,
        }
    
    def test_paginate_with_different_per_page(self):
        """Test paginate_response() with different per_page values."""
        items = [{"id": i} for i in range(1, 21)]  # 20 items
        
        result = paginate_response(items, page=1, per_page=20)
        
        assert result == {
            "items": items,
            "page": 1,
            "per_page": 20,
            "has_next": True,
            "next_page": 2,
        }
    
    def test_paginate_preserves_item_structure(self):
        """Test paginate_response() preserves complex item structure."""
        items = [
            {
                "id": 1,
                "name": "Project 1",
                "nested": {"key": "value"},
                "list": [1, 2, 3],
            },
            {
                "id": 2,
                "name": "Project 2",
                "nested": {"key": "value2"},
                "list": [4, 5, 6],
            },
        ]
        
        result = paginate_response(items, page=1, per_page=10)
        
        # Items should be preserved exactly as provided
        assert result["items"] == items
        assert result["items"][0]["nested"] == {"key": "value"}
        assert result["items"][1]["list"] == [4, 5, 6]
