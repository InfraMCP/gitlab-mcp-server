"""Unit tests for input validation functions."""

import pytest

from gitlab_mcp_server.server import (
    validate_project_id,
    validate_branch_name,
    validate_pagination,
)


class TestValidateProjectId:
    """Tests for validate_project_id() function."""
    
    def test_valid_positive_integer(self):
        """Test validate_project_id() with valid positive integer."""
        result = validate_project_id(123)
        assert result == 123
    
    def test_valid_string_integer(self):
        """Test validate_project_id() with string that can be converted to integer."""
        result = validate_project_id("456")
        assert result == 456
    
    def test_large_positive_integer(self):
        """Test validate_project_id() with large positive integer."""
        result = validate_project_id(999999999)
        assert result == 999999999
    
    def test_zero_raises_error(self):
        """Test validate_project_id() raises ValueError for zero."""
        with pytest.raises(ValueError) as exc_info:
            validate_project_id(0)
        
        assert "must be a positive integer" in str(exc_info.value)
        assert "got: 0" in str(exc_info.value)
    
    def test_negative_integer_raises_error(self):
        """Test validate_project_id() raises ValueError for negative integer."""
        with pytest.raises(ValueError) as exc_info:
            validate_project_id(-5)
        
        assert "must be a positive integer" in str(exc_info.value)
        assert "got: -5" in str(exc_info.value)
    
    def test_non_integer_string_raises_error(self):
        """Test validate_project_id() raises ValueError for non-integer string."""
        with pytest.raises(ValueError) as exc_info:
            validate_project_id("abc")
        
        assert "must be an integer" in str(exc_info.value)
        assert "got str" in str(exc_info.value)
    
    def test_float_raises_error(self):
        """Test validate_project_id() raises ValueError for float."""
        with pytest.raises(ValueError) as exc_info:
            validate_project_id(12.5)
        
        assert "must be an integer" in str(exc_info.value)
        assert "got float" in str(exc_info.value)
    
    def test_none_raises_error(self):
        """Test validate_project_id() raises ValueError for None."""
        with pytest.raises(ValueError) as exc_info:
            validate_project_id(None)
        
        assert "must be an integer" in str(exc_info.value)
    
    def test_list_raises_error(self):
        """Test validate_project_id() raises ValueError for list."""
        with pytest.raises(ValueError) as exc_info:
            validate_project_id([1, 2, 3])
        
        assert "must be an integer" in str(exc_info.value)
        assert "got list" in str(exc_info.value)


class TestValidateBranchName:
    """Tests for validate_branch_name() function."""
    
    def test_valid_branch_name(self):
        """Test validate_branch_name() with valid branch name."""
        result = validate_branch_name("main")
        assert result == "main"
    
    def test_branch_name_with_slashes(self):
        """Test validate_branch_name() with branch name containing slashes."""
        result = validate_branch_name("feature/new-feature")
        assert result == "feature/new-feature"
    
    def test_branch_name_with_special_chars(self):
        """Test validate_branch_name() with special characters."""
        result = validate_branch_name("bugfix/issue-123_fix")
        assert result == "bugfix/issue-123_fix"
    
    def test_branch_name_with_leading_trailing_spaces(self):
        """Test validate_branch_name() strips leading/trailing whitespace."""
        result = validate_branch_name("  develop  ")
        assert result == "develop"
    
    def test_empty_string_raises_error(self):
        """Test validate_branch_name() raises ValueError for empty string."""
        with pytest.raises(ValueError) as exc_info:
            validate_branch_name("")
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_whitespace_only_raises_error(self):
        """Test validate_branch_name() raises ValueError for whitespace-only string."""
        with pytest.raises(ValueError) as exc_info:
            validate_branch_name("   ")
        
        assert "cannot be empty" in str(exc_info.value)
    
    def test_integer_raises_error(self):
        """Test validate_branch_name() raises ValueError for integer."""
        with pytest.raises(ValueError) as exc_info:
            validate_branch_name(123)
        
        assert "must be a string" in str(exc_info.value)
        assert "got int" in str(exc_info.value)
    
    def test_none_raises_error(self):
        """Test validate_branch_name() raises ValueError for None."""
        with pytest.raises(ValueError) as exc_info:
            validate_branch_name(None)
        
        assert "must be a string" in str(exc_info.value)
    
    def test_list_raises_error(self):
        """Test validate_branch_name() raises ValueError for list."""
        with pytest.raises(ValueError) as exc_info:
            validate_branch_name(["main", "develop"])
        
        assert "must be a string" in str(exc_info.value)
        assert "got list" in str(exc_info.value)


