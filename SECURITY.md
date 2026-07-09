# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**Please DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please report security vulnerabilities via:

1. **GitHub Security Advisory**: [Report a vulnerability](https://github.com/manderson240/cohezion/security/advisories/new)
2. **Email**: manderson240@gmail.com (for urgent issues)

### What to Include

When reporting a vulnerability, please include:

- **Description**: Clear description of the vulnerability
- **Impact**: What could an attacker do with this?
- **Reproduction**: Steps to reproduce the issue
- **Affected versions**: Which versions are affected?
- **Mitigation**: Any suggested fixes or workarounds

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Assessment**: Within 1 week
- **Fix/Update**: Within 30 days (depending on severity)

## Security Features

This repository implements the following security measures:

### Code Scanning

- **CodeQL**: Automated security analysis on every push and PR
- **SARIF uploads**: Results available in GitHub Security tab
- **Custom queries**: Python-specific security patterns

### Dependency Security

- **Dependabot**: Automated dependency updates
- **Dependency Review**: PR-level vulnerability scanning
- **License checking**: Compliance with OSS licenses

### Secret Protection

- **Secret scanning**: Prevents accidental commits of credentials
- **Push protection**: Blocks commits with detected secrets
- **Pre-commit hooks**: Local validation before push

## Security Best Practices

### For Contributors

1. **Never commit secrets**: Use environment variables or secure vaults
2. **Keep dependencies updated**: Review Dependabot PRs promptly
3. **Run security scans locally**: Use `bandit` and `detect-secrets`
4. **Follow least privilege**: Minimal permissions in CI/CD

### For Maintainers

1. **Review security alerts weekly**: Check GitHub Security tab
2. **Apply security updates promptly**: Critical patches within 7 days
3. **Rotate credentials regularly**: PATs, API keys, certificates
4. **Audit access**: Review collaborator permissions quarterly

## Security Tools

### Local Development

```bash
# Install security tools
pip install bandit detect-secrets safety

# Run security scans
bandit -r src/
detect-secrets scan

# Check dependencies
safety check
```

### Pre-commit

Security hooks are configured in `.pre-commit-config.yaml`:

- `detect-private-key`: Prevents private key commits
- `detect-secrets`: Scans for credential patterns
- `bandit`: Security linting for Python code

## Compliance

This project aims to follow:

- **OWASP Top 10**: Web application security standards
- **CWE Top 25**: Common weakness enumeration
- **SLSA Level 1**: Software supply chain security

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities. Contributors will be acknowledged (with permission) in our release notes.

## License

Security policies and procedures are provided under the same license as the project — see [LICENSE](LICENSE) (AGPL-3.0) and [LICENSING.md](LICENSING.md).

---

**Last Updated**: 2026-02-26

**Contact**: For security questions, please use GitHub Security Advisories or email manderson240@gmail.com
