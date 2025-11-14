# GitLab MCP Server

A Model Context Protocol (MCP) server that provides seamless integration with GitLab, enabling AI assistants to interact with GitLab projects, issues, merge requests, CI/CD pipelines, and more.

## Features

- **Project Management**: List, create, update, and delete GitLab projects
- **Issue Tracking**: Full CRUD operations for issues, including comments and state management
- **Merge Requests**: Create, review, approve, and merge pull requests with diff viewing
- **Repository Operations**: Branch management, file operations, commits, and tags
- **CI/CD Integration**: Pipeline and job management with logs and retry capabilities
- **Group Management**: Manage GitLab groups and group memberships
- **User Management**: Search and retrieve user information
- **Labels & Milestones**: Organize work with labels and milestones
- **Field Filtering**: Customize API responses to include only needed fields
- **Pagination Support**: Efficient handling of large result sets
- **Comprehensive Error Handling**: Clear, actionable error messages with recovery suggestions
- **SSL Verification**: Configurable SSL certificate verification for self-hosted instances

## Installation

Install the GitLab MCP server using pip:

```bash
pip install gitlab-mcp-server
```

## Configuration

### Environment Variables

The server requires the following environment variables:

- **`GITLAB_TOKEN`** (required): Your GitLab Personal Access Token
  - Generate at: https://gitlab.com/-/profile/personal_access_tokens
  - Required scopes: `api`, `read_user`, `read_repository`, `write_repository`

- **`GITLAB_URL`** (optional): GitLab instance URL
  - Default: `https://gitlab.com`
  - For self-hosted: `https://gitlab.example.com`

- **`GITLAB_VERIFY_SSL`** (optional): SSL certificate verification
  - Default: `true`
  - Set to `false` for self-signed certificates (not recommended for production)

### MCP Client Configuration

#### Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "python",
      "args": ["-m", "gitlab_mcp_server"],
      "env": {
        "GITLAB_TOKEN": "your-personal-access-token",
        "GITLAB_URL": "https://gitlab.com",
        "GITLAB_VERIFY_SSL": "true"
      }
    }
  }
}
```

#### Other MCP Clients

For other MCP-compatible clients, use the following command:

```bash
python -m gitlab_mcp_server
```

With environment variables set in your shell or passed directly:

```bash
GITLAB_TOKEN=your-token GITLAB_URL=https://gitlab.com python -m gitlab_mcp_server
```

## Available Tools

### Project Management

- **`list_projects`**: List GitLab projects with pagination and search
  - Parameters: `per_page`, `page`, `search`, `include_fields`
  
- **`get_project`**: Get details of a specific project
  - Parameters: `project_id`, `include_fields`
  
- **`create_project`**: Create a new GitLab project
  - Parameters: `name`, `description`, `visibility`, `initialize_with_readme`, `include_fields`
  
- **`update_project`**: Update an existing project
  - Parameters: `project_id`, `name`, `description`, `visibility`, `default_branch`, `include_fields`
  
- **`delete_project`**: Delete a project
  - Parameters: `project_id`

### Issue Management

- **`list_issues`**: List issues in a project with filtering
  - Parameters: `project_id`, `per_page`, `page`, `state`, `labels`, `include_fields`
  
- **`get_issue`**: Get details of a specific issue
  - Parameters: `project_id`, `issue_iid`, `include_fields`
  
- **`create_issue`**: Create a new issue
  - Parameters: `project_id`, `title`, `description`, `labels`, `assignee_ids`, `include_fields`
  
- **`update_issue`**: Update an existing issue
  - Parameters: `project_id`, `issue_iid`, `title`, `description`, `labels`, `assignee_ids`, `state_event`, `include_fields`
  
- **`close_issue`**: Close an issue
  - Parameters: `project_id`, `issue_iid`, `include_fields`
  
- **`reopen_issue`**: Reopen a closed issue
  - Parameters: `project_id`, `issue_iid`, `include_fields`
  
- **`add_issue_comment`**: Add a comment to an issue
  - Parameters: `project_id`, `issue_iid`, `body`
  
- **`list_issue_comments`**: List comments on an issue
  - Parameters: `project_id`, `issue_iid`, `per_page`, `page`

### Merge Request Management

- **`list_merge_requests`**: List merge requests in a project
  - Parameters: `project_id`, `per_page`, `page`, `state`, `include_fields`
  
- **`get_merge_request`**: Get details of a specific merge request
  - Parameters: `project_id`, `mr_iid`, `include_fields`
  
- **`create_merge_request`**: Create a new merge request
  - Parameters: `project_id`, `source_branch`, `target_branch`, `title`, `description`, `include_fields`
  
- **`update_merge_request`**: Update an existing merge request
  - Parameters: `project_id`, `mr_iid`, `title`, `description`, `target_branch`, `state_event`, `include_fields`
  
- **`merge_merge_request`**: Merge a merge request
  - Parameters: `project_id`, `mr_iid`, `merge_commit_message`
  
- **`approve_merge_request`**: Approve a merge request
  - Parameters: `project_id`, `mr_iid`
  
- **`get_merge_request_changes`**: Get diff/changes for a merge request
  - Parameters: `project_id`, `mr_iid`
  
- **`add_merge_request_comment`**: Add a comment to a merge request
  - Parameters: `project_id`, `mr_iid`, `body`
  
- **`list_merge_request_comments`**: List comments on a merge request
  - Parameters: `project_id`, `mr_iid`, `per_page`, `page`

### Repository Management

#### Branch Operations

- **`list_branches`**: List branches in a repository
  - Parameters: `project_id`, `per_page`, `page`, `search`, `include_fields`
  
- **`get_branch`**: Get details of a specific branch
  - Parameters: `project_id`, `branch`, `include_fields`
  
- **`create_branch`**: Create a new branch
  - Parameters: `project_id`, `branch`, `ref`, `include_fields`
  
- **`delete_branch`**: Delete a branch
  - Parameters: `project_id`, `branch`

#### File Operations

- **`get_file`**: Get a file from the repository
  - Parameters: `project_id`, `file_path`, `ref`, `include_fields`
  
- **`create_file`**: Create a new file in the repository
  - Parameters: `project_id`, `file_path`, `branch`, `content`, `commit_message`, `encoding`, `include_fields`
  
- **`update_file`**: Update an existing file
  - Parameters: `project_id`, `file_path`, `branch`, `content`, `commit_message`, `encoding`, `include_fields`
  
- **`delete_file`**: Delete a file from the repository
  - Parameters: `project_id`, `file_path`, `branch`, `commit_message`

#### Commits and Tags

- **`list_commits`**: List commits in a repository
  - Parameters: `project_id`, `per_page`, `page`, `ref_name`, `include_fields`
  
- **`get_commit`**: Get details of a specific commit
  - Parameters: `project_id`, `sha`, `include_fields`
  
- **`list_tags`**: List tags in a repository
  - Parameters: `project_id`, `per_page`, `page`, `include_fields`
  
- **`create_tag`**: Create a new tag
  - Parameters: `project_id`, `tag_name`, `ref`, `message`, `include_fields`

### CI/CD Management

#### Pipeline Operations

- **`list_pipelines`**: List CI/CD pipelines
  - Parameters: `project_id`, `per_page`, `page`, `ref`, `status`, `include_fields`
  
- **`get_pipeline`**: Get details of a specific pipeline
  - Parameters: `project_id`, `pipeline_id`, `include_fields`
  
- **`create_pipeline`**: Trigger a new pipeline
  - Parameters: `project_id`, `ref`, `variables`, `include_fields`
  
- **`retry_pipeline`**: Retry a failed pipeline
  - Parameters: `project_id`, `pipeline_id`
  
- **`cancel_pipeline`**: Cancel a running pipeline
  - Parameters: `project_id`, `pipeline_id`

#### Job Operations

- **`list_jobs`**: List jobs in a pipeline
  - Parameters: `project_id`, `pipeline_id`, `per_page`, `page`, `include_fields`
  
- **`get_job`**: Get details of a specific job
  - Parameters: `project_id`, `job_id`, `include_fields`
  
- **`retry_job`**: Retry a failed job
  - Parameters: `project_id`, `job_id`
  
- **`cancel_job`**: Cancel a running job
  - Parameters: `project_id`, `job_id`
  
- **`get_job_log`**: Get logs for a job
  - Parameters: `project_id`, `job_id`

### Group Management

- **`list_groups`**: List GitLab groups
  - Parameters: `per_page`, `page`, `search`, `include_fields`
  
- **`get_group`**: Get details of a specific group
  - Parameters: `group_id`, `include_fields`
  
- **`create_group`**: Create a new group
  - Parameters: `name`, `path`, `description`, `visibility`, `include_fields`
  
- **`update_group`**: Update an existing group
  - Parameters: `group_id`, `name`, `path`, `description`, `visibility`, `include_fields`
  
- **`delete_group`**: Delete a group
  - Parameters: `group_id`
  
- **`list_group_members`**: List members of a group
  - Parameters: `group_id`, `per_page`, `page`, `include_fields`
  
- **`add_group_member`**: Add a member to a group
  - Parameters: `group_id`, `user_id`, `access_level`, `expires_at`

### User Management

- **`get_current_user`**: Get current authenticated user details
  - Parameters: `include_fields`
  
- **`get_user`**: Get details of a specific user
  - Parameters: `user_id`, `include_fields`
  
- **`list_users`**: List GitLab users
  - Parameters: `per_page`, `page`, `include_fields`
  
- **`search_users`**: Search for users
  - Parameters: `search`, `per_page`, `page`, `include_fields`

### Label and Milestone Management

#### Labels

- **`list_labels`**: List labels in a project
  - Parameters: `project_id`, `per_page`, `page`, `include_fields`
  
- **`create_label`**: Create a new label
  - Parameters: `project_id`, `name`, `color`, `description`, `include_fields`
  
- **`update_label`**: Update an existing label
  - Parameters: `project_id`, `label_id`, `name`, `color`, `description`, `include_fields`
  
- **`delete_label`**: Delete a label
  - Parameters: `project_id`, `label_id`

#### Milestones

- **`list_milestones`**: List milestones in a project
  - Parameters: `project_id`, `per_page`, `page`, `state`, `include_fields`
  
- **`create_milestone`**: Create a new milestone
  - Parameters: `project_id`, `title`, `description`, `due_date`, `start_date`, `include_fields`
  
- **`update_milestone`**: Update an existing milestone
  - Parameters: `project_id`, `milestone_id`, `title`, `description`, `due_date`, `start_date`, `include_fields`
  
- **`close_milestone`**: Close a milestone
  - Parameters: `project_id`, `milestone_id`, `include_fields`

## Usage Examples

### List Projects

```python
# List all accessible projects
list_projects(per_page=20, page=1)

