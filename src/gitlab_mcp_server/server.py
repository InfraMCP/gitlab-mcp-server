"""GitLab MCP Server - Main server implementation."""
# pylint: disable=too-many-lines

import os
import urllib.parse
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from .errors import handle_gitlab_errors

# Create MCP server instance
mcp = FastMCP("GitLab Server")


def get_gitlab_config() -> dict[str, Any]:
    """Get GitLab configuration from environment variables.

    Returns:
        dict: Configuration with keys:
            - base_url: GitLab instance URL
            - token: Personal Access Token
            - verify_ssl: SSL verification flag

    Raises:
        ValueError: If GITLAB_TOKEN is missing or URL is invalid
    """
    # Get token (required)
    token = os.getenv("GITLAB_TOKEN")
    if not token:
        raise ValueError(
            "GITLAB_TOKEN environment variable is required. "
            "Generate a token at https://gitlab.com/-/profile/personal_access_tokens"
        )

    # Get URL (optional, defaults to gitlab.com)
    base_url = os.getenv("GITLAB_URL", "https://gitlab.com")

    # Validate URL format
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        raise ValueError(
            f"GITLAB_URL must start with http:// or https://, got: {base_url}"
        )

    # Strip trailing slashes
    base_url = base_url.rstrip("/")

    # Get SSL verification setting (optional, defaults to true)
    verify_ssl_str = os.getenv("GITLAB_VERIFY_SSL", "true").lower()
    verify_ssl = verify_ssl_str in ("true", "1", "yes")

    return {
        "base_url": base_url,
        "token": token,
        "verify_ssl": verify_ssl,
    }


def make_request(
    method: str,
    endpoint: str,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    **kwargs: Any
) -> dict[str, Any] | list[Any]:
    """Make authenticated HTTP request to GitLab API.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path (without /api/v4/ prefix)
        params: Query parameters
        json: JSON request body
        **kwargs: Additional httpx client options

    Returns:
        API response as dict or list

    Raises:
        httpx.HTTPStatusError: On HTTP error responses
        httpx.TimeoutException: On request timeout
        httpx.ConnectError: On connection failure
    """
    config = get_gitlab_config()

    # Construct full URL
    url = f"{config['base_url']}/api/v4/{endpoint}"

    # Prepare headers
    headers = {
        "PRIVATE-TOKEN": config["token"],
        "Content-Type": "application/json",
        "User-Agent": "gitlab-mcp-server/0.1.0",
    }

    # Make request with context manager for connection pooling
    with httpx.Client(verify=config["verify_ssl"], timeout=30.0) as client:
        response = client.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=headers,
            **kwargs
        )

        # Raise exception for HTTP errors
        response.raise_for_status()

        # Return JSON response
        return response.json()


# Default field sets for each resource type
DEFAULT_FIELDS = {
    "project": ["id", "name", "path", "description", "web_url", "visibility"],
    "issue": ["id", "iid", "title", "state", "author", "created_at", "web_url"],
    "merge_request": [
        "id", "iid", "title", "state", "source_branch",
        "target_branch", "author", "web_url"
    ],
    "commit": ["id", "short_id", "title", "author_name", "created_at", "web_url"],
    "branch": ["name", "commit", "protected", "web_url"],
    "pipeline": ["id", "status", "ref", "created_at", "web_url"],
    "job": ["id", "name", "status", "stage", "created_at", "web_url"],
    "user": ["id", "username", "name", "avatar_url"],
    "group": ["id", "name", "path", "description", "web_url"],
    "label": ["id", "name", "color", "description"],
    "milestone": ["id", "iid", "title", "state", "due_date", "web_url"],
}


def filter_fields(
    data: dict[str, Any] | list[Any],
    include_fields: str | list[str] | None = None,
    resource_type: str | None = None
) -> dict[str, Any] | list[Any]:
    """Filter API response to include only specified fields.

    Args:
        data: API response data (dict or list of dicts)
        include_fields: List of field names to include, comma-separated string,
            or "all" for no filtering
        resource_type: Resource type for default fields (if include_fields is None)

    Returns:
        Filtered data with only specified fields
    """
    # Handle "all" keyword - return unfiltered data
    if include_fields == "all":
        return data

    # Handle comma-separated string of fields
    if isinstance(include_fields, str):
        include_fields = [f.strip() for f in include_fields.split(",")]

    # Determine which fields to include
    if include_fields is not None:
        fields = include_fields
    elif resource_type and resource_type in DEFAULT_FIELDS:
        fields = DEFAULT_FIELDS[resource_type]
    else:
        # No filtering - return as-is
        return data

    # Convert to set for O(1) lookup performance
    field_set = set(fields)

    # Helper function to filter a single object
    def filter_object(obj: dict[str, Any]) -> dict[str, Any]:
        """Filter a single dictionary object."""
        if not isinstance(obj, dict):
            return obj

        # Use dict comprehension with set lookup for better performance
        return {k: v for k, v in obj.items() if k in field_set}

    # Handle list of objects
    if isinstance(data, list):
        return [filter_object(item) for item in data]

    # Handle single object
    return filter_object(data)


def paginate_response(
    items: list[Any],
    page: int,
    per_page: int,
    total: int | None = None
) -> dict[str, Any]:
    """Wrap list response with pagination metadata.

    Args:
        items: List of items for current page
        page: Current page number
        per_page: Items per page
        total: Total count (if known)

    Returns:
        Paginated response with metadata
    """
    # Calculate if there are more pages
    has_next = len(items) == per_page

    # Build response
    response: dict[str, Any] = {
        "items": items,
        "page": page,
        "per_page": per_page,
        "has_next": has_next,
        "next_page": page + 1 if has_next else None,
    }

    # Add total if available
    if total is not None:
        response["total"] = total

    return response


def validate_project_id(project_id: Any) -> int:
    """Validate project ID parameter.

    Args:
        project_id: Project ID to validate (should be positive integer)

    Returns:
        int: Validated project ID

    Raises:
        ValueError: If project_id is not a positive integer
    """
    # Type checking - reject floats explicitly
    if isinstance(project_id, float):
        raise ValueError(
            f"project_id must be an integer, got {type(project_id).__name__}: {project_id}"
        )

    # Type checking - convert strings to int if possible
    if not isinstance(project_id, int):
        try:
            project_id = int(project_id)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"project_id must be an integer, got {type(project_id).__name__}: {project_id}"
            ) from e

    # Range checking
    if project_id <= 0:
        raise ValueError(
            f"project_id must be a positive integer, got: {project_id}"
        )

    return project_id


def validate_branch_name(branch_name: Any) -> str:
    """Validate branch name parameter.

    Args:
        branch_name: Branch name to validate (should be non-empty string)

    Returns:
        str: Validated branch name

    Raises:
        ValueError: If branch_name is not a valid string
    """
    # Type checking
    if not isinstance(branch_name, str):
        raise ValueError(
            f"branch_name must be a string, got {type(branch_name).__name__}: {branch_name}"
        )

    # Check for empty string
    if not branch_name.strip():
        raise ValueError("branch_name cannot be empty or whitespace only")

    # Return stripped branch name
    return branch_name.strip()


def validate_pagination(page: Any = 1, per_page: Any = 20) -> tuple[int, int]:
    """Validate pagination parameters.

    Args:
        page: Page number (should be positive integer, default: 1)
        per_page: Items per page (should be positive integer 1-100, default: 20)

    Returns:
        tuple[int, int]: Validated (page, per_page) tuple

    Raises:
        ValueError: If pagination parameters are invalid
    """
    # Validate page - reject floats explicitly
    if isinstance(page, float):
        raise ValueError(
            f"page must be an integer, got {type(page).__name__}: {page}"
        )

    if not isinstance(page, int):
        try:
            page = int(page)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"page must be an integer, got {type(page).__name__}: {page}"
            ) from e

    if page < 1:
        raise ValueError(f"page must be >= 1, got: {page}")

    # Validate per_page - reject floats explicitly
    if isinstance(per_page, float):
        raise ValueError(
            f"per_page must be an integer, got {type(per_page).__name__}: {per_page}"
        )

    if not isinstance(per_page, int):
        try:
            per_page = int(per_page)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"per_page must be an integer, got {type(per_page).__name__}: {per_page}"
            ) from e

    if per_page < 1:
        raise ValueError(f"per_page must be >= 1, got: {per_page}")

    if per_page > 100:
        raise ValueError(f"per_page must be <= 100, got: {per_page}")

    return page, per_page


