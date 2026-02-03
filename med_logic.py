"""
MedGemma RAG Logic Module
Handles ChromaDB retrieval and Ollama LLM calls.
"""

import time
import subprocess
import requests
import chromadb
from chromadb.utils import embedding_functions
import streamlit as st
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================


class Config:
    DB_PATH = "./user_med_db"
    COLLECTION_NAME = "medical_docs"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Must match import script!
    LLM_MODEL = "tiny-medgemma"  # Or "tiny-medgemma" - be consistent
    OLLAMA_BASE_URL = "http://localhost:11434"
    OLLAMA_TIMEOUT = 60
    RAG_TOP_K = 3
    # Chat history retrieval tuning — kept conservative for tiny-medgemma's
    # limited context window. The distance threshold is the main gatekeeper:
    # ChromaDB L2 distances above this are too loosely related to bother including.
    CHAT_HISTORY_TOP_K = 3
    CHAT_HISTORY_DISTANCE_THRESHOLD = 0.7


# ============================================================================
# Ollama Management
# ============================================================================


def is_ollama_running() -> bool:
    """Check if Ollama server is responding."""
    try:
        response = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def is_model_available(model_name: str) -> bool:
    """Check if specific model is loaded in Ollama."""
    try:
        response = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return any(m.get("name", "").startswith(model_name) for m in models)
    except requests.exceptions.RequestException:
        pass
    return False


def start_ollama() -> str:
    """Start Ollama server if not running."""
    if is_ollama_running():
        return "✓ Ollama already running"

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        for i in range(10):  # Wait up to 10 seconds
            if is_ollama_running():
                return "✓ Ollama started"
            time.sleep(1)

        return "⚠ Ollama starting slowly..."
    except FileNotFoundError:
        return "✗ Ollama not installed"
    except Exception as e:
        return f"✗ Failed to start Ollama: {e}"


def pull_model_if_needed(model_name: str) -> str:
    """Ensure model is available, pull if not."""
    if is_model_available(model_name):
        return f"✓ Model '{model_name}' ready"

    try:
        # Trigger model pull (this can take a while)
        response = requests.post(
            f"{Config.OLLAMA_BASE_URL}/api/pull",
            json={"name": model_name},
            timeout=300,  # 5 min for large models
        )
        if response.status_code == 200:
            return f"Model '{model_name}' pulled"
        return f"Model pull returned status {response.status_code}"
    except Exception as e:
        return f"Failed to pull model: {e}"


# ============================================================================
# ChromaDB - Cached for Performance
# ============================================================================


@st.cache_resource(show_spinner=False)
def get_chroma_collection():
    """
    Initialize ChromaDB client and collection ONCE.
    Cached by Streamlit to avoid reloading on every query.
    """
    try:
        client = chromadb.PersistentClient(path=Config.DB_PATH)

        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=Config.EMBEDDING_MODEL
        )

        collection = client.get_collection(
            name=Config.COLLECTION_NAME, embedding_function=embedding_fn
        )

        doc_count = collection.count()
        logger.info(
            f"ChromaDB loaded: {doc_count} documents in '{Config.COLLECTION_NAME}'"
        )

        return collection, None

    except Exception as e:
        logger.error(f"ChromaDB initialization failed: {e}")
        return None, str(e)


# ============================================================================
# System Initialization
# ============================================================================


@st.cache_resource(show_spinner=False)
def initialize_system():
    """
    One-time system initialization on app startup.
    Returns status dict for UI display.
    """
    status = {
        "ollama": start_ollama(),
        "model": "checking...",
        "database": "checking...",
    }

    # Check model
    if is_ollama_running():
        if is_model_available(Config.LLM_MODEL):
            status["model"] = f"✓ {Config.LLM_MODEL} ready"
        else:
            status["model"] = (
                f"⚠ {Config.LLM_MODEL} not found - run: ollama pull {Config.LLM_MODEL}"
            )
    else:
        status["model"] = "✗ Ollama not running"

    # Check database
    collection, error = get_chroma_collection()
    if collection:
        status["database"] = f"✓ {collection.count()} documents loaded"
    else:
        status["database"] = f"✗ Database error: {error}"

    return status


# ============================================================================
# RAG Functions
# ============================================================================


