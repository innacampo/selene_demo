"""
Chat History Persistence Module
Stores and retrieves chat sessions with tiny-medgemma using ChromaDB.

Design notes:
- Uses the SAME PersistentClient path as med_logic (user_med_db) so there's
  only one local database on disk — but a SEPARATE collection ("chat_history").
- Embeddings ARE enabled, using the same all-MiniLM-L6-v2 model as the RAG
  knowledge base. This lets us do semantic retrieval over past conversations
  later — e.g. "what did we discuss about sleep?" can pull relevant past
  exchanges as context for the LLM, not just the static PDF knowledge base.
- Each message is one document. The session_id + message_index combo gives
  you a deterministic, sortable ID so you can always reconstruct a session
  in order.
- Metadata is kept lightweight but useful: role, timestamp, whether RAG
  context was actually retrieved for that exchange, and a short snippet of
  the RAG sources if any.
"""

import uuid
import logging
import chromadb
from chromadb.utils import embedding_functions
import streamlit as st
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration — mirrors the style of med_logic.Config
# ============================================================================


class ChatDBConfig:
    # Same DB path as med_logic so everything lives in one place on disk
    DB_PATH = "user_data/user_med_db"
    # Separate collection — keeps RAG docs and chat history cleanly partitioned
    COLLECTION_NAME = "chat_history"
    # Must match med_logic.Config.EMBEDDING_MODEL exactly — same model means
    # the vector space is consistent across both collections
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    # How many past sessions to show in the "past chats" list
    MAX_SESSIONS_SHOWN = 20


# ============================================================================
# ChromaDB Client — cached so we don't reconnect on every Streamlit rerun
# ============================================================================


@st.cache_resource(show_spinner=False)
def _get_chat_client():
    """
    Returns a (collection, None) tuple on success, cached for the app lifetime.
    Uses the same SentenceTransformer embedding model as med_logic so both
    collections live in the same vector space — consistent and efficient.
    """
    try:
        client = chromadb.PersistentClient(path=ChatDBConfig.DB_PATH)

        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=ChatDBConfig.EMBEDDING_MODEL
        )

        collection = client.get_or_create_collection(
            name=ChatDBConfig.COLLECTION_NAME,
            embedding_function=embedding_fn,
        )
        logger.info(
            f"Chat DB ready: {collection.count()} messages in '{ChatDBConfig.COLLECTION_NAME}'"
        )
        return collection, None

    except Exception as e:
        logger.error(f"Chat DB init failed: {e}")
        return None, str(e)


# ============================================================================
# Semantic Retrieval — the reason we embed
# ============================================================================


