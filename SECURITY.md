# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Cohezion, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please use one of these methods:

1. **GitHub Security Advisories** (preferred): Use the "Report a vulnerability" button on the [Security tab](https://github.com/manderson240/cohezion/security/advisories/new) of this repository.

2. **Email**: Send details to the repository owner via the email listed in `pyproject.toml`.

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 7 days
- **Fix or mitigation**: Best effort, typically within 30 days for confirmed issues

## Security Practices

This project follows these security practices:

- **Static analysis**: Ruff with flake8-bandit rules (`S` prefix) enabled
- **Secret detection**: `detect-secrets` and `detect-private-key` in pre-commit hooks
- **Dependency scanning**: Dependabot monitors for known vulnerabilities
- **Code scanning**: CodeQL runs on every PR and weekly
- **Pre-commit hooks**: Block commits containing private keys or large files
- **CI enforcement**: Security checks run in CI and block merges on failure

## Scope

The following are in scope for security reports:

- The Cohezion Python package (`src/cohezion/`)
- API endpoints (`src/cohezion/api/`)
- Authentication and authorization logic
- Data handling and storage patterns
- CI/CD pipeline security

Out of scope:

- Third-party dependencies (report to their maintainers)
- Development tooling configuration
- Documentation content
