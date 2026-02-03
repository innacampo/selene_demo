# Selene: Menopause Research & Longitudinal Assistant

Selene is a specialized medical AI prototype designed to bridge the gap between complex menopause research and personalized patient support. Built for the MedGemma Impact Challenge, it uses a Retrieval-Augmented Generation (RAG) architecture to provide evidence-based insights grounded in the 2024 IMS World Congress findings.

## Key Features

- **Dr. Selene Persona**: An empathetic, AI-driven menopause specialist grounded in clinical logic.
- **Dual-RAG Architecture**: Strictly separates Global Research (PDFs) from Personal History (User Logs) using multi-collection ChromaDB storage.
- **Personalized Research Alerts**: Connects your recent symptoms directly to the latest clinical breakthroughs.
- **Automated Clinical Briefs**: Generates structured longitudinal summaries of symptoms for users to share with their healthcare providers.
- **Local-First Privacy**: Powered by Ollama and MedGemma; no medical data ever leaves your machine.
- **Advanced Chat History**: Persistent conversation history with ability to reference past context using vector-based retrieval.

## Technical Stack

- **Model**: MedGemma (via Ollama)
- **Frontend**: Streamlit with Custom CSS
- **Vector Database**: ChromaDB
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
- **views/**: Contains UI pages (Home, Chat, Clinical, Pulse).
- **med_logic.py**: Core RAG engine and Ollama integration logic.
- **chat_db.py**: Database management for chat persistence and history retrieval.
- **styles.py**: Centralized UI styling using CSS variables.
- **user_med_db/**: Local ChromaDB storage.
- **papers/**: Directory for research PDFs used in RAG.
- **output/**: Generated artifacts.

## Medical Disclaimer

NOT MEDICAL ADVICE. Selene is a research prototype developed for educational and demonstration purposes. It does not provide medical diagnoses or treatment recommendations. Always seek the advice of a physician or other qualified health provider with any questions regarding a medical condition.

## License

Distributed under the Apache 2.0 License.