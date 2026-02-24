---
title: SELENE
colorFrom: indigo
colorTo: blue
sdk: docker
app_file: app.py
pinned: false
license: cc-by-4.0
short_description: Privacy-first menopause assistant (MedGemma demo)
suggested_hardware: t4-small
models:
  - google/medgemma-1.5-4b-it
---

# SELENE

[![CI](https://github.com/innacampo/selene/actions/workflows/ci.yml/badge.svg)](https://github.com/innacampo/selene/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B.svg)](https://streamlit.io)

> Privacy-first menopause assistant: symptom tracking, RAG-backed chat, and clinician-style summaries — designed to run **fully offline** with local LLMs.

> **This is the interactive demo** of SELENE, running [MedGemma](https://huggingface.co/google/medgemma-1.5-4b-it) on a Hugging Face GPU Space so you can try the UX without installing anything. The production version runs entirely locally via [Ollama](https://ollama.com) with no internet calls whatsoever.

## Overview

- **Demo backend**: runs `google/medgemma-1.5-4b-it` locally on a HF GPU Space via `transformers` (requires `HF_TOKEN` for model access).
- **Production backend**: runs any compatible model via Ollama — fully offline, zero data leaves your machine.
- **Core flows**: Daily Attune logging, chat with RAG + safety guardrails, clinical insight reports with PDF export.

## Key Features
- Daily Attune: capture rest/internal weather/clarity + notes; validated saves with backups.
- Chat: contextualized queries, Chroma RAG, past-session recall, streaming MedGemma responses.
- Clinical summary: deterministic stats/patterns/risk + single MedGemma call; PDF export via xhtml2pdf.
- Local knowledge base: Chroma collections (medical_docs, chat_history) with SentenceTransformer embeddings.
- Safety: deterministic risk flags, conservative prompts, low temperature.

## Architecture (brief)
- RAG + LLM orchestration: [med_logic.py](src/selene/core/med_logic.py)
- Context building: [context_builder.py](src/selene/core/context_builder.py) (chat) and [context_builder_multi_agent.py](src/selene/core/context_builder_multi_agent.py) (reports)
- Deterministic analysis: [deterministic_analysis.py](src/selene/core/deterministic_analysis.py)
- Persistence: [data_manager.py](src/selene/storage/data_manager.py), [chat_db.py](src/selene/storage/chat_db.py)
- Insights reporting: [insights_generator.py](src/selene/core/insights_generator.py), UI in [views/clinical.py](src/selene/ui/views/clinical.py)
- Streamlit views: [views/home.py](src/selene/ui/views/home.py), [views/pulse.py](src/selene/ui/views/pulse.py), [views/chat.py](src/selene/ui/views/chat.py), [views/clinical.py](src/selene/ui/views/clinical.py)
- Configuration: [settings.py](src/selene/settings.py)

## Prerequisites
- Python 3.11+
- A Hugging Face token (`HF_TOKEN`) with access to `google/medgemma-1.5-4b-it`
- Basic build deps for scientific stack (numpy/scipy) and xhtml2pdf; install via requirements.txt

## Quick Start

### Deploy on Hugging Face Spaces (demo)

1. Create a new Space on [huggingface.co/new-space](https://huggingface.co/new-space) with **Docker** SDK and **T4 small** GPU.
2. Push this repo to the Space.
3. Add your `HF_TOKEN` as a **Space secret** (Settings → Repository secrets).
4. The app will build and start automatically on port 7860.

### Run locally (production — fully offline)

```bash
# 1. Clone the repository
git clone https://github.com/innacampo/selene.git
cd selene/selene

# 2. Create venv and install
python3 -m venv med_env
source med_env/bin/activate
pip install -e ".[dev]"

# 3. Set your HF token
export HF_TOKEN=hf_...

# 4. Launch app
streamlit run app.py
```

## Repository Structure

```
selene_demo/
├── app.py                    # Thin entry point
├── Dockerfile                # HF Spaces Docker build
├── src/selene/               # Installable Python package
│   ├── core/                 # Business logic (med_logic, context, analysis)
│   ├── storage/              # Persistence (data_manager, chat_db)
│   └── ui/                   # Streamlit UI & views
├── data/
│   ├── metadata/stages.json  # Menopause stage definitions
│   └── user_data/user_med_db # ChromaDB knowledge base
├── pyproject.toml            # Build config & metadata
└── requirements.txt          # Dependencies
```

## Usage

- **Daily Attune**: enter Rest/Internal Weather/Clarity + notes → saves to pulse_history.json and invalidates caches.
- **Chat**: ask questions; system contextualizes follow-ups, retrieves KB + prior chats, streams MedGemma output with sources.
- **Clinical Summary**: pick a date range; generates report if ≥3 pulse entries and completeness ≥0.4; download PDF.

## Data & Storage (local)
- Profile: `data/user_data/user_profile.json`
- Pulse history: `data/user_data/pulse_history.json` (+ backups in `data/user_data/backups/`)
- Chroma DB: `data/user_data/user_med_db` (medical_docs, chat_history)
- Reports (optional): `data/reports/`
- Logs (if enabled): `../logs/selene.log` (rotating)

## Configuration Highlights
- Paths, model ID, cache TTLs in [settings.py](src/selene/settings.py): RAG_TOP_K=2, contextualize cache 300s, RAG cache 600s, user context cache 180s.
- HF_TOKEN read from environment; model defaults to `google/medgemma-1.5-4b-it`.
- Logging defaults to INFO on Spaces; set `LOG_LEVEL=DEBUG` and `LOG_TO_FILE=1` for local development.

## Knowledge Base
- Chroma collections live under `data/user_data/user_med_db`; embeddings via SentenceTransformer all-MiniLM-L6-v2.
- Pre-built from peer-reviewed menopause literature; loaded at container start.

## Safety & Guardrails
- Deterministic risk scoring (recent 7–14 days) flags severe/rapid changes and concerning notes; injected into chat/report prompts for conservative language and referrals.
- MedGemma calls use low temperature (≤0.2) and stop tokens; evidence sections include source headers.
- Contextualization cache reduces ambiguous follow-ups; RAG returns empty-safe outputs if DB is empty.

## License

This project is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — see [LICENSE](LICENSE) for details.

The full SELENE project (with Ollama backend, tests, scripts, docs, and contributing guidelines) lives at [github.com/innacampo/selene](https://github.com/innacampo/selene).
