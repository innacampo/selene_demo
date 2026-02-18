# Quick Start for Contributors

Welcome to SELENE development! This guide gets you up and running in 5 minutes.

## Prerequisites

- Python 3.11+ installed
- Ollama installed and running
- Git configured

## Setup (5 minutes)

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/selene.git
cd selene/selene

# 2. Create virtual environment
python3 -m venv med_env
source med_env/bin/activate

# 3. Install package in editable mode with dev extras
pip install -e ".[dev]"

# 4. Set up pre-commit hooks
pre-commit install

# 6. Pull the MedGemma model (one-time, ~2GB download)
ollama pull MedAIBase/MedGemma1.5:4b

# 6. Run tests to verify setup
python -m pytest tests/ -v

# 7. Start the app
streamlit run app.py
```

Visit http://localhost:8501 in your browser!

## Development Workflow

### Making Changes

```bash
# 1. Create a feature branch
git checkout -b feature/your-feature-name

# 2. Make your changes
# Edit files...

# 3. Run tests
python -m pytest tests/ -v

# 4. Run linter
ruff check .
ruff format .

# 5. Commit (pre-commit hooks will run automatically)
git add .
git commit -m "feat: add awesome feature"

# 6. Push and create PR
git push origin feature/your-feature-name
```

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_deterministic_analysis.py -v

# With coverage
python -m pytest tests/ -v --cov=src/selene --cov-report=term-missing

# Watch mode (requires pytest-watch)
pip install pytest-watch
ptw tests/
```

### Code Style

We use Ruff for linting and formatting:

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

## Project Structure

```
selene/
├── app.py                          # Thin entry point
├── src/selene/                     # Installable Python package
│   ├── core/                       # Business logic
│   │   ├── med_logic.py            # LLM + RAG orchestration
│   │   ├── context_builder.py      # User context for chat
│   │   ├── context_builder_multi_agent.py  # User context for reports
│   │   ├── deterministic_analysis.py       # Stats/patterns/risk
│   │   └── insights_generator.py   # Report generation
│   ├── storage/                    # Persistence layer
│   │   ├── data_manager.py         # Profile, pulse, notes
│   │   └── chat_db.py              # Chat history DB (Chroma)
│   ├── ui/                         # Streamlit UI
│   │   ├── app.py                  # Main Streamlit app
│   │   └── views/                  # Pages (home, pulse, chat, clinical)
│   └── settings.py                 # Configuration
├── tests/                          # Test suite
├── scripts/                        # Utility scripts
├── data/                           # Runtime data (mostly gitignored)
└── docs/                           # Documentation
```

## Common Tasks

### Adding a New Feature

1. Check [ROADMAP.md](ROADMAP.md) to see if it's planned
2. Open a [Feature Request](https://github.com/innacampo/selene/issues/new?template=feature_request.md)
3. Wait for maintainer feedback/approval
4. Implement with tests
5. Update documentation
6. Submit PR

### Fixing a Bug

1. Check [existing issues](https://github.com/innacampo/selene/issues)
2. Reproduce the bug locally
3. Write a failing test that exposes the bug
4. Fix the bug
5. Verify test passes
6. Submit PR

### Updating Documentation

- README.md - High-level overview and quick start
- docs/technical_reference.md - Detailed architecture
- Docstrings - Inline code documentation
- tests/README.md - Test suite guide

## Tips

- **Run tests frequently** - Catch issues early
- **Keep PRs focused** - One feature/fix per PR
- **Write descriptive commits** - Use [Conventional Commits](https://www.conventionalcommits.org/)
- **Add tests** - All new code should have tests
- **Ask questions** - Use [Discussions](https://github.com/innacampo/selene/discussions)

## Getting Help

- 📖 [Full Documentation](README.md)
- 🏗️ [Architecture Guide](docs/technical_reference.md)
- 💬 [Discussions](https://github.com/innacampo/selene/discussions)
- 🐛 [Report Issues](https://github.com/innacampo/selene/issues)

## Next Steps

1. Explore the codebase - start with [app.py](app.py) and [src/selene/ui/app.py](src/selene/ui/app.py)
2. Run the app and try all features
3. Read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines
4. Pick a ["good first issue"](https://github.com/innacampo/selene/labels/good%20first%20issue)
5. Join the community discussions

Happy coding! 🚀
