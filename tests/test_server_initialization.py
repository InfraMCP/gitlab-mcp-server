"""Tests for FastMCP server initialization."""

import pytest
from gitlab_mcp_server import mcp, main


class TestServerInitialization:
    """Test suite for FastMCP server initialization."""
    
    def test_mcp_server_instance_exists(self):
        """Test that mcp server instance is created."""
        assert mcp is not None
    
    def test_mcp_server_name(self):
        """Test that mcp server has correct name."""
        assert mcp.name == "GitLab Server"
    
    def test_main_function_exists(self):
        """Test that main function is exported."""
        assert callable(main)
    
    def test_main_function_has_docstring(self):
        """Test that main function has proper documentation."""
        assert main.__doc__ is not None
        assert "entry point" in main.__doc__.lower()
