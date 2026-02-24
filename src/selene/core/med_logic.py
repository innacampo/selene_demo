"""
MedGemma RAG Logic Module - Hugging Face Inference API Version
Includes: User Context, Query Contextualization, Rolling Buffer, and TTL Caching.

Calls google/medgemma-1.5-4b-it via the HF serverless Inference API using
``huggingface_hub.InferenceClient``.  No local Ollama server required.

DEBUG MODE: Set environment variable DEBUG_MEDLOGIC=1 for verbose output.
"""

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import chromadb
import streamlit as st
from chromadb.config import Settings as ChromaSettings
from huggingface_hub import InferenceClient

from selene import settings

logger = logging.getLogger(__name__)

# Per-module DEBUG override via environment variable
DEBUG_MODE = os.environ.get("DEBUG_MEDLOGIC", "0") == "1"
if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
    logger.debug("=" * 60)
    logger.debug("MedLogic DEBUG MODE ENABLED")
    logger.debug("=" * 60)

# Module-level HF Inference client (lazy-initialised via _get_hf_client)
_hf_client: InferenceClient | None = None


def _get_hf_client() -> InferenceClient:
    """Return a singleton ``InferenceClient`` for the configured HF model."""
    global _hf_client
    if _hf_client is None:
        token = settings.HF_TOKEN
        if not token:
            raise RuntimeError(
                "HF_TOKEN is not set. Add it as a Hugging Face Space secret "
                "or export HF_TOKEN=hf_... in your environment."
            )
        _hf_client = InferenceClient(
            model=settings.HF_MODEL_ID,
            token=token,
            timeout=settings.HF_TIMEOUT,
        )
        logger.info("HF InferenceClient initialised for model %s", settings.HF_MODEL_ID)
    return _hf_client


# ============================================================================
# Configuration
# ============================================================================


class Config:
    """Configuration — delegates to centralized settings.py."""

    DB_PATH = settings.DB_PATH
    COLLECTION_NAME = settings.MEDICAL_DOCS_COLLECTION
    EMBEDDING_MODEL = settings.EMBEDDING_MODEL
    LLM_MODEL = settings.LLM_MODEL
    HF_MODEL_ID = settings.HF_MODEL_ID
    HF_TIMEOUT = settings.HF_TIMEOUT
    RAG_TOP_K = settings.RAG_TOP_K
    CHAT_HISTORY_TOP_K = settings.CHAT_HISTORY_TOP_K
    CHAT_HISTORY_DISTANCE_THRESHOLD = settings.CHAT_HISTORY_DISTANCE_THRESHOLD
    CONTEXTUALIZED_QUERY_CACHE_TTL = settings.CONTEXTUALIZED_QUERY_CACHE_TTL
    RAG_CACHE_TTL = settings.RAG_CACHE_TTL
    USER_CONTEXT_CACHE_TTL = settings.USER_CONTEXT_CACHE_TTL
    MAX_CACHE_SIZE = settings.MAX_CACHE_SIZE


# ============================================================================
# Cache Infrastructure
# ============================================================================


@dataclass
class CacheEntry:
    """Generic cache entry with TTL support."""

    value: Any
    timestamp: datetime
    ttl_seconds: int

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        expired = datetime.now() > self.timestamp + timedelta(seconds=self.ttl_seconds)
        if expired:
            logger.debug(
                f"CacheEntry expired: age={(datetime.now() - self.timestamp).total_seconds():.1f}s, TTL={self.ttl_seconds}s"
            )
        return expired


