# SELENE

[![CI](https://github.com/innacampo/selene_shell_to_brain/actions/workflows/ci.yml/badge.svg)](https://github.com/innacampo/selene_shell_to_brain/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B.svg)](https://streamlit.io)

> Privacy-first menopause assistant: local symptom tracking, RAG-backed chat, and clinician-style summaries powered by MedGemma.

## Overview

- **Runs fully on-device**: user data stays under `data/user_data/`; LLM calls target a local Ollama endpoint.
- **Core flows**: Daily Attune logging, chat with RAG + safety guardrails, clinical insight reports with PDF export.

## Key Features
- Daily Attune: capture rest/internal weather/clarity + notes; validated saves with backups.
- Chat: contextualized queries, Chroma RAG, past-session recall, streaming MedGemma responses.
- Clinical summary: deterministic stats/patterns/risk + single MedGemma call; PDF export via xhtml2pdf.
- Local knowledge base: Chroma collections (medical_docs, chat_history) with SentenceTransformer embeddings.
- Safety: deterministic risk flags, conservative prompts, low temperature, offline defaults.

## Architecture (brief)
- RAG + LLM orchestration: [med_logic.py](src/selene/core/med_logic.py)
- Context building: [context_builder.py](src/selene/core/context_builder.py) (chat) and [context_builder_multi_agent.py](src/selene/core/context_builder_multi_agent.py) (reports)
- Deterministic analysis: [deterministic_analysis.py](src/selene/core/deterministic_analysis.py)
- Persistence: [data_manager.py](src/selene/storage/data_manager.py), [chat_db.py](src/selene/storage/chat_db.py)
- Insights reporting: [insights_generator.py](src/selene/core/insights_generator.py), UI in [views/clinical.py](src/selene/ui/views/clinical.py)
- Streamlit views: [views/home.py](src/selene/ui/views/home.py), [views/pulse.py](src/selene/ui/views/pulse.py), [views/chat.py](src/selene/ui/views/chat.py), [views/clinical.py](src/selene/ui/views/clinical.py)
- Configuration: [settings.py](src/selene/settings.py)
- Full details: [docs/technical_reference.md](docs/technical_reference.md)

## Prerequisites
- Python 3.11+
- Ollama running locally with model `MedAIBase/MedGemma1.5:4b` pulled
- Basic build deps for scientific stack (numpy/scipy/pandas) and xhtml2pdf; install via requirements.txt

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/innacampo/selene_shell_to_brain.git
cd selene_shell_to_brain/selene

# 2. Create venv and install
python3 -m venv med_env
source med_env/bin/activate
pip install -e ".[dev]"

# 3. Pull model in Ollama (once)
ollama pull MedAIBase/MedGemma1.5:4b

# 4. Launch app
streamlit run app.py
```

Or use the setup script: `./scripts/setup_project.sh`

## Repository Structure

```
selene/
├── app.py                    # Thin entry point (from selene.ui.app import main)
├── src/selene/               # Installable Python package
│   ├── core/                 # Business logic (med_logic, context, analysis)
│   ├── storage/              # Persistence (data_manager, chat_db)
│   └── ui/                   # Streamlit UI & views
├── tests/                    # Test suite (pytest)
├── scripts/                  # Utility scripts (setup, KB management)
├── docs/                     # Documentation and guides
├── examples/                 # Example code and usage demonstrations
├── data/                     # Data directories (mostly gitignored)
├── pyproject.toml            # Build config & metadata
└── requirements.txt          # Dependencies
```

See [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) for the full tree.

## Usage

- **Daily Attune**: enter Rest/Internal Weather/Clarity + notes → saves to pulse_history.json and invalidates caches.
- **Chat**: ask questions; system contextualizes follow-ups, retrieves KB + prior chats, streams MedGemma output with sources.
- **Clinical Summary**: pick a date range; generates report if ≥3 pulse entries and completeness ≥0.4; download PDF.

## Data & Storage (local)
- Profile: `data/user_data/user_profile.json`
- Pulse history: `data/user_data/pulse_history.json` (+ backups in `data/user_data/backups/`)
- Notes (optional): `data/user_data/notes.json`
- Chroma DB: `data/user_data/user_med_db` (medical_docs, chat_history)
- Reports (optional): `data/reports/`
- Logs (if enabled): `../logs/selene.log` (rotating)

## Configuration Highlights
- Paths, model names, cache TTLs in [settings.py](src/selene/settings.py): RAG_TOP_K=2, contextualize cache 300s, RAG cache 600s, user context cache 180s.
- Offline/telemetry disabled by default via envs set in settings (TRANSFORMERS_OFFLINE, HF_*_OFFLINE, CHROMA_TELEMETRY=False).
- Logging defaults to DEBUG; file logging enabled by default (toggle LOG_TO_FILE).

## Knowledge Base Management
- Chroma collections live under `data/user_data/user_med_db`; embeddings via SentenceTransformer all-MiniLM-L6-v2.
- Import/export and collection maintenance via [scripts/update_kb_chroma.py](scripts/update_kb_chroma.py) (keeps collection IDs stable).

## Safety & Guardrails
- Deterministic risk scoring (recent 7–14 days) flags severe/rapid changes and concerning notes; injected into chat/report prompts for conservative language and referrals.
- MedGemma calls use low temperature (≤0.2) and stop tokens; evidence sections include source headers.
- Contextualization cache reduces ambiguous follow-ups; RAG returns empty-safe outputs if DB is empty.

## Testing

```bash
# Run the test suite
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ -v --cov=src/selene --cov-report=term-missing
```

Coverage focus (see [tests/README.md](tests/README.md)):
- `test_deterministic_analysis.py` — symptom mapping/stats/patterns/risk formatting
- `test_context_builder.py` — profile/pulse context, notes/chat aggregation, completeness scoring
- `test_med_logic_cache.py` — TTL cache behavior, eviction, stats, and cache invalidation helpers

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

## License

This project is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) - see [LICENSE](LICENSE) for details.

## More Documentation
- Engineering guide: [docs/technical_reference.md](docs/technical_reference.md)
