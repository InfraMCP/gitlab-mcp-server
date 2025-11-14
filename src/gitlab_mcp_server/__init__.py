"""GitLab MCP Server - Model Context Protocol server for GitLab."""

__version__ = "0.1.0"

from .errors import (
    format_http_error,
    format_connection_error,
    format_timeout_error,
    format_validation_error,
    handle_gitlab_errors,
)

from .server import (
    mcp,
    main,
    validate_project_id,
    validate_branch_name,
    validate_pagination,
    validate_iid,
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

__all__ = [
    "mcp",
    "main",
    "format_http_error",
    "format_connection_error",
    "format_timeout_error",
    "format_validation_error",
    "handle_gitlab_errors",
    "validate_project_id",
    "validate_branch_name",
    "validate_pagination",
    "validate_iid",
    "list_merge_requests",
    "get_merge_request",
    "create_merge_request",
    "update_merge_request",
    "merge_merge_request",
    "approve_merge_request",
    "get_merge_request_changes",
    "add_merge_request_comment",
    "list_merge_request_comments",
]
