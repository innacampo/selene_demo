#!/bin/bash
set -euo pipefail

echo "Starting Selene Assistant Setup..."

# 1. Check for prerequisites
if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama not found. Please install it from https://ollama.com"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Please install Python 3.10+"
    exit 1
fi

python3 - <<'PY'
import sys
try:
    import venv  # noqa: F401
except ImportError:
    sys.exit("Python venv module missing. Install python3-venv package.")
PY

# 2. Pull MedGemma
echo "Pulling MedGemma model (this may take a few minutes)..."
ollama pull MedAIBase/MedGemma1.5:4b

# Verify Ollama service responds (helpful if serve is not running)
if command -v curl >/dev/null 2>&1; then
    if curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "Ollama service reachable at http://localhost:11434"
    else
        echo "Note: Ollama not responding on http://localhost:11434. Start it with: ollama serve"
    fi
else
    echo "Skipping Ollama reachability check (curl not available)."
fi

# 3. Setup Python Environment
echo "Setting up Python virtual environment..."
python3 -m venv med_env
source med_env/bin/activate

# 4. Install Requirements
echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing dependencies..."
python -m pip install -r requirements.txt

echo "Setup Complete!"
echo "Run the app with: source med_env/bin/activate && streamlit run app.py"
echo "If you need to seed the knowledge base, run: python update_kb_chroma.py output/medgemma_kb_*.json"