def query_knowledge_base(
    query: str, top_k: int = None
) -> tuple[str, list[str], list[dict]]:
    """
    Query ChromaDB for relevant documents.

    Returns:
        (context_text, source_list, full_results)
    """
    top_k = top_k or Config.RAG_TOP_K

    collection, error = get_chroma_collection()

    if collection is None:
        return "", [], {"error": error}

    if collection.count() == 0:
        return "", [], {"error": "Database is empty"}

    try:
        results = collection.query(
            query_texts=[query], n_results=min(top_k, collection.count())
        )

        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        # Combine documents into context
        context = "\n\n---\n\n".join(documents)

        # Extract unique sources
        sources = list(set(m.get("source", "Unknown") for m in metadatas))

        # Full results for UI
        full_results = [
            {
                "text": doc,
                "source": meta.get("source", "Unknown"),
                "distance": dist,
                "metadata": meta,
            }
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]

        return context, sources, full_results

    except Exception as e:
        logger.error(f"Query failed: {e}")
        return "", [], {"error": str(e)}


def call_medgemma(prompt: str, context: str = "", chat_context: str = "", stream: bool = False):
    """
    Call MedGemma via Ollama API.

    Args:
        prompt: User's question
        context: RAG context from the medical_docs knowledge base
        chat_context: Relevant past conversation excerpts from chat_history.
                      Pre-formatted by the caller — just gets dropped into the
                      prompt as-is. Empty string if nothing relevant was found.
        stream: If True, yields chunks for streaming UI
    """
    # Import here to avoid circular dependency
    try:
        from onboarding import get_profile_summary
        profile_context = get_profile_summary()
    except ImportError:
        profile_context = ""
    
    base_instruction = """You are Dr. Selene, an empathetic and highly knowledgeable menopause specialist.

Your approach:
- Supportive, grounded, and clinical yet accessible tone
- Always prioritize patient safety
- Cite when findings are from recent 2024/2025 research
- If uncertain, acknowledge limitations and recommend consulting a healthcare provider
- Structure responses clearly with bullet points when appropriate
- If relevant past conversations are provided, you may reference them to provide continuity
  (e.g. "As we discussed before...") but prioritize the research context for clinical accuracy
- Keep up to 5 sentences in your response"""
    
    # Inject user profile if available
    if profile_context:
        system_instruction = f"""{base_instruction}

{profile_context}"""
    else:
        system_instruction = base_instruction

    # Build prompt in sections. Order matters for small models: put the
    # question at the END so it's closest to where generation starts.
    sections = []

    if context:
        sections.append(f"Research Context (from knowledge base):\n{context}")

    if chat_context:
        sections.append(f"Relevant Past Conversations:\n{chat_context}")

    if sections:
        combined_context = "\n\n---\n\n".join(sections)
        full_prompt = (
            f"{combined_context}\n\n"
            f"---\n\n"
            f"Patient Question: {prompt}\n\n"
            f"Please provide a helpful, evidence-based response:"
        )
    else:
        full_prompt = (
            f"Patient Question: {prompt}\n\n"
            f"Note: No specific research context available for this query. "
            f"Please provide general guidance and recommend consulting recent "
            f"literature or a healthcare provider for specific advice."
        )

    payload = {
        "model": Config.LLM_MODEL,
        "prompt": full_prompt,
        "system": system_instruction,
        "stream": stream,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
        },
    }

    try:
        if stream:
            # Streaming response
            response = requests.post(
                f"{Config.OLLAMA_BASE_URL}/api/generate",
                json=payload,
                stream=True,
                timeout=Config.OLLAMA_TIMEOUT,
            )

            for line in response.iter_lines():
                if line:
                    import json

                    chunk = json.loads(line)
                    if "response" in chunk:
                        yield chunk["response"]
                    if chunk.get("done"):
                        break
        else:
            # Non-streaming
            response = requests.post(
                f"{Config.OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=Config.OLLAMA_TIMEOUT,
            )

            if response.status_code == 200:
                return response.json().get("response", "No response generated.")
            else:
                return f"Error: Ollama returned status {response.status_code}"

    except requests.exceptions.Timeout:
        error_msg = "Request timed out. The model may be overloaded."
        if stream:
            yield error_msg
        else:
            return error_msg
    except requests.exceptions.ConnectionError:
        error_msg = "Cannot connect to Ollama. Is it running?"
        if stream:
            yield error_msg
        else:
            return error_msg
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        if stream:
            yield error_msg
        else:
            return error_msg