# Search for projects
list_projects(search="my-project")

# Get specific fields only
list_projects(include_fields="id,name,web_url")
```

### Create and Manage Issues

```python
# Create a new issue
create_issue(
    project_id=123,
    title="Bug: Login not working",
    description="Users cannot log in with valid credentials",
    labels="bug,priority::high"
)

# Add a comment
add_issue_comment(
    project_id=123,
    issue_iid=42,
    body="I've reproduced this issue on staging"
)

# Close the issue
close_issue(project_id=123, issue_iid=42)
```

### Create a Merge Request

```python
# Create a merge request
create_merge_request(
    project_id=123,
    source_branch="feature/new-login",
    target_branch="main",
    title="Add new login flow",
    description="Implements OAuth2 authentication"
)

# Get the diff
get_merge_request_changes(project_id=123, mr_iid=15)

# Approve and merge
approve_merge_request(project_id=123, mr_iid=15)
merge_merge_request(project_id=123, mr_iid=15)
```

### Manage Repository Files

```python
# Get a file
get_file(
    project_id=123,
    file_path="src/main.py",
    ref="main"
)

# Create a new file
create_file(
    project_id=123,
    file_path="docs/api.md",
    branch="main",
    content="# API Documentation\n\n...",
    commit_message="Add API documentation"
)