def validate_iid(iid: Any, param_name: str = "iid") -> int:
    """Validate IID (internal ID) parameter.

    Used for issue_iid, mr_iid, and other internal ID parameters.

    Args:
        iid: IID to validate (should be positive integer)
        param_name: Parameter name for error messages (default: "iid")

    Returns:
        int: Validated IID

    Raises:
        ValueError: If iid is not a positive integer
    """
    # Type checking - reject floats explicitly
    if isinstance(iid, float):
        raise ValueError(
            f"{param_name} must be an integer, got {type(iid).__name__}: {iid}"
        )

    # Type checking - convert strings to int if possible
    if not isinstance(iid, int):
        try:
            iid = int(iid)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"{param_name} must be an integer, got {type(iid).__name__}: {iid}"
            ) from e

    # Range checking
    if iid <= 0:
        raise ValueError(
            f"{param_name} must be a positive integer, got: {iid}"
        )

    return iid


def validate_group_id(group_id: Any) -> int:
    """Validate group ID parameter.

    Args:
        group_id: Group ID to validate (should be positive integer)

    Returns:
        int: Validated group ID

    Raises:
        ValueError: If group_id is not a positive integer
    """
    if isinstance(group_id, float):
        raise ValueError(
            f"group_id must be an integer, got {type(group_id).__name__}: {group_id}"
        )

    if not isinstance(group_id, int):
        try:
            group_id = int(group_id)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"group_id must be an integer, got {type(group_id).__name__}: {group_id}"
            ) from e

    if group_id <= 0:
        raise ValueError(
            f"group_id must be a positive integer, got: {group_id}"
        )

    return group_id


def validate_user_id(user_id: Any) -> int:
    """Validate user ID parameter.

    Args:
        user_id: User ID to validate (should be positive integer)

    Returns:
        int: Validated user ID

    Raises:
        ValueError: If user_id is not a positive integer
    """
    if isinstance(user_id, float):
        raise ValueError(
            f"user_id must be an integer, got {type(user_id).__name__}: {user_id}"
        )

    if not isinstance(user_id, int):
        try:
            user_id = int(user_id)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"user_id must be an integer, got {type(user_id).__name__}: {user_id}"
            ) from e

    if user_id <= 0:
        raise ValueError(
            f"user_id must be a positive integer, got: {user_id}"
        )

    return user_id


# GitLab access level constants
ACCESS_LEVEL_GUEST = 10
ACCESS_LEVEL_REPORTER = 20
ACCESS_LEVEL_DEVELOPER = 30
ACCESS_LEVEL_MAINTAINER = 40
ACCESS_LEVEL_OWNER = 50

VALID_ACCESS_LEVELS = (
    ACCESS_LEVEL_GUEST,
    ACCESS_LEVEL_REPORTER,
    ACCESS_LEVEL_DEVELOPER,
    ACCESS_LEVEL_MAINTAINER,
    ACCESS_LEVEL_OWNER,
)


def validate_access_level(access_level: Any) -> int:
    """Validate GitLab access level parameter.

    Args:
        access_level: Access level to validate (should be 10, 20, 30, 40, or 50)

    Returns:
        int: Validated access level

    Raises:
        ValueError: If access_level is not a valid access level
    """
    if isinstance(access_level, float):
        raise ValueError(
            f"access_level must be an integer, got {type(access_level).__name__}: {access_level}"
        )

    if not isinstance(access_level, int):
        try:
            access_level = int(access_level)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"access_level must be an integer, got "
                f"{type(access_level).__name__}: {access_level}"
            ) from e

    if access_level not in VALID_ACCESS_LEVELS:
        raise ValueError(
            f"access_level must be one of {VALID_ACCESS_LEVELS} "
            f"(10=Guest, 20=Reporter, 30=Developer, 40=Maintainer, 50=Owner), got: {access_level}"
        )

    return access_level


def validate_non_empty_string(value: Any, param_name: str) -> str:
    """Validate that a parameter is a non-empty string.

    Args:
        value: Value to validate
        param_name: Parameter name for error messages

    Returns:
        str: Validated and stripped string

    Raises:
        ValueError: If value is not a non-empty string
    """
    if not isinstance(value, str):
        raise ValueError(
            f"{param_name} must be a string, got {type(value).__name__}: {value}"
        )

    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{param_name} cannot be empty or whitespace only")

    return stripped


# Valid GitLab visibility levels
VALID_VISIBILITY_LEVELS = ("private", "internal", "public")


def validate_visibility(visibility: str) -> str:
    """Validate GitLab visibility parameter.

    Args:
        visibility: Visibility level to validate

    Returns:
        str: Validated visibility level

    Raises:
        ValueError: If visibility is not valid
    """
    if visibility not in VALID_VISIBILITY_LEVELS:
        raise ValueError(
            f"visibility must be one of {VALID_VISIBILITY_LEVELS}, got: {visibility}"
        )
    return visibility


def validate_gitlab_connection() -> bool:
    """Validate GitLab connection on startup.

    Performs:
    1. URL format validation
    2. Connectivity test (GET /api/v4/version)
    3. Authentication test (GET /api/v4/user)
    4. Permission validation (GET /api/v4/projects)

    Returns:
        True if all validations pass

    Raises:
        ValueError: With detailed error message if validation fails
    """
    config = None
    try:
        # Get configuration (validates URL format and token presence)
        config = get_gitlab_config()

        # Test connectivity - GET /api/v4/version
        print("Testing GitLab connectivity...")
        version_data = make_request("GET", "version")
        version = version_data.get("version", "unknown")
        print(f"✅ Connected to GitLab {version}")

        # Test authentication - GET /api/v4/user
        print("Testing authentication...")
        user_data = make_request("GET", "user")
        username = user_data.get("username", "unknown")
        print(f"✅ Authenticated as: {username}")

        # Test permissions - GET /api/v4/projects
        print("Testing permissions...")
        try:
            make_request("GET", "projects", params={"per_page": 1})
            print("✅ Token has read access")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                print("⚠️  Token has limited permissions - some operations may fail")
            else:
                raise

        return True

    except ValueError as e:
        # Configuration error
        raise ValueError(f"Configuration error: {e}") from e
    except httpx.ConnectError as e:
        # Connection failure
        base_url = config['base_url'] if config else "GitLab"
        raise ValueError(
            f"Failed to connect to GitLab at {base_url}. "
            "Check your network connection and GITLAB_URL setting."
        ) from e
    except httpx.HTTPStatusError as e:
        # HTTP error
        if e.response.status_code == 401:
            raise ValueError(
                "Authentication failed. Your GITLAB_TOKEN may be invalid or "
                "expired. Generate a new token at "
                "https://gitlab.com/-/profile/personal_access_tokens"
            ) from e
        raise ValueError(
            f"GitLab API error: {e.response.status_code} - {e.response.text}"
        ) from e
    except httpx.TimeoutException as e:
        # Timeout
        base_url = config['base_url'] if config else "GitLab"
        raise ValueError(
            f"Connection timeout to {base_url}. "
            "The GitLab instance may be slow or unreachable."
        ) from e