def query_chat_history(
    query: str,
    top_k: int = 5,
    role_filter: str | None = None,
    exclude_session_id: str | None = None,
) -> list[dict]:
    """
    Semantic search over past chat messages.

    This is the payoff for storing embeddings: you can ask questions like
    "what did we discuss about sleep disruptions?" and pull the most
    relevant past exchanges as context — not just keyword matches.

    Args:
        query: Natural language query to search for
        top_k: How many results to return
        role_filter: Optionally restrict to "user" or "bot" messages only.
                     Usually you want bot responses (the actual answers),
                     but filtering to user messages can help find which
                     topics have been discussed.
        exclude_session_id: Skip messages from this session. Useful when
                            you're building context for the *current*
                            conversation and don't want it to retrieve
                            itself.

    Returns:
        List of dicts, each containing:
            - content: the message text
            - role: "user" or "bot"
            - session_id: which session it came from
            - timestamp: when it was saved
            - distance: ChromaDB distance score (lower = more relevant)
            - rag_sources: what PDF sources informed that answer (if any)
    """
    collection, error = _get_chat_client()
    if collection is None:
        logger.error(f"Cannot query chat history — DB unavailable: {error}")
        return []

    if collection.count() == 0:
        return []

    try:
        # Build the where filter if any constraints are specified
        where = None
        conditions = []

        if role_filter:
            conditions.append({"role": role_filter})
        if exclude_session_id:
            conditions.append({"session_id": {"$ne": exclude_session_id}})

        if len(conditions) == 1:
            where = conditions[0]
        elif len(conditions) > 1:
            where = {"$and": conditions}

        query_kwargs = {
            "query_texts": [query],
            "n_results": min(top_k, collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        results = collection.query(**query_kwargs)

        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        return [
            {
                "content": doc,
                "role": meta.get("role", "unknown"),
                "session_id": meta.get("session_id", ""),
                "timestamp": meta.get("timestamp", ""),
                "distance": dist,
                "rag_sources": meta.get("rag_sources", ""),
            }
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]

    except Exception as e:
        logger.error(f"Chat history query failed: {e}")
        return []


# ============================================================================
# Session ID Management
# ============================================================================


def new_session_id() -> str:
    """Generate a fresh session ID. Call this when starting a new conversation."""
    return str(uuid.uuid4())


def _ensure_session_id():
    """
    Make sure st.session_state has a chat session ID.
    Creates one automatically on first load so chat.py doesn't have to
    think about it.
    """
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = new_session_id()
    return st.session_state.chat_session_id


# ============================================================================
# Core CRUD Operations
# ============================================================================


def save_message(
    role: str,
    content: str,
    message_index: int,
    rag_sources: list[str] | None = None,
    timestamp: str | None = None,
):
    """
    Persist a single chat message.

    Args:
        role: "user" or "bot"
        content: The full message text
        message_index: Sequential position in this session (0, 1, 2, ...)
                       This is what lets us reconstruct order later.
        rag_sources: List of source filenames that were pulled from ChromaDB
                     for this exchange (empty list if none were used)
        timestamp: ISO-format string; defaults to now if not provided
    """
    collection, error = _get_chat_client()
    if collection is None:
        logger.error(f"Cannot save message — DB unavailable: {error}")
        return False

    session_id = _ensure_session_id()
    timestamp = timestamp or datetime.now().isoformat()

    # Deterministic ID: session + zero-padded index.
    # Zero-padding (06d) means lexicographic sort == chronological sort,
    # which is handy if we ever need to ORDER BY id.
    doc_id = f"{session_id}_{message_index:06d}"

    metadata = {
        "session_id": session_id,
        "role": role,  # "user" or "bot"
        "message_index": message_index,  # int — position in session
        "timestamp": timestamp,
        "had_rag_context": len(rag_sources) > 0 if rag_sources else False,
        # Store sources as a comma-joined string (ChromaDB metadata must be scalar)
        "rag_sources": ", ".join(rag_sources) if rag_sources else "",
    }

    try:
        collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata],
        )
        return True

    except Exception as e:
        logger.error(f"Failed to save message {doc_id}: {e}")
        return False


def load_current_session() -> list[dict]:
    """
    Load all messages for the current session, in chronological order.
    Returns a list of dicts shaped like the existing chat_history format
    so chat.py can drop them straight into st.session_state.chat_history.

        [{"role": "user"|"bot", "content": "...", "timestamp": "..."), ...]
    """
    collection, error = _get_chat_client()
    if collection is None:
        logger.error(f"Cannot load session — DB unavailable: {error}")
        return []

    session_id = _ensure_session_id()

    try:
        results = collection.get(
            where={"session_id": session_id},
            include=["documents", "metadatas"],
        )

        if not results["ids"]:
            return []

        # Pair up documents with their metadata, then sort by message_index
        messages = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            messages.append(
                {
                    "role": meta["role"],
                    "content": doc,
                    "timestamp": meta.get("timestamp", ""),
                    "message_index": meta.get("message_index", 0),
                }
            )

        # Sort ascending by index — ChromaDB doesn't guarantee order on .get()
        messages.sort(key=lambda m: m["message_index"])

        # Strip the internal message_index before returning so the format
        # matches what chat.py already expects
        for m in messages:
            del m["message_index"]

        return messages

    except Exception as e:
        logger.error(f"Failed to load session {session_id}: {e}")
        return []