class TTLCache:
    """Thread-safe TTL cache with automatic expiration and size limits."""

    def __init__(self, max_size: int = 100):
        self._lock = threading.Lock()
        self.cache: dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        """Retrieve value from cache if not expired."""
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry.is_expired():
                    del self.cache[key]
                    self.misses += 1
                    logger.debug(f"Cache EXPIRED: {key[:50]}...")
                    return None
                self.hits += 1
                logger.info(
                    f"Cache HIT: {key[:50]}... (age: {(datetime.now() - entry.timestamp).total_seconds():.1f}s)"
                )
                return entry.value
            self.misses += 1
            logger.debug(f"Cache MISS: {key[:50]}...")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int):
        """Store value in cache with TTL."""
        with self._lock:
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_oldest()
            self.cache[key] = CacheEntry(
                value=value, timestamp=datetime.now(), ttl_seconds=ttl_seconds
            )
            logger.debug(f"Cache SET: {key[:50]}... (TTL: {ttl_seconds}s)")

    def _evict_oldest(self):
        """Remove oldest cache entry. Caller must hold self._lock."""
        if not self.cache:
            return
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
        del self.cache[oldest_key]
        logger.debug(f"Cache EVICTED: {oldest_key[:50]}...")

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            logger.info("Cache CLEARED")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            return {
                "size": len(self.cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "total_requests": total_requests,
            }


# Initialize global caches
contextualized_query_cache = TTLCache(max_size=Config.MAX_CACHE_SIZE)
rag_cache = TTLCache(max_size=Config.MAX_CACHE_SIZE)
user_context_cache = TTLCache(max_size=10)  # Smaller cache for user contexts


# ============================================================================
# Cache Helper Functions
# ============================================================================


def generate_cache_key(*args, prefix: str = "") -> str:
    """Generate a deterministic cache key from arguments."""
    logger.debug(f"generate_cache_key called with prefix='{prefix}', args_count={len(args)}")
    # Convert args to a stable string representation
    key_parts = [str(arg) for arg in args]
    combined = "|".join(key_parts)
    # Hash for consistent length and privacy
    hash_digest = hashlib.sha256(combined.encode()).hexdigest()
    key = f"{prefix}:{hash_digest}" if prefix else hash_digest
    logger.debug(f"Cache key generated: {key}")
    return key


def get_user_context_hash() -> str:
    """
    Generate a hash of user context inputs to detect changes.
    This should be based on user profile data that affects context building.
    """
    logger.debug("get_user_context_hash: Generating user context hash...")
    try:
        from selene.core.context_builder import get_user_profile_hash

        hash_val = get_user_profile_hash()
        logger.debug(f"get_user_context_hash: Using profile hash: {hash_val[:20]}...")
        return hash_val
    except (ImportError, AttributeError) as e:
        # Fallback: use timestamp rounded to cache TTL
        # This ensures cache invalidation every N seconds
        logger.debug(f"get_user_context_hash: Fallback mode (reason: {type(e).__name__})")
        timestamp = int(time.time() / Config.USER_CONTEXT_CACHE_TTL)
        logger.debug(f"get_user_context_hash: Using timestamp bucket: {timestamp}")
        return str(timestamp)


# ============================================================================
# HF Inference API Health Check
# ============================================================================


def is_hf_api_available() -> bool:
    """Check if the HF Inference API is reachable and the token is valid."""
    logger.debug("is_hf_api_available: Checking HF Inference API...")
    try:
        client = _get_hf_client()
        # A lightweight call to verify connectivity
        client.model_info(settings.HF_MODEL_ID)
        logger.debug("is_hf_api_available: OK")
        return True
    except Exception as e:
        logger.debug(f"is_hf_api_available: FAILED - {type(e).__name__}: {e}")
        return False


# ============================================================================
# ChromaDB
# ============================================================================


@st.cache_resource(show_spinner=False)
def get_chroma_collection():
    """Initialize ChromaDB client and collection ONCE."""
    logger.debug("get_chroma_collection: Initializing ChromaDB...")
    logger.debug(f"  DB_PATH: {Config.DB_PATH}")
    logger.debug(f"  COLLECTION: {Config.COLLECTION_NAME}")
    logger.debug(f"  EMBEDDING_MODEL: {Config.EMBEDDING_MODEL}")
    try:
        start = time.time()
        client = chromadb.PersistentClient(
            path=Config.DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=settings.CHROMA_TELEMETRY),
        )
        logger.debug(f"  Client created in {time.time() - start:.3f}s")

        emb_start = time.time()
        embedding_fn = settings.get_embedding_function()
        logger.debug(f"  Embedding function loaded in {time.time() - emb_start:.3f}s")

        col_start = time.time()
        collection = client.get_collection(
            name=Config.COLLECTION_NAME, embedding_function=embedding_fn
        )
        logger.debug(f"  Collection retrieved in {time.time() - col_start:.3f}s")
        logger.debug(f"  Collection contains {collection.count()} documents")
        logger.info(f"get_chroma_collection: SUCCESS (total: {time.time() - start:.3f}s)")
        return collection, None
    except Exception as e:
        logger.error(f"get_chroma_collection: FAILED - {type(e).__name__}: {e}")
        return None, str(e)


