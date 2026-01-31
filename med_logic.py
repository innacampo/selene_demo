import os
import subprocess
import time
import requests
import chromadb
from chromadb.utils import embedding_functions
import streamlit as st

# Config Constants
DB_PATH = "./user_med_db"
MODEL_NAME = "all-MiniLM-L6-v2"
OLLAMA_URL = "http://localhost:11434/api/tags"


def is_ollama_running():
    """Checks if the Ollama server is responding."""
    try:
        response = requests.get(OLLAMA_URL, timeout=2)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def start_ollama():
    """Starts the Ollama server in the background if it's not running."""
    if is_ollama_running():
        return "Ollama is already running."

    try:
        # Popen runs it in the background so it doesn't block your Python script
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Keeps it running even if the script closes
        )
        # Give it a few seconds to initialize
        for _ in range(5):
            if is_ollama_running():
                return "Ollama started successfully!"
            time.sleep(1)
        return "Ollama is taking a while to start..."
    except Exception as e:
        return f"Failed to start Ollama: {e}"


# (Keep your existing imports in med_logic.py)


@st.cache_resource
def auto_boot_system():
    """
    This function will run ONCE when the app starts.
    It ensures Ollama is up and ready.
    """
    if not is_ollama_running():
        status = start_ollama()
        # Optional: Pre-warm the model by calling it once
        # requests.post("http://localhost:11434/api/show", json={"name": "medgemma"})
        return f"System Initialized: {status}"
    return "System Online (Ollama already running)"


def query_knowledge_base(query):
    """Fetches top 3 chunks from ChromaDB."""
    client = chromadb.PersistentClient(path=DB_PATH)
    embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODEL_NAME
    )
    collection = client.get_collection(
        name="medical_docs", embedding_function=embedding_model
    )

    results = collection.query(query_texts=[query], n_results=3)
    # Combine text and sources for better UI display
    context = "\n---\n".join(results["documents"][0])
    sources = list(set([m["source"] for m in results["metadatas"][0]]))
    return context, sources


def call_medgemma(prompt):
    # This is where the 'Personality' lives
    system_instruction = (
        "You are Dr. Selene, an empathetic and highly knowledgeable menopause specialist. "
        "Your tone is supportive, grounded, and clinical yet accessible. "
        "Always prioritize safety and mention when findings are from recent 2024/2025 research."
    )

    full_payload = f"{system_instruction}\n\nContext and Question:\n{prompt}"

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "medgemma", "prompt": full_payload, "stream": False},
            timeout=90,
        )
        return response.json().get("response", "No response content.")
    except Exception as e:
        return f"Request failed: {e}"
