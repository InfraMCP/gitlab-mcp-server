# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-14

### Added

#### Core Infrastructure
- Initial release of GitLab MCP Server
- FastMCP-based server implementation with Model Context Protocol support
- Configuration management via environment variables (GITLAB_TOKEN, GITLAB_URL, GITLAB_VERIFY_SSL)
- HTTP client wrapper with httpx for GitLab API v4 integration
- Startup validation for connectivity, authentication, and permissions
- Comprehensive error handling system with actionable error messages
- Field filtering system with default fields for each resource type
- Pagination support with metadata (has_next, next_page, total count)
- Input validation for project IDs, branch names, and pagination parameters

#### Project Management Tools
- `list_projects` - List GitLab projects with search and pagination
- `get_project` - Get details of a specific project
- `create_project` - Create new GitLab projects
- `update_project` - Update existing projects
- `delete_project` - Delete projects

#### Issue Management Tools
- `list_issues` - List issues with state and label filtering
- `get_issue` - Get issue details
- `create_issue` - Create new issues with labels and assignees
- `update_issue` - Update issue properties
- `close_issue` - Close issues
- `reopen_issue` - Reopen closed issues
- `add_issue_comment` - Add comments to issues
- `list_issue_comments` - List issue comments with pagination

#### Merge Request Management Tools
- `list_merge_requests` - List merge requests with state filtering
- `get_merge_request` - Get merge request details
- `create_merge_request` - Create new merge requests
- `update_merge_request` - Update merge request properties
- `merge_merge_request` - Merge approved merge requests
- `approve_merge_request` - Approve merge requests
- `get_merge_request_changes` - View merge request diffs
- `add_merge_request_comment` - Add comments to merge requests
- `list_merge_request_comments` - List merge request comments

#### Repository Management Tools
- `list_branches` - List repository branches with search
- `get_branch` - Get branch details
- `create_branch` - Create new branches
- `delete_branch` - Delete branches
- `get_file` - Get file contents from repository
- `create_file` - Create new files in repository
- `update_file` - Update existing files
- `delete_file` - Delete files from repository
- `list_commits` - List repository commits with filtering
- `get_commit` - Get commit details
- `list_tags` - List repository tags
- `create_tag` - Create new tags

#### CI/CD Pipeline Tools
- `list_pipelines` - List CI/CD pipelines with status filtering
- `get_pipeline` - Get pipeline details
- `create_pipeline` - Trigger new pipelines with variables
- `retry_pipeline` - Retry failed pipelines
- `cancel_pipeline` - Cancel running pipelines
- `list_jobs` - List pipeline jobs
- `get_job` - Get job details
- `retry_job` - Retry failed jobs
- `cancel_job` - Cancel running jobs
- `get_job_log` - Retrieve job logs

#### Group Management Tools
- `list_groups` - List GitLab groups with search
- `get_group` - Get group details
- `create_group` - Create new groups
- `update_group` - Update group properties
- `delete_group` - Delete groups
- `list_group_members` - List group members
- `add_group_member` - Add members to groups with access levels

#### User Management Tools
- `get_current_user` - Get authenticated user details
- `get_user` - Get specific user details
- `list_users` - List GitLab users with pagination
- `search_users` - Search for users by query

#### Label and Milestone Tools
- `list_labels` - List project labels
- `create_label` - Create new labels with colors
- `update_label` - Update label properties
- `delete_label` - Delete labels
- `list_milestones` - List project milestones
- `create_milestone` - Create new milestones with dates
- `update_milestone` - Update milestone properties
- `close_milestone` - Close milestones

#### Testing and Quality
- Comprehensive test suite with 290+ tests
- 90% code coverage across all modules
- Unit tests for all tools and utilities
- Error handling tests for various failure scenarios
- Field filtering and pagination tests
- Validation tests for input parameters

#### Documentation
- Complete README with installation instructions
- Configuration guide for Claude Desktop and other MCP clients
- Detailed tool documentation with parameters and examples
- Usage examples for common workflows
- Development setup guide
- Contributing guidelines
- Security best practices

#### CI/CD Workflows
- Automated testing on Python 3.10, 3.11, 3.12
- Pylint code quality checks
- Safety dependency vulnerability scanning
- pip-audit security advisory checks
- OSV scanner for pull requests
- Automated PyPI publishing on version tags

### Security
- SSL certificate verification (configurable)
- Secure token handling via environment variables
- Input validation to prevent injection attacks
- Comprehensive error handling without exposing sensitive data
- Security policy documentation (SECURITY.md)

### Dependencies
- mcp >= 1.3.2 - Model Context Protocol SDK
- httpx >= 0.28.1 - HTTP client for API requests
- pytest >= 8.3.4 - Testing framework
- pytest-cov >= 6.0.0 - Coverage reporting
- pytest-asyncio >= 0.25.2 - Async test support
- pylint >= 3.3.3 - Code quality analysis

[0.1.0]: https://github.com/yourusername/gitlab-mcp-server/releases/tag/v0.1.0