# ============================================================================
# Core Logic with Caching
# ============================================================================


def contextualize_query(query: str, history: list[dict]) -> str:
    """
    Rewrites 'What about it?' into 'What about [Drug X]?' for better RAG.
    CACHED: Similar query+history combinations are cached for 5 minutes.
    """
    logger.debug("=" * 40)
    logger.debug("contextualize_query: ENTER")
    logger.debug(f"  Query: '{query[:100]}...'" if len(query) > 100 else f"  Query: '{query}'")
    logger.debug(f"  History length: {len(history)} messages")

    if not history:
        logger.debug("  No history, returning original query")
        return query

    # Generate cache key from query and recent history
    history_snippet = str(history[-2:])  # Last 2 messages
    cache_key = generate_cache_key(query, history_snippet, prefix="ctx_query")

    # Check cache first
    cached_result = contextualized_query_cache.get(cache_key)
    if cached_result is not None:
        logger.debug("  CACHE HIT: returning cached result")
        return cached_result

    logger.debug("  CACHE MISS: calling HF API for contextualization...")

    # Cache miss - perform contextualization via HF Inference API
    history_txt = "\n".join([f"{m['role'].title()}: {m['content']}" for m in history[-2:]])
    user_message = (
        f"Conversation:\n{history_txt}\n\nUser's follow-up: {query}\n\n"
        f"Task: Rewrite the follow-up as a standalone question. Output ONLY the rewritten text."
    )
    logger.debug(f"  Prompt length: {len(user_message)} chars")

    try:
        start_time = time.time()
        client = _get_hf_client()
        response = client.chat_completion(
            messages=[{"role": "user", "content": user_message}],
            max_tokens=128,
            temperature=0.1,
        )
        duration = time.time() - start_time

        rewritten = response.choices[0].message.content.strip()
        logger.debug(
            f"  Rewritten query: '{rewritten[:100]}...'"
            if len(rewritten) > 100
            else f"  Rewritten: '{rewritten}'"
        )

        result = rewritten if len(rewritten) > 3 else query
        if result == query:
            logger.debug("  Using original query (rewritten too short)")

        # Cache the result
        contextualized_query_cache.set(cache_key, result, Config.CONTEXTUALIZED_QUERY_CACHE_TTL)
        logger.info(
            f"contextualize_query: {duration:.3f}s (cached for {Config.CONTEXTUALIZED_QUERY_CACHE_TTL}s)"
        )

        return result
    except Exception as e:
        logger.warning(f"contextualize_query: FAILED - {type(e).__name__}: {e}")
        logger.debug("  Returning original query due to error")
        return query


