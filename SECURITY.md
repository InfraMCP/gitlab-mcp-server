# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of GitLab MCP Server seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Where to Report

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: security@inframcp.example.com

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

### What to Include

Please include the following information in your report:

- Type of vulnerability (e.g., authentication bypass, injection, etc.)
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability, including how an attacker might exploit it

### What to Expect

- We will acknowledge receipt of your vulnerability report within 48 hours
- We will send you regular updates about our progress
- We will notify you when the vulnerability is fixed
- We may ask for additional information or guidance

### Disclosure Policy

- We will coordinate with you on the disclosure timeline
- We prefer to fully remediate vulnerabilities before public disclosure
- We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security Best Practices

When using GitLab MCP Server, please follow these security best practices:

### Token Security

- **Never commit tokens to version control**: Always use environment variables for `GITLAB_TOKEN`
- **Use minimal scopes**: Only grant the API scopes your application needs
- **Rotate tokens regularly**: Generate new Personal Access Tokens periodically
- **Use read-only tokens when possible**: If you only need read access, use a token with read-only scopes
- **Store tokens securely**: Use secure credential storage systems in production

### SSL/TLS Configuration

- **Enable SSL verification**: Keep `GITLAB_VERIFY_SSL=true` in production
- **Only disable for development**: Only set `GITLAB_VERIFY_SSL=false` for local development with self-signed certificates
- **Use valid certificates**: Ensure your GitLab instance uses valid SSL certificates

### Network Security

- **Use HTTPS**: Always connect to GitLab instances over HTTPS
- **Restrict network access**: Limit which networks can access your MCP server
- **Use firewalls**: Configure firewalls to restrict inbound/outbound traffic
- **Monitor access logs**: Regularly review access logs for suspicious activity

### Input Validation

- **Validate all inputs**: The server validates inputs, but ensure your client does too
- **Sanitize user data**: Clean any user-provided data before passing to the server
- **Use parameterized queries**: Never construct API calls with string concatenation

### Dependency Management

- **Keep dependencies updated**: Regularly update to the latest version
- **Monitor security advisories**: Watch for security updates in dependencies
- **Use dependency scanning**: Enable automated dependency vulnerability scanning
- **Review dependency changes**: Check changelogs when updating dependencies

### Deployment Security

- **Use least privilege**: Run the server with minimal required permissions
- **Isolate the server**: Use containers or VMs to isolate the server
- **Enable logging**: Configure comprehensive logging for security monitoring
- **Implement rate limiting**: Protect against abuse with rate limiting
- **Use secrets management**: Store sensitive configuration in secure vaults

### Monitoring and Auditing

- **Enable audit logging**: Track all API calls and changes
- **Monitor for anomalies**: Watch for unusual patterns in API usage
- **Set up alerts**: Configure alerts for security-relevant events
- **Regular security reviews**: Periodically review security configurations

## Known Security Considerations

### API Token Exposure

The server requires a GitLab Personal Access Token to function. This token has the same permissions as the user who created it. Ensure:

- Tokens are stored securely in environment variables
- Tokens are never logged or exposed in error messages
- Tokens are rotated if compromised

### Rate Limiting

The server does not implement its own rate limiting. GitLab's API rate limits apply:

- 2,000 requests per minute for authenticated requests (GitLab.com)
- Self-hosted instances may have different limits
- Monitor rate limit headers in responses

### Error Messages

Error messages are designed to be helpful without exposing sensitive information:

- No tokens or credentials in error messages
- No internal system paths in error messages
- Generic messages for authentication failures

### SSL Certificate Verification

The `GITLAB_VERIFY_SSL` setting can be disabled for development:

- **Never disable in production**
- Only use for local development with self-signed certificates
- Re-enable immediately after development

## Security Updates

We will publish security advisories for any vulnerabilities:

- GitHub Security Advisories
- CHANGELOG.md with security notes
- Email notifications to users (if contact information available)

## Compliance

This project aims to follow security best practices including:

- OWASP Top 10 guidelines
- CWE/SANS Top 25 Most Dangerous Software Errors
- Secure coding standards for Python

## Questions

If you have questions about security that are not covered here, please email: security@inframcp.example.com

---

Thank you for helping keep GitLab MCP Server and its users safe!
