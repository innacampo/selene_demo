# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in SELENE, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities.

2. **Email** the maintainers directly at [inna@harmonilab.org] with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

3. **Response Time**: We aim to acknowledge reports within 48 hours and provide a timeline for a fix.

4. **Disclosure**: We follow coordinated disclosure. We'll work with you on timing for public disclosure after a fix is available.

## Security Best Practices for Users

SELENE is designed with privacy-first principles:

- **Local-only data**: All user data (`user_data/`) stays on your machine
- **No telemetry**: External telemetry is disabled by default
- **Local LLM**: MedGemma runs via Ollama on localhost

### Recommendations

1. **Keep dependencies updated**: Regularly update via `pip install -U -r requirements.txt`
2. **Protect your data directory**: Ensure `user_data/` has appropriate file permissions
3. **Network exposure**: Only run the Streamlit app on localhost; do not expose to public networks
4. **Backup data**: Periodically back up `user_data/` to a secure location

## Acknowledgments

We appreciate security researchers who help keep SELENE safe. Contributors who report valid vulnerabilities will be acknowledged (with permission) in release notes.