def query_knowledge_base(query: str, top_k: int | None = None) -> tuple[str, list[str], list[dict]]:
    """
    Query ChromaDB for relevant documents with Section-Aware formatting.
    CACHED: Identical queries are cached for 10 minutes.
    """
    logger.debug("=" * 40)
    logger.debug("query_knowledge_base: ENTER")
    logger.debug(f"  Query: '{query[:80]}...'" if len(query) > 80 else f"  Query: '{query}'")

    top_k = top_k or Config.RAG_TOP_K
    logger.debug(f"  top_k: {top_k}")

    # Generate cache key from query and parameters
    cache_key = generate_cache_key(query, top_k, prefix="rag")

    # Check cache first
    cached_result = rag_cache.get(cache_key)
    if cached_result is not None:
        logger.debug("  CACHE HIT: returning cached RAG result")
        return cached_result

    logger.debug("  CACHE MISS: performing RAG retrieval...")

    # Cache miss - perform RAG retrieval
    collection, error = get_chroma_collection()

    if collection is None:
        logger.error(f"  ChromaDB unavailable: {error}")
        return "", [], [{"error": error}]

    doc_count = collection.count()
    logger.debug(f"  Collection has {doc_count} documents")

    if doc_count == 0:
        logger.warning("  Database is empty!")
        return "", [], [{"error": "Database is empty"}]

    try:
        start_time = time.time()
        n_results = min(top_k, doc_count)
        logger.debug(f"  Querying for {n_results} results...")

        results = collection.query(query_texts=[query], n_results=n_results)
        duration = time.time() - start_time
        logger.info(f"query_knowledge_base: RAG retrieval {duration:.3f}s")

        documents = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        logger.debug(f"  Retrieved {len(documents)} documents")
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances, strict=False)):
            logger.debug(
                f"    [{i}] dist={dist:.4f}, source={meta.get('source', 'Unknown')[:30]}, len={len(doc)}"
            )

        # --- Formatted Context Injection ---
        formatted_chunks = []
        for doc, meta in zip(documents, metadatas, strict=False):
            source = meta.get("source", "Unknown Source")
            section = meta.get("section", "General Context")

            header = f"SOURCE: {source} | SECTION: {section.upper()}"
            formatted_chunks.append(f"[{header}]\n{doc}")

        context = "\n\n---\n\n".join(formatted_chunks)
        sources = list({m.get("source", "Unknown") for m in metadatas})

        logger.debug(f"  Context total length: {len(context)} chars")
        logger.debug(f"  Unique sources: {sources}")

        full_results = [
            {
                "text": doc,
                "source": meta.get("source", "Unknown"),
                "distance": dist,
                "metadata": meta,
            }
            for doc, meta, dist in zip(documents, metadatas, distances, strict=False)
        ]

        result = (context, sources, full_results)

        # Cache the result
        rag_cache.set(cache_key, result, Config.RAG_CACHE_TTL)
        logger.info(f"query_knowledge_base: cached for {Config.RAG_CACHE_TTL}s")

        return result

    except Exception as e:
        logger.error(f"query_knowledge_base: FAILED - {type(e).__name__}: {e}")
        return "", [], [{"error": str(e)}]


def get_user_context_cached() -> str:
    """
    Get user context with caching to avoid rebuilding on every call.
    CACHED: User context is cached for 3 minutes or until profile changes.
    """
    logger.debug("=" * 40)
    logger.debug("get_user_context_cached: ENTER")

    # Generate cache key based on user profile state
    profile_hash = get_user_context_hash()
    cache_key = generate_cache_key(profile_hash, prefix="user_ctx")

    # Check cache first
    cached_context = user_context_cache.get(cache_key)
    if cached_context is not None:
        logger.debug(f"  CACHE HIT: returning cached context ({len(cached_context)} chars)")
        return cached_context

    logger.debug("  CACHE MISS: building user context...")

    # Cache miss - build user context
    try:
        from selene.core.context_builder import build_user_context

        start_time = time.time()
        logger.debug("  Calling build_user_context()...")
        user_context = build_user_context(
            include_profile=True,
            include_recent_pulse=True,
            include_pulse_analysis=False,
            recent_pulse_days=7,
        )
        duration = time.time() - start_time

        logger.debug(f"  Built context: {len(user_context)} chars in {duration:.3f}s")

        # Cache the result
        user_context_cache.set(cache_key, user_context, Config.USER_CONTEXT_CACHE_TTL)
        logger.info(
            f"get_user_context_cached: built {len(user_context)} chars in {duration:.3f}s (cached {Config.USER_CONTEXT_CACHE_TTL}s)"
        )

        return user_context
    except ImportError as e:
        logger.warning(f"get_user_context_cached: context_builder not found - {e}")
        return ""


