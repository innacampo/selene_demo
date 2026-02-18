# CHANGELOG

All notable changes to SELENE will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial GitHub optimization with CI/CD, issue templates, and community docs
- Pre-commit hooks for code quality
- Comprehensive test suite (27 deterministic tests, 19 context tests, 34 cache tests)
- CC BY 4.0 licensing

### Changed
- Improved .gitignore with better coverage
- Enhanced README with badges and structured sections

## [0.1.0] - 2026-02-17

### Added
- Privacy-first menopause assistant with local data storage
- Daily Attune logging (rest/internal weather/clarity tracking)
- RAG-backed chat with MedGemma integration
- Clinical insight reports with PDF export
- Deterministic risk assessment and pattern detection
- Local ChromaDB knowledge base with sentence embeddings
- Streamlit UI with home/pulse/chat/clinical views
- Caching infrastructure (contextualized queries, RAG, user context)
- Safety guardrails with low-temperature LLM calls
- Automated backup system for pulse history
- Knowledge base import/export utilities

[Unreleased]: https://github.com/innacampo/selene/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/innacampo/selene/releases/tag/v0.1.0