def list_past_sessions(limit: int = None) -> list[dict]:
    """
    Return a summary of recent sessions for a "past chats" UI.

    Each entry contains:
        - session_id
        - first_user_message (preview text, truncated)
        - started_at (timestamp of the first message)
        - message_count
    """
    limit = limit or ChatDBConfig.MAX_SESSIONS_SHOWN

    collection, error = _get_chat_client()
    if collection is None:
        return []

    try:
        # Pull everything — for a personal app the total message count
        # will be small enough that this is fine. If it ever grows large
        # we'd want a metadata index, but that's a bridge for later.
        all_results = collection.get(include=["documents", "metadatas"])

        if not all_results["ids"]:
            return []

        # Group messages by session_id
        sessions: dict[str, list[dict]] = {}
        for doc, meta in zip(all_results["documents"], all_results["metadatas"]):
            sid = meta["session_id"]
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append({"doc": doc, "meta": meta})

        # Build summary for each session
        summaries = []
        for sid, messages in sessions.items():
            # Sort by index to find the first user message reliably
            messages.sort(key=lambda m: m["meta"].get("message_index", 0))

            # Find the first user message for the preview
            first_user_msg = next(
                (m for m in messages if m["meta"]["role"] == "user"), None
            )

            summaries.append(
                {
                    "session_id": sid,
                    "first_message": (
                        first_user_msg["doc"][:120]
                        if first_user_msg
                        else "(no user message)"
                    ),
                    "started_at": messages[0]["meta"].get("timestamp", ""),
                    "message_count": len(messages),
                }
            )

        # Sort by started_at descending (most recent first), then trim to limit
        summaries.sort(key=lambda s: s["started_at"], reverse=True)
        return summaries[:limit]

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return []


def load_session_by_id(session_id: str) -> list[dict]:
    """
    Load a specific past session by its ID.
    Useful when the user taps on a past chat to resume/view it.
    Same return format as load_current_session().
    """
    collection, error = _get_chat_client()
    if collection is None:
        return []

    try:
        results = collection.get(
            where={"session_id": session_id},
            include=["documents", "metadatas"],
        )

        if not results["ids"]:
            return []

        messages = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            messages.append(
                {
                    "role": meta["role"],
                    "content": doc,
                    "timestamp": meta.get("timestamp", ""),
                    "message_index": meta.get("message_index", 0),
                }
            )

        messages.sort(key=lambda m: m["message_index"])

        for m in messages:
            del m["message_index"]

        return messages

    except Exception as e:
        logger.error(f"Failed to load session {session_id}: {e}")
        return []


def switch_to_session(session_id: str) -> bool:
    """
    Switch the current Streamlit session to a past chat.
    Loads that session's messages into st.session_state so the UI
    picks them up on the next rerun.
    """
    messages = load_session_by_id(session_id)
    if not messages:
        return False

    st.session_state.chat_session_id = session_id
    st.session_state.chat_history = messages
    return True


def clear_current_session():
    """
    Start a fresh conversation: new session ID, empty history in state.
    Does NOT delete the old session from the DB — it stays in past chats.
    """
    st.session_state.chat_session_id = new_session_id()
    st.session_state.chat_history = []


def delete_session(session_id: str) -> bool:
    """
    Permanently delete a session and all its messages from the DB.
    """
    collection, error = _get_chat_client()
    if collection is None:
        return False

    try:
        # Get all IDs for this session first
        results = collection.get(where={"session_id": session_id})
        if results["ids"]:
            collection.delete(ids=results["ids"])
            logger.info(
                f"Deleted session {session_id} ({len(results['ids'])} messages)"
            )
        return True

    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        return False