def _build_medgemma_messages(
    prompt: str,
    context: str = "",
    chat_context: str = "",
    recent_history: list[dict] | None = None,
) -> list[dict]:
    """
    Build the chat-completion messages list for MedGemma.
    Returns a list of ``{"role": ..., "content": ...}`` dicts suitable for
    ``InferenceClient.chat_completion()``.
    """
    logger.debug("=" * 60)
    logger.debug("_build_medgemma_messages: ENTER")
    logger.debug(f"  Prompt: '{prompt[:80]}...'" if len(prompt) > 80 else f"  Prompt: '{prompt}'")
    logger.debug(f"  Context length: {len(context)} chars")
    logger.debug(f"  Chat context length: {len(chat_context)} chars")
    logger.debug(f"  Recent history: {len(recent_history) if recent_history else 0} messages")
    logger.debug(f"  Model: {Config.HF_MODEL_ID}")

    # Get user context (cached)
    logger.debug("  Fetching user context...")
    user_context = get_user_context_cached()
    logger.debug(f"  User context: {len(user_context)} chars")

    # System instruction
    system_instruction = """You are SELENE, a menopause reasoning engine.
        IDENTITY: Synthesize user data with your clinical training and the [RESEARCH CONTEXT — CURATED, RECENT].
        KNOWLEDGE HIERARCHY:
        1. Ground claims in [RESEARCH CONTEXT — CURATED, RECENT], but weave findings naturally into the narrative.
        2. Use internal medical knowledge to explain the "why" (pathophysiology).

        TONE & STYLE:
        - Warm and grounding.
        - **HARD NEGATIVE**: Never use phrases like "It's understandable," "I understand," or "It is normal to feel."
        - **NO PREAMBLES**: Do not offer validation or empathetic scripts.
        - Avoid clinical coldness; maintain a "companion" feel while providing academic-level insights.
        - No names. No formulaic empathy.
        - **CRITICAL**: Do not start responses or paragraphs with "Based on the research," "According to the context," or similar disclaimers.
        - Speak with calm, direct authority. Integrate evidence as if it is your own expert knowledge.
        - Always respond in English.

        CONSTRAINTS:
        - Never prescribe; always suggest discussing specific findings with an informed clinician."""

    # Build the dynamic context block
    sections = []

    if user_context:
        sections.append(f"[PATIENT PROFILE & RECENT SYMPTOMS]:\n{user_context}")

    if context:
        sections.append(f"[RESEARCH CONTEXT — CURATED, RECENT]:\n{context}")

    if chat_context:
        sections.append(f"[RELEVANT PAST CONVERSATIONS]:\n{chat_context}")

    # Add rolling buffer for immediate continuity
    if recent_history:
        current_chars = 0
        buffered_messages = []
        MAX_HISTORY_CHARS = 1200

        for m in reversed(recent_history):
            role = "Patient" if m["role"] == "user" else "Selene"
            msg_line = f"{role}: {m['content']}\n"

            if current_chars + len(msg_line) > MAX_HISTORY_CHARS:
                break

            buffered_messages.insert(0, msg_line)
            current_chars += len(msg_line)

        hist_str = "[IMMEDIATE CONVERSATION HISTORY]:\n" + "".join(buffered_messages)
        sections.append(hist_str)

    # Assemble the user message with "Double-Wrap"
    if sections:
        combined_context = "\n\n---\n\n".join(sections)
        user_message = (
            f"PRIMARY TASK: Analyze the user's situation and provide insight.\n"
            f"Patient Question: {prompt}\n\n"
            f"---\n\n"
            f"{combined_context}\n\n"
            f"---\n\n"
            f"Patient Question: {prompt}\n\n"
            f"Provide a clear, direct explanation for the patient:"
        )
    else:
        user_message = prompt

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_message},
    ]

    # Prompt size debugging
    total_len = len(user_message)
    base_len = len(system_instruction)
    user_len = len(user_context) if user_context else 0
    rag_len = len(context) if context else 0
    past_len = len(chat_context) if chat_context else 0
    recent_len = (
        sum(len(f"{m['role']}: {m['content']}") for m in recent_history) if recent_history else 0
    )

    logger.info("Prompt Breakdown (chars):")
    logger.info(f"  - Base System:    {base_len:>6}")
    logger.info(
        f"  - User Context:   {user_len:>6} ({user_len / total_len * 100 if total_len > 0 else 0:>4.1f}%) [CACHED]"
    )
    logger.info(
        f"  - Knowledge Base: {rag_len:>6} ({rag_len / total_len * 100 if total_len > 0 else 0:>4.1f}%)"
    )
    logger.info(
        f"  - Past Discs:     {past_len:>6} ({past_len / total_len * 100 if total_len > 0 else 0:>4.1f}%)"
    )
    logger.info(
        f"  - Immediate Hist: {recent_len:>6} ({recent_len / total_len * 100 if total_len > 0 else 0:>4.1f}%)"
    )
    logger.info(f"  - TOTAL:          {total_len:>6}")

    return messages