# ============================================================================
# Project Management Tools
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def list_projects(
    per_page: int = 20,
    page: int = 1,
    search: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List GitLab projects with pagination and optional search.

    Args:
        per_page: Number of projects per page (1-100, default: 20)
        page: Page number (default: 1)
        search: Optional search query to filter projects by name/path
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with project list and metadata
    """
    # Validate pagination parameters
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add search parameter if provided
    if search:
        params["search"] = search

    # Make API request
    response = make_request("GET", "projects", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "project")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def get_project(
    project_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get details of a specific GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Project details
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Make API request
    response = make_request("GET", f"projects/{project_id}")

    # Apply field filtering
    return filter_fields(response, include_fields, "project")


@mcp.tool()
@handle_gitlab_errors
def create_project(
    name: str,
    description: str | None = None,
    visibility: str = "private",
    initialize_with_readme: bool = False,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new GitLab project.

    Args:
        name: Project name (required)
        description: Project description (optional)
        visibility: Project visibility - "private", "internal", or "public" (default: "private")
        initialize_with_readme: Initialize project with README file (default: False)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created project details
    """
    # Build request body
    data: dict[str, Any] = {
        "name": name,
        "visibility": visibility,
        "initialize_with_readme": initialize_with_readme,
    }

    # Add optional description
    if description:
        data["description"] = description

    # Make API request
    response = make_request("POST", "projects", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "project")


@mcp.tool()
@handle_gitlab_errors
def update_project(
    project_id: int,
    name: str | None = None,
    description: str | None = None,
    visibility: str | None = None,
    default_branch: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Update an existing GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        name: New project name (optional)
        description: New project description (optional)
        visibility: New visibility - "private", "internal", or "public" (optional)
        default_branch: New default branch name (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Updated project details
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Build request body with only provided fields
    data: dict[str, Any] = {}

    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if visibility is not None:
        data["visibility"] = visibility
    if default_branch is not None:
        data["default_branch"] = default_branch

    # Make API request
    response = make_request("PUT", f"projects/{project_id}", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "project")


@mcp.tool()
@handle_gitlab_errors
def delete_project(project_id: int) -> dict[str, Any]:
    """Delete a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)

    Returns:
        Success confirmation
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Make API request
    make_request("DELETE", f"projects/{project_id}")

    # Return success confirmation
    return {
        "success": True,
        "message": f"Project {project_id} deleted successfully"
    }


# ============================================================================
# Issue Management Tools
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def list_issues(
    project_id: int,
    per_page: int = 20,
    page: int = 1,
    state: str | None = None,
    labels: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List issues in a GitLab project with pagination and filtering.

    Args:
        project_id: Project ID (must be positive integer)
        per_page: Number of issues per page (1-100, default: 20)
        page: Page number (default: 1)
        state: Filter by state - "opened", "closed", or "all" (optional)
        labels: Comma-separated list of label names to filter by (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with issue list and metadata
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Validate pagination parameters
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add optional filters
    if state:
        params["state"] = state
    if labels:
        params["labels"] = labels

    # Make API request
    response = make_request("GET", f"projects/{project_id}/issues", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "issue")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def get_issue(
    project_id: int,
    issue_iid: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get details of a specific issue in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        issue_iid: Issue IID (internal ID, must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Issue details
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Validate issue_iid
    if isinstance(issue_iid, float):
        raise ValueError(
            f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
        )

    if not isinstance(issue_iid, int):
        try:
            issue_iid = int(issue_iid)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
            ) from e

    if issue_iid <= 0:
        raise ValueError(
            f"issue_iid must be a positive integer, got: {issue_iid}"
        )

    # Make API request
    response = make_request("GET", f"projects/{project_id}/issues/{issue_iid}")

    # Apply field filtering
    return filter_fields(response, include_fields, "issue")


@mcp.tool()
@handle_gitlab_errors
def create_issue(
    project_id: int,
    title: str,
    description: str | None = None,
    labels: str | None = None,
    assignee_ids: list[int] | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new issue in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        title: Issue title (required)
        description: Issue description (optional)
        labels: Comma-separated list of label names (optional)
        assignee_ids: List of user IDs to assign to the issue (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created issue details
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Build request body
    data: dict[str, Any] = {
        "title": title,
    }

    # Add optional fields
    if description:
        data["description"] = description
    if labels:
        data["labels"] = labels
    if assignee_ids:
        data["assignee_ids"] = assignee_ids

    # Make API request
    response = make_request("POST", f"projects/{project_id}/issues", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "issue")


@mcp.tool()
@handle_gitlab_errors
def update_issue(
    project_id: int,
    issue_iid: int,
    title: str | None = None,
    description: str | None = None,
    labels: str | None = None,
    assignee_ids: list[int] | None = None,
    state_event: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Update an existing issue in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        issue_iid: Issue IID (internal ID, must be positive integer)
        title: New issue title (optional)
        description: New issue description (optional)
        labels: Comma-separated list of label names (optional)
        assignee_ids: List of user IDs to assign to the issue (optional)
        state_event: State event - "close" or "reopen" (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Updated issue details
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Validate issue_iid
    if isinstance(issue_iid, float):
        raise ValueError(
            f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
        )

    if not isinstance(issue_iid, int):
        try:
            issue_iid = int(issue_iid)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
            ) from e

    if issue_iid <= 0:
        raise ValueError(
            f"issue_iid must be a positive integer, got: {issue_iid}"
        )

    # Build request body with only provided fields
    data: dict[str, Any] = {}

    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if labels is not None:
        data["labels"] = labels
    if assignee_ids is not None:
        data["assignee_ids"] = assignee_ids
    if state_event is not None:
        data["state_event"] = state_event

    # Make API request
    response = make_request("PUT", f"projects/{project_id}/issues/{issue_iid}", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "issue")


@mcp.tool()
@handle_gitlab_errors
def close_issue(
    project_id: int,
    issue_iid: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Close an issue in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        issue_iid: Issue IID (internal ID, must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Closed issue details
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Validate issue_iid
    if isinstance(issue_iid, float):
        raise ValueError(
            f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
        )

    if not isinstance(issue_iid, int):
        try:
            issue_iid = int(issue_iid)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
            ) from e

    if issue_iid <= 0:
        raise ValueError(
            f"issue_iid must be a positive integer, got: {issue_iid}"
        )

    # Make API request with state_event=close
    data = {"state_event": "close"}
    response = make_request("PUT", f"projects/{project_id}/issues/{issue_iid}", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "issue")


@mcp.tool()
@handle_gitlab_errors
def reopen_issue(
    project_id: int,
    issue_iid: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Reopen a closed issue in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        issue_iid: Issue IID (internal ID, must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Reopened issue details
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Validate issue_iid
    if isinstance(issue_iid, float):
        raise ValueError(
            f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
        )

    if not isinstance(issue_iid, int):
        try:
            issue_iid = int(issue_iid)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
            ) from e

    if issue_iid <= 0:
        raise ValueError(
            f"issue_iid must be a positive integer, got: {issue_iid}"
        )

    # Make API request with state_event=reopen
    data = {"state_event": "reopen"}
    response = make_request("PUT", f"projects/{project_id}/issues/{issue_iid}", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "issue")


@mcp.tool()
@handle_gitlab_errors
def add_issue_comment(
    project_id: int,
    issue_iid: int,
    body: str
) -> dict[str, Any]:
    """Add a comment to an issue in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        issue_iid: Issue IID (internal ID, must be positive integer)
        body: Comment text (required)

    Returns:
        Created comment details
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Validate issue_iid
    if isinstance(issue_iid, float):
        raise ValueError(
            f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
        )

    if not isinstance(issue_iid, int):
        try:
            issue_iid = int(issue_iid)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
            ) from e

    if issue_iid <= 0:
        raise ValueError(
            f"issue_iid must be a positive integer, got: {issue_iid}"
        )

    # Build request body
    data = {"body": body}

    # Make API request
    response = make_request("POST", f"projects/{project_id}/issues/{issue_iid}/notes", json=data)

    return response


@mcp.tool()
@handle_gitlab_errors
def list_issue_comments(
    project_id: int,
    issue_iid: int,
    per_page: int = 20,
    page: int = 1
) -> dict[str, Any]:
    """List comments on an issue in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        issue_iid: Issue IID (internal ID, must be positive integer)
        per_page: Number of comments per page (1-100, default: 20)
        page: Page number (default: 1)

    Returns:
        Paginated response with comment list and metadata
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Validate issue_iid
    if isinstance(issue_iid, float):
        raise ValueError(
            f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
        )

    if not isinstance(issue_iid, int):
        try:
            issue_iid = int(issue_iid)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"issue_iid must be an integer, got {type(issue_iid).__name__}: {issue_iid}"
            ) from e

    if issue_iid <= 0:
        raise ValueError(
            f"issue_iid must be a positive integer, got: {issue_iid}"
        )

    # Validate pagination parameters
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Make API request
    response = make_request("GET", f"projects/{project_id}/issues/{issue_iid}/notes", params=params)

    # Wrap with pagination metadata
    return paginate_response(response, page, per_page)


# ============================================================================
# Merge Request Management Tools
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def list_merge_requests(
    project_id: int,
    per_page: int = 20,
    page: int = 1,
    state: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List merge requests in a GitLab project with pagination and filtering.

    Args:
        project_id: Project ID (must be positive integer)
        per_page: Number of merge requests per page (1-100, default: 20)
        page: Page number (default: 1)
        state: Filter by state - "opened", "closed", "merged", or "all" (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with merge request list and metadata
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    page, per_page = validate_pagination(page, per_page)

    # Validate state if provided
    if state and state not in ("opened", "closed", "merged", "all"):
        raise ValueError(
            f"state must be one of: opened, closed, merged, all. Got: {state}"
        )

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add optional filters
    if state:
        params["state"] = state

    # Make API request
    response = make_request("GET", f"projects/{project_id}/merge_requests", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "merge_request")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def get_merge_request(
    project_id: int,
    mr_iid: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get details of a specific merge request in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        mr_iid: Merge request IID (internal ID, must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Merge request details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    mr_iid = validate_iid(mr_iid, "mr_iid")

    # Make API request
    response = make_request("GET", f"projects/{project_id}/merge_requests/{mr_iid}")

    # Apply field filtering
    return filter_fields(response, include_fields, "merge_request")


@mcp.tool()
@handle_gitlab_errors
def create_merge_request(
    project_id: int,
    source_branch: str,
    target_branch: str,
    title: str,
    description: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new merge request in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        source_branch: Source branch name (required)
        target_branch: Target branch name (required)
        title: Merge request title (required)
        description: Merge request description (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created merge request details
    """
    # Validate project_id
    project_id = validate_project_id(project_id)

    # Validate branch names
    source_branch = validate_branch_name(source_branch)
    target_branch = validate_branch_name(target_branch)

    # Build request body
    data: dict[str, Any] = {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
    }

    # Add optional description
    if description:
        data["description"] = description

    # Make API request
    response = make_request("POST", f"projects/{project_id}/merge_requests", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "merge_request")


@mcp.tool()
@handle_gitlab_errors
def update_merge_request(
    project_id: int,
    mr_iid: int,
    title: str | None = None,
    description: str | None = None,
    target_branch: str | None = None,
    state_event: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Update an existing merge request in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        mr_iid: Merge request IID (internal ID, must be positive integer)
        title: New merge request title (optional)
        description: New merge request description (optional)
        target_branch: New target branch name (optional)
        state_event: State event - "close" or "reopen" (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Updated merge request details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    mr_iid = validate_iid(mr_iid, "mr_iid")

    # Validate state_event if provided
    if state_event and state_event not in ("close", "reopen"):
        raise ValueError(
            f"state_event must be 'close' or 'reopen', got: {state_event}"
        )

    # Build request body with only provided fields
    data: dict[str, Any] = {}

    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if target_branch is not None:
        data["target_branch"] = validate_branch_name(target_branch)
    if state_event is not None:
        data["state_event"] = state_event

    # Make API request
    response = make_request("PUT", f"projects/{project_id}/merge_requests/{mr_iid}", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "merge_request")


@mcp.tool()
@handle_gitlab_errors
def merge_merge_request(
    project_id: int,
    mr_iid: int,
    merge_commit_message: str | None = None
) -> dict[str, Any]:
    """Merge a merge request in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        mr_iid: Merge request IID (internal ID, must be positive integer)
        merge_commit_message: Custom merge commit message (optional)

    Returns:
        Merge result
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    mr_iid = validate_iid(mr_iid, "mr_iid")

    # Build request body
    data: dict[str, Any] = {}

    if merge_commit_message:
        data["merge_commit_message"] = merge_commit_message

    # Make API request
    response = make_request(
        "PUT", f"projects/{project_id}/merge_requests/{mr_iid}/merge", json=data
    )

    return response


@mcp.tool()
@handle_gitlab_errors
def approve_merge_request(
    project_id: int,
    mr_iid: int
) -> dict[str, Any]:
    """Approve a merge request in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        mr_iid: Merge request IID (internal ID, must be positive integer)

    Returns:
        Approval result
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    mr_iid = validate_iid(mr_iid, "mr_iid")

    # Make API request
    response = make_request("POST", f"projects/{project_id}/merge_requests/{mr_iid}/approve")

    return response


@mcp.tool()
@handle_gitlab_errors
def get_merge_request_changes(
    project_id: int,
    mr_iid: int
) -> dict[str, Any]:
    """Get changes/diff for a merge request in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        mr_iid: Merge request IID (internal ID, must be positive integer)

    Returns:
        Merge request changes/diff data
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    mr_iid = validate_iid(mr_iid, "mr_iid")

    # Make API request
    response = make_request("GET", f"projects/{project_id}/merge_requests/{mr_iid}/changes")

    return response


@mcp.tool()
@handle_gitlab_errors
def add_merge_request_comment(
    project_id: int,
    mr_iid: int,
    body: str
) -> dict[str, Any]:
    """Add a comment to a merge request in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        mr_iid: Merge request IID (internal ID, must be positive integer)
        body: Comment text (required)

    Returns:
        Created comment details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    mr_iid = validate_iid(mr_iid, "mr_iid")

    # Build request body
    data = {"body": body}

    # Make API request
    response = make_request(
        "POST", f"projects/{project_id}/merge_requests/{mr_iid}/notes", json=data
    )

    return response


@mcp.tool()
@handle_gitlab_errors
def list_merge_request_comments(
    project_id: int,
    mr_iid: int,
    per_page: int = 20,
    page: int = 1
) -> dict[str, Any]:
    """List comments on a merge request in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        mr_iid: Merge request IID (internal ID, must be positive integer)
        per_page: Number of comments per page (1-100, default: 20)
        page: Page number (default: 1)

    Returns:
        Paginated response with comment list and metadata
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    mr_iid = validate_iid(mr_iid, "mr_iid")
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Make API request
    response = make_request(
        "GET", f"projects/{project_id}/merge_requests/{mr_iid}/notes", params=params
    )

    # Wrap with pagination metadata
    return paginate_response(response, page, per_page)


# ============================================================================
# Repository Management Tools - Branch Operations
# ============================================================================

def encode_branch_name(branch: str) -> str:
    """URL encode a branch name for API requests.

    Branch names may contain special characters like slashes (e.g., 'feature/my-branch')
    that need to be properly encoded for use in API URLs.

    Args:
        branch: Branch name to encode

    Returns:
        URL-encoded branch name safe for use in API paths
    """
    return urllib.parse.quote(branch, safe='')


@mcp.tool()
@handle_gitlab_errors
def list_branches(
    project_id: int,
    per_page: int = 20,
    page: int = 1,
    search: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List branches in a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        per_page: Number of branches per page (1-100, default: 20)
        page: Page number (default: 1)
        search: Optional search query to filter branches by name
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with branch list and metadata
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add search parameter if provided
    if search:
        params["search"] = search

    # Make API request
    response = make_request("GET", f"projects/{project_id}/repository/branches", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "branch")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def get_branch(
    project_id: int,
    branch: str,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get details of a specific branch in a GitLab project repository.

    Branch names with special characters (e.g., 'feature/my-branch') are
    automatically URL-encoded for the API request.

    Args:
        project_id: Project ID (must be positive integer)
        branch: Branch name (required, e.g., 'main', 'feature/new-feature')
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Branch details including commit information and protection status
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    branch = validate_branch_name(branch)

    # URL encode branch name for API request
    encoded_branch = encode_branch_name(branch)

    # Make API request
    response = make_request("GET", f"projects/{project_id}/repository/branches/{encoded_branch}")

    # Apply field filtering
    return filter_fields(response, include_fields, "branch")


@mcp.tool()
@handle_gitlab_errors
def create_branch(
    project_id: int,
    branch: str,
    ref: str,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new branch in a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        branch: New branch name (required)
        ref: Source branch name, tag, or commit SHA to create branch from (required)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created branch details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    branch = validate_branch_name(branch)
    ref = validate_branch_name(ref)  # Reuse existing validator for ref

    # Build request body
    data: dict[str, Any] = {
        "branch": branch,
        "ref": ref,
    }

    # Make API request
    response = make_request("POST", f"projects/{project_id}/repository/branches", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "branch")


@mcp.tool()
@handle_gitlab_errors
def delete_branch(
    project_id: int,
    branch: str
) -> dict[str, Any]:
    """Delete a branch from a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        branch: Branch name to delete (required)

    Returns:
        Success confirmation
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    branch = validate_branch_name(branch)

    # URL encode branch name for API request
    encoded_branch = encode_branch_name(branch)

    # Make API request
    make_request("DELETE", f"projects/{project_id}/repository/branches/{encoded_branch}")

    # Return success confirmation
    return {
        "success": True,
        "message": f"Branch '{branch}' deleted successfully from project {project_id}"
    }


# ============================================================================
# Repository Management Tools - File Operations
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def get_file(
    project_id: int,
    file_path: str,
    ref: str = "main",
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get a file from a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        file_path: Path to the file in the repository (required)
        ref: Branch name, tag, or commit SHA (default: "main")
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        File details including content (base64 encoded)
    """
    # Validate parameters
    project_id = validate_project_id(project_id)

    # Validate file_path
    if not isinstance(file_path, str):
        raise ValueError(
            f"file_path must be a string, got {type(file_path).__name__}: {file_path}"
        )
    if not file_path.strip():
        raise ValueError("file_path cannot be empty or whitespace only")

    file_path = file_path.strip()

    # Validate ref
    if not isinstance(ref, str):
        raise ValueError(
            f"ref must be a string, got {type(ref).__name__}: {ref}"
        )
    if not ref.strip():
        raise ValueError("ref cannot be empty or whitespace only")

    ref = ref.strip()

    # URL encode file path for API request
    encoded_path = urllib.parse.quote(file_path, safe='')

    # Build query parameters
    params: dict[str, Any] = {
        "ref": ref,
    }

    # Make API request
    response = make_request(
        "GET", f"projects/{project_id}/repository/files/{encoded_path}",
        params=params
    )

    # Apply field filtering if requested
    if include_fields:
        return filter_fields(response, include_fields)

    return response


@mcp.tool()
@handle_gitlab_errors
def create_file(
    project_id: int,
    file_path: str,
    branch: str,
    content: str,
    commit_message: str,
    encoding: str = "text",
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new file in a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        file_path: Path where the file will be created (required)
        branch: Branch name to commit to (required)
        content: File content (required)
        commit_message: Commit message (required)
        encoding: Content encoding - "text" or "base64" (default: "text")
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created file details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)

    # Validate file_path
    if not isinstance(file_path, str):
        raise ValueError(
            f"file_path must be a string, got {type(file_path).__name__}: {file_path}"
        )
    if not file_path.strip():
        raise ValueError("file_path cannot be empty or whitespace only")

    file_path = file_path.strip()

    # Validate branch
    branch = validate_branch_name(branch)

    # Validate commit_message
    if not isinstance(commit_message, str):
        raise ValueError(
            f"commit_message must be a string, got "\
                f"{type(commit_message).__name__}: {commit_message}"
        )
    if not commit_message.strip():
        raise ValueError("commit_message cannot be empty or whitespace only")

    commit_message = commit_message.strip()

    # Validate encoding
    if encoding not in ("text", "base64"):
        raise ValueError(
            f"encoding must be 'text' or 'base64', got: {encoding}"
        )

    # URL encode file path for API request
    encoded_path = urllib.parse.quote(file_path, safe='')

    # Build request body
    data: dict[str, Any] = {
        "branch": branch,
        "content": content,
        "commit_message": commit_message,
        "encoding": encoding,
    }

    # Make API request
    response = make_request(
        "POST", f"projects/{project_id}/repository/files/{encoded_path}", json=data
    )

    # Apply field filtering if requested
    if include_fields:
        return filter_fields(response, include_fields)

    return response


@mcp.tool()
@handle_gitlab_errors
def update_file(
    project_id: int,
    file_path: str,
    branch: str,
    content: str,
    commit_message: str,
    encoding: str = "text",
    include_fields: str | None = None
) -> dict[str, Any]:
    """Update an existing file in a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        file_path: Path to the file to update (required)
        branch: Branch name to commit to (required)
        content: New file content (required)
        commit_message: Commit message (required)
        encoding: Content encoding - "text" or "base64" (default: "text")
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Updated file details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)

    # Validate file_path
    if not isinstance(file_path, str):
        raise ValueError(
            f"file_path must be a string, got {type(file_path).__name__}: {file_path}"
        )
    if not file_path.strip():
        raise ValueError("file_path cannot be empty or whitespace only")

    file_path = file_path.strip()

    # Validate branch
    branch = validate_branch_name(branch)

    # Validate commit_message
    if not isinstance(commit_message, str):
        raise ValueError(
            f"commit_message must be a string, got "\
                f"{type(commit_message).__name__}: {commit_message}"
        )
    if not commit_message.strip():
        raise ValueError("commit_message cannot be empty or whitespace only")

    commit_message = commit_message.strip()

    # Validate encoding
    if encoding not in ("text", "base64"):
        raise ValueError(
            f"encoding must be 'text' or 'base64', got: {encoding}"
        )

    # URL encode file path for API request
    encoded_path = urllib.parse.quote(file_path, safe='')

    # Build request body
    data: dict[str, Any] = {
        "branch": branch,
        "content": content,
        "commit_message": commit_message,
        "encoding": encoding,
    }

    # Make API request
    response = make_request(
        "PUT", f"projects/{project_id}/repository/files/{encoded_path}", json=data
    )

    # Apply field filtering if requested
    if include_fields:
        return filter_fields(response, include_fields)

    return response


@mcp.tool()
@handle_gitlab_errors
def delete_file(
    project_id: int,
    file_path: str,
    branch: str,
    commit_message: str
) -> dict[str, Any]:
    """Delete a file from a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        file_path: Path to the file to delete (required)
        branch: Branch name to commit to (required)
        commit_message: Commit message (required)

    Returns:
        Success confirmation
    """
    # Validate parameters
    project_id = validate_project_id(project_id)

    # Validate file_path
    if not isinstance(file_path, str):
        raise ValueError(
            f"file_path must be a string, got {type(file_path).__name__}: {file_path}"
        )
    if not file_path.strip():
        raise ValueError("file_path cannot be empty or whitespace only")

    file_path = file_path.strip()

    # Validate branch
    branch = validate_branch_name(branch)

    # Validate commit_message
    if not isinstance(commit_message, str):
        raise ValueError(
            f"commit_message must be a string, got "\
                f"{type(commit_message).__name__}: {commit_message}"
        )
    if not commit_message.strip():
        raise ValueError("commit_message cannot be empty or whitespace only")

    commit_message = commit_message.strip()

    # URL encode file path for API request
    encoded_path = urllib.parse.quote(file_path, safe='')

    # Build request body
    data: dict[str, Any] = {
        "branch": branch,
        "commit_message": commit_message,
    }

    # Make API request
    make_request("DELETE", f"projects/{project_id}/repository/files/{encoded_path}", json=data)

    # Return success confirmation
    return {
        "success": True,
        "message": (
            f"File '{file_path}' deleted successfully from branch '{branch}' "
            f"in project {project_id}"
        )
    }


# ============================================================================
# Repository Management Tools - Commit and Tag Operations
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def list_commits(
    project_id: int,
    per_page: int = 20,
    page: int = 1,
    ref_name: str | None = None,
    since: str | None = None,
    until: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List commits in a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        per_page: Number of commits per page (1-100, default: 20)
        page: Page number (default: 1)
        ref_name: Branch name, tag, or commit SHA to list commits from (optional)
        since: Only commits after this date (ISO 8601 format, optional)
        until: Only commits before this date (ISO 8601 format, optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with commit list and metadata
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add optional filters
    if ref_name:
        params["ref_name"] = ref_name
    if since:
        params["since"] = since
    if until:
        params["until"] = until

    # Make API request
    response = make_request("GET", f"projects/{project_id}/repository/commits", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "commit")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def get_commit(
    project_id: int,
    sha: str,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get details of a specific commit in a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        sha: Commit SHA (required)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Commit details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)

    # Validate sha
    if not isinstance(sha, str):
        raise ValueError(
            f"sha must be a string, got {type(sha).__name__}: {sha}"
        )
    if not sha.strip():
        raise ValueError("sha cannot be empty or whitespace only")

    sha = sha.strip()

    # Make API request
    response = make_request("GET", f"projects/{project_id}/repository/commits/{sha}")

    # Apply field filtering
    return filter_fields(response, include_fields, "commit")


@mcp.tool()
@handle_gitlab_errors
def list_tags(
    project_id: int,
    per_page: int = 20,
    page: int = 1,
    search: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List tags in a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        per_page: Number of tags per page (1-100, default: 20)
        page: Page number (default: 1)
        search: Optional search query to filter tags by name
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with tag list and metadata
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add search parameter if provided
    if search:
        params["search"] = search

    # Make API request
    response = make_request("GET", f"projects/{project_id}/repository/tags", params=params)

    # Apply field filtering if requested
    if include_fields:
        filtered_data = filter_fields(response, include_fields)
    else:
        filtered_data = response

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def create_tag(
    project_id: int,
    tag_name: str,
    ref: str,
    message: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new tag in a GitLab project repository.

    Args:
        project_id: Project ID (must be positive integer)
        tag_name: Tag name (required)
        ref: Branch name, tag, or commit SHA to create tag from (required)
        message: Tag message/annotation (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created tag details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)

    # Validate tag_name
    if not isinstance(tag_name, str):
        raise ValueError(
            f"tag_name must be a string, got {type(tag_name).__name__}: {tag_name}"
        )
    if not tag_name.strip():
        raise ValueError("tag_name cannot be empty or whitespace only")

    tag_name = tag_name.strip()

    # Validate ref
    if not isinstance(ref, str):
        raise ValueError(
            f"ref must be a string, got {type(ref).__name__}: {ref}"
        )
    if not ref.strip():
        raise ValueError("ref cannot be empty or whitespace only")

    ref = ref.strip()

    # Build request body
    data: dict[str, Any] = {
        "tag_name": tag_name,
        "ref": ref,
    }

    # Add optional message
    if message:
        data["message"] = message

    # Make API request
    response = make_request("POST", f"projects/{project_id}/repository/tags", json=data)

    # Apply field filtering if requested
    if include_fields:
        return filter_fields(response, include_fields)

    return response


# ============================================================================
# CI/CD Pipeline Management Tools
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def list_pipelines(
    project_id: int,
    per_page: int = 20,
    page: int = 1,
    ref: str | None = None,
    status: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List CI/CD pipelines in a GitLab project with pagination and filtering.

    Args:
        project_id: Project ID (must be positive integer)
        per_page: Number of pipelines per page (1-100, default: 20)
        page: Page number (default: 1)
        ref: Filter by branch name or tag (optional)
        status: Filter by status - "running", "pending", "success", "failed",
            "canceled", "skipped", "created", "manual" (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with pipeline list and metadata
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    page, per_page = validate_pagination(page, per_page)

    # Validate status if provided
    valid_statuses = (
        "running", "pending", "success", "failed",
        "canceled", "skipped", "created", "manual"
    )
    if status and status not in valid_statuses:
        raise ValueError(
            f"status must be one of: {', '.join(valid_statuses)}. Got: {status}"
        )

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add optional filters
    if ref:
        params["ref"] = ref
    if status:
        params["status"] = status

    # Make API request
    response = make_request("GET", f"projects/{project_id}/pipelines", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "pipeline")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def get_pipeline(
    project_id: int,
    pipeline_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get details of a specific CI/CD pipeline in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        pipeline_id: Pipeline ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Pipeline details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    pipeline_id = validate_iid(pipeline_id, "pipeline_id")

    # Make API request
    response = make_request("GET", f"projects/{project_id}/pipelines/{pipeline_id}")

    # Apply field filtering
    return filter_fields(response, include_fields, "pipeline")


@mcp.tool()
@handle_gitlab_errors
def create_pipeline(
    project_id: int,
    ref: str,
    variables: dict[str, str] | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new CI/CD pipeline in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        ref: Branch name, tag, or commit SHA to run pipeline on (required)
        variables: Pipeline variables as key-value pairs (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created pipeline details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)

    # Validate ref
    if not isinstance(ref, str):
        raise ValueError(
            f"ref must be a string, got {type(ref).__name__}: {ref}"
        )
    if not ref.strip():
        raise ValueError("ref cannot be empty or whitespace only")

    ref = ref.strip()

    # Build request body
    data: dict[str, Any] = {
        "ref": ref,
    }

    # Add variables if provided
    if variables:
        # Convert dict to list of {key, value} objects for GitLab API
        data["variables"] = [
            {"key": k, "value": v} for k, v in variables.items()
        ]

    # Make API request
    response = make_request("POST", f"projects/{project_id}/pipeline", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "pipeline")


@mcp.tool()
@handle_gitlab_errors
def retry_pipeline(
    project_id: int,
    pipeline_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Retry a failed CI/CD pipeline in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        pipeline_id: Pipeline ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Retried pipeline details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    pipeline_id = validate_iid(pipeline_id, "pipeline_id")

    # Make API request
    response = make_request("POST", f"projects/{project_id}/pipelines/{pipeline_id}/retry")

    # Apply field filtering
    return filter_fields(response, include_fields, "pipeline")


@mcp.tool()
@handle_gitlab_errors
def cancel_pipeline(
    project_id: int,
    pipeline_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Cancel a running CI/CD pipeline in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        pipeline_id: Pipeline ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Canceled pipeline details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    pipeline_id = validate_iid(pipeline_id, "pipeline_id")

    # Make API request
    response = make_request("POST", f"projects/{project_id}/pipelines/{pipeline_id}/cancel")

    # Apply field filtering
    return filter_fields(response, include_fields, "pipeline")


# ============================================================================
# CI/CD Job Management Tools
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def list_jobs(
    project_id: int,
    pipeline_id: int,
    per_page: int = 20,
    page: int = 1,
    scope: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List jobs in a CI/CD pipeline with pagination and filtering.

    Args:
        project_id: Project ID (must be positive integer)
        pipeline_id: Pipeline ID (must be positive integer)
        per_page: Number of jobs per page (1-100, default: 20)
        page: Page number (default: 1)
        scope: Filter by scope - "created", "pending", "running", "failed",
            "success", "canceled", "skipped", "manual" (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with job list and metadata
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    pipeline_id = validate_iid(pipeline_id, "pipeline_id")
    page, per_page = validate_pagination(page, per_page)

    # Validate scope if provided
    valid_scopes = (
        "created", "pending", "running", "failed",
        "success", "canceled", "skipped", "manual"
    )
    if scope and scope not in valid_scopes:
        raise ValueError(
            f"scope must be one of: {', '.join(valid_scopes)}. Got: {scope}"
        )

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add optional filters
    if scope:
        params["scope"] = scope

    # Make API request
    response = make_request(
        "GET", f"projects/{project_id}/pipelines/{pipeline_id}/jobs", params=params
    )

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "job")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def get_job(
    project_id: int,
    job_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get details of a specific CI/CD job in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        job_id: Job ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Job details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    job_id = validate_iid(job_id, "job_id")

    # Make API request
    response = make_request("GET", f"projects/{project_id}/jobs/{job_id}")

    # Apply field filtering
    return filter_fields(response, include_fields, "job")


@mcp.tool()
@handle_gitlab_errors
def retry_job(
    project_id: int,
    job_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Retry a failed CI/CD job in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        job_id: Job ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Retried job details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    job_id = validate_iid(job_id, "job_id")

    # Make API request
    response = make_request("POST", f"projects/{project_id}/jobs/{job_id}/retry")

    # Apply field filtering
    return filter_fields(response, include_fields, "job")


@mcp.tool()
@handle_gitlab_errors
def cancel_job(
    project_id: int,
    job_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Cancel a running CI/CD job in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        job_id: Job ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Canceled job details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    job_id = validate_iid(job_id, "job_id")

    # Make API request
    response = make_request("POST", f"projects/{project_id}/jobs/{job_id}/cancel")

    # Apply field filtering
    return filter_fields(response, include_fields, "job")


@mcp.tool()
@handle_gitlab_errors
def get_job_log(
    project_id: int,
    job_id: int
) -> dict[str, Any]:
    """Get the log/trace output of a CI/CD job in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        job_id: Job ID (must be positive integer)

    Returns:
        Job log as text in a dict with 'log' key
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    job_id = validate_iid(job_id, "job_id")

    # Get configuration for custom request
    config = get_gitlab_config()

    # Construct full URL
    url = f"{config['base_url']}/api/v4/projects/{project_id}/jobs/{job_id}/trace"

    # Prepare headers
    headers = {
        "PRIVATE-TOKEN": config["token"],
        "User-Agent": "gitlab-mcp-server/0.1.0",
    }

    # Make request with context manager for connection pooling
    with httpx.Client(verify=config["verify_ssl"], timeout=30.0) as client:
        response = client.get(url, headers=headers)

        # Raise exception for HTTP errors
        response.raise_for_status()

        # Return log as text wrapped in dict
        return {
            "log": response.text,
            "job_id": job_id,
            "project_id": project_id
        }


# ============================================================================
# Group Management Tools
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def list_groups(
    per_page: int = 20,
    page: int = 1,
    search: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List GitLab groups with pagination and optional search.

    Args:
        per_page: Number of groups per page (1-100, default: 20)
        page: Page number (default: 1)
        search: Optional search query to filter groups by name/path
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with group list and metadata
    """
    # Validate pagination parameters
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add search parameter if provided
    if search:
        params["search"] = search

    # Make API request
    response = make_request("GET", "groups", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "group")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def get_group(
    group_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get details of a specific GitLab group.

    Args:
        group_id: Group ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Group details
    """
    # Validate group_id
    group_id = validate_group_id(group_id)

    # Make API request
    response = make_request("GET", f"groups/{group_id}")

    # Apply field filtering
    return filter_fields(response, include_fields, "group")


@mcp.tool()
@handle_gitlab_errors
def create_group(
    name: str,
    path: str,
    description: str | None = None,
    visibility: str = "private",
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new GitLab group.

    Args:
        name: Group name (required)
        path: Group path/URL slug (required)
        description: Group description (optional)
        visibility: Group visibility - "private", "internal", or "public" (default: "private")
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created group details
    """
    # Validate parameters
    name = validate_non_empty_string(name, "name")
    path = validate_non_empty_string(path, "path")
    visibility = validate_visibility(visibility)

    # Build request body
    data: dict[str, Any] = {
        "name": name,
        "path": path,
        "visibility": visibility,
    }

    # Add optional description
    if description:
        data["description"] = description

    # Make API request
    response = make_request("POST", "groups", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "group")


@mcp.tool()
@handle_gitlab_errors
def update_group(
    group_id: int,
    name: str | None = None,
    path: str | None = None,
    description: str | None = None,
    visibility: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Update an existing GitLab group.

    Args:
        group_id: Group ID (must be positive integer)
        name: New group name (optional)
        path: New group path/URL slug (optional)
        description: New group description (optional)
        visibility: New visibility - "private", "internal", or "public" (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Updated group details
    """
    # Validate group_id
    group_id = validate_group_id(group_id)

    # Validate optional parameters
    if name is not None:
        name = validate_non_empty_string(name, "name")

    if path is not None:
        path = validate_non_empty_string(path, "path")

    if visibility is not None:
        visibility = validate_visibility(visibility)

    # Build request body with only provided fields
    data: dict[str, Any] = {}

    if name is not None:
        data["name"] = name

    if path is not None:
        data["path"] = path

    if description is not None:
        data["description"] = description

    if visibility is not None:
        data["visibility"] = visibility

    # Make API request
    response = make_request("PUT", f"groups/{group_id}", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "group")


@mcp.tool()
@handle_gitlab_errors
def delete_group(group_id: int) -> dict[str, Any]:
    """Delete a GitLab group.

    Args:
        group_id: Group ID (must be positive integer)

    Returns:
        Success confirmation
    """
    # Validate group_id
    group_id = validate_group_id(group_id)

    # Make API request
    make_request("DELETE", f"groups/{group_id}")

    # Return success confirmation
    return {
        "success": True,
        "message": f"Group {group_id} deleted successfully"
    }


@mcp.tool()
@handle_gitlab_errors
def list_group_members(
    group_id: int,
    per_page: int = 20,
    page: int = 1,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List members of a GitLab group with pagination.

    Args:
        group_id: Group ID (must be positive integer)
        per_page: Number of members per page (1-100, default: 20)
        page: Page number (default: 1)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with member list and metadata
    """
    # Validate parameters
    group_id = validate_group_id(group_id)
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Make API request
    response = make_request("GET", f"groups/{group_id}/members", params=params)

    # Apply field filtering with user resource type
    filtered_data = filter_fields(response, include_fields, "user")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def add_group_member(
    group_id: int,
    user_id: int,
    access_level: int = ACCESS_LEVEL_DEVELOPER,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Add a member to a GitLab group.

    Args:
        group_id: Group ID (must be positive integer)
        user_id: User ID to add (must be positive integer)
        access_level: Access level - 10 (Guest), 20 (Reporter), 30 (Developer),
            40 (Maintainer), 50 (Owner) (default: 30)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Added member details
    """
    # Validate parameters
    group_id = validate_group_id(group_id)
    user_id = validate_user_id(user_id)
    access_level = validate_access_level(access_level)

    # Build request body
    data: dict[str, Any] = {
        "user_id": user_id,
        "access_level": access_level,
    }

    # Make API request
    response = make_request("POST", f"groups/{group_id}/members", json=data)

    # Apply field filtering with user resource type
    return filter_fields(response, include_fields, "user")


# ============================================================================
# User Management Tools
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def get_current_user(
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get information about the currently authenticated user.

    Args:
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Current user details
    """
    # Make API request
    response = make_request("GET", "user")

    # Apply field filtering
    return filter_fields(response, include_fields, "user")


@mcp.tool()
@handle_gitlab_errors
def get_user(
    user_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Get information about a specific user by ID.

    Args:
        user_id: User ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        User details
    """
    # Validate user_id
    user_id = validate_user_id(user_id)

    # Make API request
    response = make_request("GET", f"users/{user_id}")

    # Apply field filtering
    return filter_fields(response, include_fields, "user")


@mcp.tool()
@handle_gitlab_errors
def list_users(
    per_page: int = 20,
    page: int = 1,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List all users in the GitLab instance with pagination.

    Args:
        per_page: Number of users per page (1-100, default: 20)
        page: Page number (default: 1)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with user list and metadata
    """
    # Validate pagination parameters
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Make API request
    response = make_request("GET", "users", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "user")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def search_users(
    search: str,
    per_page: int = 20,
    page: int = 1,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Search for users by username, name, or email.

    Args:
        search: Search query (searches username, name, and email)
        per_page: Number of users per page (1-100, default: 20)
        page: Page number (default: 1)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with matching users and metadata
    """
    # Validate search parameter
    if not isinstance(search, str):
        raise ValueError(
            f"search must be a string, got {type(search).__name__}: {search}"
        )

    if not search.strip():
        raise ValueError("search query cannot be empty or whitespace only")

    # Validate pagination parameters
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "search": search.strip(),
        "per_page": per_page,
        "page": page,
    }

    # Make API request
    response = make_request("GET", "users", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "user")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


# ============================================================================
# Label Management Tools
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def list_labels(
    project_id: int,
    per_page: int = 20,
    page: int = 1,
    search: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List labels in a GitLab project with pagination and optional search.

    Args:
        project_id: Project ID (must be positive integer)
        per_page: Number of labels per page (1-100, default: 20)
        page: Page number (default: 1)
        search: Optional search query to filter labels by name
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with label list and metadata
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    page, per_page = validate_pagination(page, per_page)

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add search parameter if provided
    if search:
        params["search"] = search

    # Make API request
    response = make_request("GET", f"projects/{project_id}/labels", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "label")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def create_label(
    project_id: int,
    name: str,
    color: str,
    description: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new label in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        name: Label name (required)
        color: Label color in hex format (e.g., "#FF0000") (required)
        description: Label description (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created label details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    name = validate_non_empty_string(name, "name")
    color = validate_non_empty_string(color, "color")

    # Build request body
    data: dict[str, Any] = {
        "name": name,
        "color": color,
    }

    # Add optional description
    if description:
        data["description"] = description

    # Make API request
    response = make_request("POST", f"projects/{project_id}/labels", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "label")


@mcp.tool()
@handle_gitlab_errors
def update_label(
    project_id: int,
    label_id: int,
    name: str | None = None,
    new_name: str | None = None,
    color: str | None = None,
    description: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Update an existing label in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        label_id: Label ID (must be positive integer)
        name: Current label name (required for identification if label_id not supported)
        new_name: New label name (optional)
        color: New label color in hex format (optional)
        description: New label description (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Updated label details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    label_id = validate_iid(label_id, "label_id")

    # Build request body with only provided fields
    data: dict[str, Any] = {}

    if name is not None:
        data["name"] = validate_non_empty_string(name, "name")

    if new_name is not None:
        data["new_name"] = validate_non_empty_string(new_name, "new_name")

    if color is not None:
        data["color"] = validate_non_empty_string(color, "color")

    if description is not None:
        data["description"] = description

    # Make API request
    response = make_request("PUT", f"projects/{project_id}/labels/{label_id}", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "label")


@mcp.tool()
@handle_gitlab_errors
def delete_label(
    project_id: int,
    label_id: int
) -> dict[str, Any]:
    """Delete a label from a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        label_id: Label ID (must be positive integer)

    Returns:
        Success confirmation
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    label_id = validate_iid(label_id, "label_id")

    # Make API request
    make_request("DELETE", f"projects/{project_id}/labels/{label_id}")

    # Return success confirmation
    return {
        "success": True,
        "message": f"Label {label_id} deleted successfully from project {project_id}"
    }


# ============================================================================
# Milestone Management Tools
# ============================================================================

@mcp.tool()
@handle_gitlab_errors
def list_milestones(
    project_id: int,
    per_page: int = 20,
    page: int = 1,
    state: str | None = None,
    search: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """List milestones in a GitLab project with pagination and filtering.

    Args:
        project_id: Project ID (must be positive integer)
        per_page: Number of milestones per page (1-100, default: 20)
        page: Page number (default: 1)
        state: Filter by state - "active" or "closed" (optional)
        search: Optional search query to filter milestones by title
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Paginated response with milestone list and metadata
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    page, per_page = validate_pagination(page, per_page)

    # Validate state if provided
    if state and state not in ("active", "closed"):
        raise ValueError(
            f"state must be 'active' or 'closed', got: {state}"
        )

    # Build query parameters
    params: dict[str, Any] = {
        "per_page": per_page,
        "page": page,
    }

    # Add optional filters
    if state:
        params["state"] = state
    if search:
        params["search"] = search

    # Make API request
    response = make_request("GET", f"projects/{project_id}/milestones", params=params)

    # Apply field filtering
    filtered_data = filter_fields(response, include_fields, "milestone")

    # Wrap with pagination metadata
    return paginate_response(filtered_data, page, per_page)


@mcp.tool()
@handle_gitlab_errors
def create_milestone(
    project_id: int,
    title: str,
    description: str | None = None,
    due_date: str | None = None,
    start_date: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Create a new milestone in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        title: Milestone title (required)
        description: Milestone description (optional)
        due_date: Due date in YYYY-MM-DD format (optional)
        start_date: Start date in YYYY-MM-DD format (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Created milestone details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    title = validate_non_empty_string(title, "title")

    # Build request body
    data: dict[str, Any] = {
        "title": title,
    }

    # Add optional fields
    if description:
        data["description"] = description
    if due_date:
        data["due_date"] = due_date
    if start_date:
        data["start_date"] = start_date

    # Make API request
    response = make_request("POST", f"projects/{project_id}/milestones", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "milestone")


@mcp.tool()
@handle_gitlab_errors
def update_milestone(
    project_id: int,
    milestone_id: int,
    title: str | None = None,
    description: str | None = None,
    due_date: str | None = None,
    start_date: str | None = None,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Update an existing milestone in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        milestone_id: Milestone ID (must be positive integer)
        title: New milestone title (optional)
        description: New milestone description (optional)
        due_date: New due date in YYYY-MM-DD format (optional)
        start_date: New start date in YYYY-MM-DD format (optional)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Updated milestone details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    milestone_id = validate_iid(milestone_id, "milestone_id")

    # Build request body with only provided fields
    data: dict[str, Any] = {}

    if title is not None:
        data["title"] = validate_non_empty_string(title, "title")

    if description is not None:
        data["description"] = description

    if due_date is not None:
        data["due_date"] = due_date

    if start_date is not None:
        data["start_date"] = start_date

    # Make API request
    response = make_request("PUT", f"projects/{project_id}/milestones/{milestone_id}", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "milestone")


@mcp.tool()
@handle_gitlab_errors
def close_milestone(
    project_id: int,
    milestone_id: int,
    include_fields: str | None = None
) -> dict[str, Any]:
    """Close a milestone in a GitLab project.

    Args:
        project_id: Project ID (must be positive integer)
        milestone_id: Milestone ID (must be positive integer)
        include_fields: Comma-separated list of fields to include, or "all" for all fields

    Returns:
        Closed milestone details
    """
    # Validate parameters
    project_id = validate_project_id(project_id)
    milestone_id = validate_iid(milestone_id, "milestone_id")

    # Build request body with state_event=close
    data: dict[str, Any] = {
        "state_event": "close"
    }

    # Make API request
    response = make_request("PUT", f"projects/{project_id}/milestones/{milestone_id}", json=data)

    # Apply field filtering
    return filter_fields(response, include_fields, "milestone")


def main() -> None:
    """Main entry point for the server.

    Validates GitLab connection on startup and runs the MCP server.
    """
    # Validate connection on startup
    validate_gitlab_connection()

    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()
