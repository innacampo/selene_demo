#!/bin/bash

echo "🚀 Starting Selene Assistant Setup..."

# 1. Check for Ollama
if ! command -v ollama &> /dev/null
then
    echo "❌ Ollama not found. Please install it from https://ollama.com"
    exit
fi

# 2. Pull MedGemma
echo "🧠 Pulling MedGemma model (this may take a few minutes)..."
ollama pull medgemma

# 3. Setup Python Environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv med_env
source med_env/bin/activate

# 4. Install Requirements
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Setup Complete!"
echo "👉 Run the app with: source med_env/bin/activate && streamlit run app.py"