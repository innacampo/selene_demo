# Directory Structure Migration Guide

This document records the migration from a flat layout (all `.py` files at root) to the current **src-layout** package structure.

> **Status: COMPLETED** — All phases have been implemented and verified.

## Migration Summary

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Documentation organization (`docs/`) | ✅ COMPLETED |
| Phase 2 | Scripts organization (`scripts/`) | ✅ COMPLETED |
| Phase 3 | Data directory consolidation (`data/`) | ✅ COMPLETED |
| Phase 4 | Full src-layout package structure (`src/selene/`) | ✅ COMPLETED |
| Phase 5 | Examples & extras (`examples/`) | ✅ COMPLETED |

## What Changed

### Phase 1: Documentation Organization
- `selene_technical_reference.md` → `docs/technical_reference.md`
- Created `docs/README.md`
- Updated all cross-references in markdown files

### Phase 2: Scripts Organization
- `setup_project.sh` → `scripts/setup_project.sh`
- `update_kb_chroma.py` → `scripts/update_kb_chroma.py`
- `pdf_processor_medgemma.py` → `scripts/pdf_processor_medgemma.py`

### Phase 3: Data Directory Consolidation
- `metadata/`, `papers/`, `models/`, `output/`, `reports/`, `user_data/` → `data/`
- Updated `settings.py` with `DATA_DIR` and all derived paths

### Phase 4: src-layout Package Structure
- All Python source modules moved into `src/selene/` with subpackages:
  - `src/selene/core/` — business logic (`med_logic`, `context_builder`, `deterministic_analysis`, etc.)
  - `src/selene/storage/` — persistence (`data_manager`, `chat_db`)
  - `src/selene/ui/` — Streamlit app, navigation, onboarding, styles
  - `src/selene/ui/views/` — view pages (`home`, `pulse`, `chat`, `clinical`)
  - `src/selene/settings.py`, `constants.py`, `config.py` — configuration
- Root `app.py` is now a thin entry point: `from selene.ui.app import main; main()`
- `pyproject.toml` configured with `[tool.setuptools.packages.find] where = ["src"]`
- All imports updated to package-qualified form (e.g., `from selene.core.med_logic import ...`)
- Tests updated to import from the installed package

### Phase 5: Examples
- Created `examples/` with `basic_usage.py` and `README.md`

## Current Layout

See [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) for the full current tree.

```
selene/
├── app.py                    # Thin entry point
├── src/selene/               # Installable package
│   ├── core/                 # Business logic
│   ├── storage/              # Persistence layer
│   └── ui/                   # Streamlit UI & views
├── tests/                    # pytest suite
├── scripts/                  # Utility scripts
├── docs/                     # Documentation
├── examples/                 # Usage examples
├── data/                     # Runtime data (mostly gitignored)
└── pyproject.toml            # Build & metadata
```

## Install & Run

```bash
# Editable install (development)
pip install -e ".[dev]"

# Run the app
streamlit run app.py

# Run tests
python -m pytest tests/ -v
```

## Import Changes Reference

If you have code referencing old flat imports, update them as follows:

| Old (flat) | New (src-layout) |
|------------|-------------------|
| `import med_logic` | `from selene.core import med_logic` |
| `from context_builder import ...` | `from selene.core.context_builder import ...` |
| `from deterministic_analysis import ...` | `from selene.core.deterministic_analysis import ...` |
| `from insights_generator import ...` | `from selene.core.insights_generator import ...` |
| `from data_manager import ...` | `from selene.storage.data_manager import ...` |
| `from chat_db import ...` | `from selene.storage.chat_db import ...` |
| `import settings` | `from selene import settings` |
| `from views.clinical import ...` | `from selene.ui.views.clinical import ...` |

## Validation

All items verified:

- [x] All tests pass: `python -m pytest tests/ -v`
- [x] App launches: `streamlit run app.py`
- [x] Onboarding works
- [x] Pulse entry saves correctly
- [x] Chat loads and responds
- [x] Report generation works
- [x] PDF export works
- [x] All README links valid
- [x] CI pipeline passes

## Questions?

- See [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) for detailed structure info
- See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- Open a [Discussion](https://github.com/innacampo/selene_shell_to_brain/discussions) for questions