class TestValidatePagination:
    """Tests for validate_pagination() function."""
    
    def test_valid_pagination_defaults(self):
        """Test validate_pagination() with default values."""
        page, per_page = validate_pagination()
        assert page == 1
        assert per_page == 20
    
    def test_valid_pagination_custom_values(self):
        """Test validate_pagination() with custom valid values."""
        page, per_page = validate_pagination(page=5, per_page=50)
        assert page == 5
        assert per_page == 50
    
    def test_valid_pagination_string_integers(self):
        """Test validate_pagination() with string integers."""
        page, per_page = validate_pagination(page="3", per_page="25")
        assert page == 3
        assert per_page == 25
    
    def test_valid_pagination_max_per_page(self):
        """Test validate_pagination() with maximum per_page value."""
        page, per_page = validate_pagination(page=1, per_page=100)
        assert page == 1
        assert per_page == 100
    
    def test_valid_pagination_min_values(self):
        """Test validate_pagination() with minimum valid values."""
        page, per_page = validate_pagination(page=1, per_page=1)
        assert page == 1
        assert per_page == 1
    
    def test_page_zero_raises_error(self):
        """Test validate_pagination() raises ValueError for page=0."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=0, per_page=20)
        
        assert "page must be >= 1" in str(exc_info.value)
        assert "got: 0" in str(exc_info.value)
    
    def test_page_negative_raises_error(self):
        """Test validate_pagination() raises ValueError for negative page."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=-1, per_page=20)
        
        assert "page must be >= 1" in str(exc_info.value)
        assert "got: -1" in str(exc_info.value)
    
    def test_per_page_zero_raises_error(self):
        """Test validate_pagination() raises ValueError for per_page=0."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=1, per_page=0)
        
        assert "per_page must be >= 1" in str(exc_info.value)
        assert "got: 0" in str(exc_info.value)
    
    def test_per_page_negative_raises_error(self):
        """Test validate_pagination() raises ValueError for negative per_page."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=1, per_page=-10)
        
        assert "per_page must be >= 1" in str(exc_info.value)
        assert "got: -10" in str(exc_info.value)
    
    def test_per_page_exceeds_max_raises_error(self):
        """Test validate_pagination() raises ValueError for per_page > 100."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=1, per_page=101)
        
        assert "per_page must be <= 100" in str(exc_info.value)
        assert "got: 101" in str(exc_info.value)
    
    def test_per_page_large_value_raises_error(self):
        """Test validate_pagination() raises ValueError for very large per_page."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=1, per_page=1000)
        
        assert "per_page must be <= 100" in str(exc_info.value)
        assert "got: 1000" in str(exc_info.value)
    
    def test_page_non_integer_string_raises_error(self):
        """Test validate_pagination() raises ValueError for non-integer page string."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page="abc", per_page=20)
        
        assert "page must be an integer" in str(exc_info.value)
        assert "got str" in str(exc_info.value)
    
    def test_per_page_non_integer_string_raises_error(self):
        """Test validate_pagination() raises ValueError for non-integer per_page string."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=1, per_page="xyz")
        
        assert "per_page must be an integer" in str(exc_info.value)
        assert "got str" in str(exc_info.value)
    
    def test_page_float_raises_error(self):
        """Test validate_pagination() raises ValueError for float page."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=1.5, per_page=20)
        
        assert "page must be an integer" in str(exc_info.value)
        assert "got float" in str(exc_info.value)
    
    def test_per_page_float_raises_error(self):
        """Test validate_pagination() raises ValueError for float per_page."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=1, per_page=20.5)
        
        assert "per_page must be an integer" in str(exc_info.value)
        assert "got float" in str(exc_info.value)
    
    def test_page_none_raises_error(self):
        """Test validate_pagination() raises ValueError for None page."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=None, per_page=20)
        
        assert "page must be an integer" in str(exc_info.value)
    
    def test_per_page_none_raises_error(self):
        """Test validate_pagination() raises ValueError for None per_page."""
        with pytest.raises(ValueError) as exc_info:
            validate_pagination(page=1, per_page=None)
        
        assert "per_page must be an integer" in str(exc_info.value)
