"""Shared pytest fixtures for GitLab MCP Server tests."""

import pytest


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set up mock environment variables."""
    monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com")
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test-token-1234567890")
    monkeypatch.setenv("GITLAB_VERIFY_SSL", "true")
    return {
        "GITLAB_URL": "https://gitlab.example.com",
        "GITLAB_TOKEN": "glpat-test-token-1234567890",
        "GITLAB_VERIFY_SSL": "true",
    }


@pytest.fixture
def mock_env_vars_minimal(monkeypatch):
    """Fixture with minimal environment variables (only token)."""
    monkeypatch.setenv("GITLAB_TOKEN", "glpat-test-token-1234567890")
    # Clear other variables
    monkeypatch.delenv("GITLAB_URL", raising=False)
    monkeypatch.delenv("GITLAB_VERIFY_SSL", raising=False)
    return {
        "GITLAB_TOKEN": "glpat-test-token-1234567890",
    }