def call_medgemma(
    prompt: str,
    context: str = "",
    chat_context: str = "",
    recent_history: list[dict] | None = None,
) -> str:
    """
    Call MedGemma via HF Inference API and return the complete response.
    Uses cached user context to avoid rebuilding on every call.
    """
    messages = _build_medgemma_messages(prompt, context, chat_context, recent_history)
    try:
        start_time = time.time()
        client = _get_hf_client()
        logger.debug(f"  Calling HF chat_completion (model={Config.HF_MODEL_ID})...")
        response = client.chat_completion(
            messages=messages,
            max_tokens=512,
            temperature=0.2,
            top_p=0.8,
            stop=["Patient:", "=== USER PROFILE ===", "Note:", "Disclaimer:"],
        )
        duration = time.time() - start_time
        result = response.choices[0].message.content
        logger.info(f"call_medgemma: received {len(result)} chars in {duration:.3f}s")
        logger.debug(
            f"  Response preview: '{result[:100]}...'"
            if len(result) > 100
            else f"  Response: '{result}'"
        )
        return result
    except Exception as e:
        logger.error(f"call_medgemma: FAILED - {type(e).__name__}: {e}")
        return f"Error: {str(e)}"


def call_medgemma_stream(
    prompt: str,
    context: str = "",
    chat_context: str = "",
    recent_history: list[dict] | None = None,
):
    """
    Call MedGemma with streaming via HF Inference API.
    Yields response text chunks as they arrive.
    """
    messages = _build_medgemma_messages(prompt, context, chat_context, recent_history)
    try:
        start_time = time.time()
        client = _get_hf_client()
        logger.debug("  HF streaming mode enabled")
        stream = client.chat_completion(
            messages=messages,
            max_tokens=512,
            temperature=0.2,
            top_p=0.8,
            stop=["Patient:", "=== USER PROFILE ===", "Note:", "Disclaimer:"],
            stream=True,
        )
        chunk_count = 0
        total_chars = 0
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                chunk_count += 1
                total_chars += len(text)
                yield text
        duration = time.time() - start_time
        logger.info(
            f"call_medgemma_stream: streamed {chunk_count} chunks, {total_chars} chars in {duration:.3f}s"
        )
    except Exception as e:
        logger.error(f"call_medgemma_stream: FAILED - {type(e).__name__}: {e}")
        yield f"Error: {str(e)}"


# ============================================================================
# Cache Management Functions
# ============================================================================


def get_cache_stats() -> dict[str, Any]:
    """Get statistics for all caches."""
    stats = {
        "contextualized_query": contextualized_query_cache.get_stats(),
        "rag": rag_cache.get_stats(),
        "user_context": user_context_cache.get_stats(),
    }
    logger.debug(f"Cache stats: {stats}")
    return stats


def clear_all_caches():
    """Clear all caches. Useful for testing or when data changes."""
    logger.debug("clear_all_caches: Clearing all caches...")
    contextualized_query_cache.clear()
    rag_cache.clear()
    user_context_cache.clear()
    logger.info("clear_all_caches: All caches cleared")


def invalidate_user_context_cache():
    """Invalidate user context cache when profile data changes."""
    logger.debug("invalidate_user_context_cache: Clearing user context cache...")
    user_context_cache.clear()
    logger.info("invalidate_user_context_cache: User context cache invalidated")


def invalidate_rag_cache():
    """Invalidate RAG cache when knowledge base is updated."""
    logger.debug("invalidate_rag_cache: Clearing RAG cache...")
    rag_cache.clear()
    logger.info("invalidate_rag_cache: RAG cache invalidated")