# Update an existing file
update_file(
    project_id=123,
    file_path="README.md",
    branch="main",
    content="# Updated README\n\n...",
    commit_message="Update README with new instructions"
)
```

### Trigger and Monitor CI/CD

```python
# Trigger a pipeline
create_pipeline(
    project_id=123,
    ref="main",
    variables={"DEPLOY_ENV": "staging"}
)

# List pipeline jobs
list_jobs(project_id=123, pipeline_id=456)

# Get job logs
get_job_log(project_id=123, job_id=789)

# Retry a failed job
retry_job(project_id=123, job_id=789)
```

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager
- GitLab account with Personal Access Token

### Installation for Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gitlab-mcp-server.git
cd gitlab-mcp-server
```

2. Install dependencies:
```bash
pip install -e ".[dev]"
```

3. Set up environment variables:
```bash
export GITLAB_TOKEN="your-personal-access-token"
export GITLAB_URL="https://gitlab.com"
```

4. Run tests:
```bash
pytest
```

5. Run with coverage:
```bash
pytest --cov=gitlab_mcp_server --cov-report=html
```

6. Run linting:
```bash
pylint src/gitlab_mcp_server
```

7. Format code:
```bash
black src/gitlab_mcp_server tests
```

### Project Structure

```
gitlab-mcp-server/
├── src/
│   └── gitlab_mcp_server/
│       ├── __init__.py       # Package initialization
│       ├── server.py          # Main server implementation
│       └── errors.py          # Error handling utilities
├── tests/
│   ├── test_*.py             # Test files
│   └── conftest.py           # Pytest configuration
├── README.md                  # This file
└── pyproject.toml            # Project metadata
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Write tests** for new functionality
3. **Ensure all tests pass** with `pytest`
4. **Follow code style** using `black` and `pylint`
5. **Update documentation** for new features
6. **Submit a pull request** with a clear description

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible
- Use meaningful variable and function names

### Testing

- Write unit tests for all new functionality
- Maintain test coverage above 70%
- Use mocking for external API calls
- Test error handling and edge cases

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove)
- Reference issue numbers when applicable

## Security

### Reporting Security Issues

If you discover a security vulnerability, please email security@example.com instead of using the issue tracker. We take security seriously and will respond promptly.

### Security Best Practices

- **Never commit tokens**: Keep your `GITLAB_TOKEN` secure and never commit it to version control
- **Use environment variables**: Store sensitive configuration in environment variables
- **Enable SSL verification**: Only disable SSL verification for development/testing
- **Rotate tokens regularly**: Generate new Personal Access Tokens periodically
- **Limit token scopes**: Only grant necessary API scopes to your tokens
- **Use read-only tokens**: When possible, use tokens with read-only access

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/yourusername/gitlab-mcp-server/issues)
- **Discussions**: Ask questions on [GitHub Discussions](https://github.com/yourusername/gitlab-mcp-server/discussions)
- **Documentation**: Full API documentation at [docs.example.com](https://docs.example.com)

## Acknowledgments

- Built with [Model Context Protocol](https://modelcontextprotocol.io/)
- Uses [httpx](https://www.python-httpx.org/) for HTTP requests
- Inspired by the GitLab API and community

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

---

Made with ❤️ for the GitLab and AI community
