# Selene: Menopause Research & Longitudinal Assistant

Selene is a specialized medical AI prototype designed to bridge the gap between complex menopause research and personalized patient support. Built for the MedGemma Impact Challenge, it uses a Retrieval-Augmented Generation (RAG) architecture to provide evidence-based insights grounded in the 2024 IMS World Congress findings.

## Key Features

- **Selene Persona**: An empathetic, AI-driven menopause specialist grounded in clinical logic.
- **Dual-RAG Architecture**: Strictly separates Global Research (PDFs) from Personal History (User Logs) using multi-collection ChromaDB storage.
- **Daily Attune (Pulse)**: A specialized logging interface for tracking sleep (Rest), internal weather (Climate), and cognitive state (Clarity).
- **Automated Clinical Briefs**: Generates structured longitudinal summaries with customizable date ranges for users to share with their healthcare providers.
- **Local-First Privacy**: Powered by Ollama and MedGemma; no medical data ever leaves your machine.
- **Dynamic Symptom Analysis**: Automatically populates clinical reports with frequency data and trends based on user logs.

## Technical Stack

- **Model**: MedGemma (via Ollama)
- **Frontend**: Streamlit with Custom CSS
- **Vector Database**: ChromaDB
- **Data Persistence**: Local JSON storage for structured logs and profiles
- **Embeddings**: all-MiniLM-L6-v2 (Sentence-Transformers)
- **Orchestration**: Python

## Quick Start

### 1. Prerequisites

- Install Ollama
- Python 3.10+

### 2. Installation

Clone the repository and run the automated setup script:

```bash
git clone https://github.com/yourusername/selene-menopause-assistant.git
cd selene-menopause-assistant
bash setup_project.sh
```

### 3. Run the App

```bash
source med_env/bin/activate
streamlit run app.py
```

## Project Structure

- **app.py**: Main application entry point and router.
- **onboarding.py**: User initialization and physiological stage mapping.
- **config.py**: Global session state and app configuration.
- **data_manager.py**: Unified interface for local JSON data persistence.
- **views/**: UI pages (Home, Chat, Clinical, Pulse).
- **med_logic.py**: Core RAG engine and Ollama integration logic.
- **chat_db.py**: Database management for chat persistence and history retrieval.
- **metadata/**: Clinical lookup tables (e.g., `stages.json`).
- **user_data/**: Local encrypted storage for user profiles and pulse history.
- **styles.py**: Centralized UI styling using CSS variables.
- **user_data/user_med_db/**: Local ChromaDB storage.
- **papers/**: Directory for research PDFs used in RAG.
- **output/**: Generated artifacts.

## Medical Disclaimer

NOT MEDICAL ADVICE. Selene is a research prototype developed for educational and demonstration purposes. It does not provide medical diagnoses or treatment recommendations. Always seek the advice of a physician or other qualified health provider with any questions regarding a medical condition.

## License

Distributed under the Apache 2.0 License.