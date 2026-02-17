"""
Centralized Settings & Configuration for SELENE.

Single source of truth for all configuration constants: paths, model
identifiers, API endpoints, and tuning parameters. Import from here
instead of hardcoding values across modules.
"""
import os

# Force libraries to only look for local files — must be set before
# importing transformers, sentence_transformers, or huggingface_hub.
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
from pathlib import Path

# ============================================================================
# Base Paths
# ============================================================================

# PROJECT_ROOT = repo root (3 levels up from src/selene/settings.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BASE_DIR = PROJECT_ROOT  # backward-compat alias

DATA_DIR = PROJECT_ROOT / "data"
USER_DATA_DIR = DATA_DIR / "user_data"
PROFILE_PATH = USER_DATA_DIR / "user_profile.json"
PULSE_HISTORY_FILE = USER_DATA_DIR / "pulse_history.json"
STAGES_METADATA_PATH = DATA_DIR / "metadata" / "stages.json"
REPORTS_DIR = DATA_DIR / "reports"
OUTPUT_DIR = DATA_DIR / "output"
PAPERS_DIR = DATA_DIR / "papers"

# ============================================================================
# ChromaDB
# ============================================================================

DB_PATH = str(USER_DATA_DIR / "user_med_db")
MEDICAL_DOCS_COLLECTION = "medical_docs"
CHAT_HISTORY_COLLECTION = "chat_history"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_TELEMETRY = False

# ============================================================================
# LLM / Ollama
# ============================================================================

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 60
LLM_MODEL = "MedAIBase/MedGemma1.5:4b"

# ============================================================================
# RAG & Chat History Retrieval
# ============================================================================

RAG_TOP_K = 2
CHAT_HISTORY_TOP_K = 1
CHAT_HISTORY_DISTANCE_THRESHOLD = 0.5
MAX_SESSIONS_SHOWN = 20

# ============================================================================
# Caching
# ============================================================================

CONTEXTUALIZED_QUERY_CACHE_TTL = 300   # 5 minutes
RAG_CACHE_TTL = 600                    # 10 minutes
USER_CONTEXT_CACHE_TTL = 180           # 3 minutes
MAX_CACHE_SIZE = 100

# ============================================================================
# Logging / Observability
# ============================================================================

# Default log level for console and file handlers. Use 'DEBUG' for development,
# 'INFO' for production.
LOG_LEVEL = "DEBUG"

# Toggle file logging (rotating file handler). When True, logs are written to
# LOG_FILE_PATH as a rotating log file with LOG_MAX_BYTES and LOG_BACKUP_COUNT.
LOG_TO_FILE = True

# Path to the log file. By default, logs will be stored in the *parent* directory's
# 'logs' folder as 'selene.log'. You can change this to a full absolute path.
LOG_FILE_PATH = str(PROJECT_ROOT.parent / "logs" / "selene.log")
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Log formatting
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATEFMT = "%H:%M:%S"


# ============================================================================
# Embedding Function Factory
# ============================================================================

_embedding_function_instance = None


def get_embedding_function():
    """Return a cached ChromaDB-compatible embedding function.

    Uses ChromaDB's built-in ``SentenceTransformerEmbeddingFunction`` so the
    persisted collection metadata stays consistent (type ``sentence_transformer``).
    The model is loaded once and reused across all callers (Streamlit app and
    CLI tools like update_kb_chroma.py).
    """
    global _embedding_function_instance
    if _embedding_function_instance is None:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        _embedding_function_instance = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return _embedding_function_instance
