# Contributing to SELENE

Thank you for your interest in contributing to SELENE! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Issues

- **Bug Reports**: Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) and include:
  - Steps to reproduce
  - Expected vs actual behavior
  - Python/Ollama version, OS
  - Relevant log snippets

- **Feature Requests**: Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) with:
  - Clear description of the feature
  - Use case / motivation
  - Proposed implementation (optional)

### Pull Requests

1. **Fork & Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/selene.git
   cd selene/selene
   ```

2. **Set Up Development Environment**
   ```bash
   python3.13 -m venv med_env
   source med_env/bin/activate
   pip install -e ".[dev]"
   pre-commit install
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Changes**
   - Follow the existing code style (PEP 8)
   - Add/update tests for new functionality
   - Update documentation as needed

5. **Run Tests**
   ```bash
   python -m pytest tests/ -v
   ```

6. **Commit with Meaningful Messages**
   ```bash
   git commit -m "feat: add new symptom tracking feature"
   ```
   
   We follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation changes
   - `test:` adding/updating tests
   - `refactor:` code refactoring
   - `chore:` maintenance tasks

7. **Push & Open PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Open a PR against `main` using the PR template.

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8; use type hints where practical
- **Docstrings**: Use Google-style docstrings
- **Line length**: 100 characters max
- **Imports**: Group stdlib → third-party → local, sorted alphabetically

### Testing

- Tests live in `tests/`
- Aim for coverage of deterministic logic; LLM outputs tested via mocking
- Run full suite before submitting PRs

### Architecture Notes

- **Deterministic-first**: All statistics, risk scoring, and pattern detection are computed without LLM calls
- **Privacy-first**: All user data stays local; no telemetry
- **Single LLM call**: Reports use one MedGemma inference on pre-computed context

### Commit Checklist

- [ ] Code follows project style
- [ ] Tests added/updated and passing
- [ ] Documentation updated (if applicable)
- [ ] No secrets or personal data committed
- [ ] Pre-commit hooks pass

## Questions?

Open a [Discussion](https://github.com/innacampo/selene/discussions) for questions not suited for issues.

---

Thank you for helping make SELENE better!
