"""
SELENE Chat Interface Module.

This module implements the primary Streamlit chat view, including:
- Interactive chat history display with custom avatars.
- Multi-step optimization pipeline (Contextualization -> Retrieval -> Generation).
- Integration with ChromaDB for semantic past-discussion lookup.
- Source transparency and session management.
"""

import streamlit as st
from datetime import datetime
from selene.ui.navigation import render_header_with_back
# Import the new function from med_logic
from selene.core.med_logic import query_knowledge_base, call_medgemma_stream, contextualize_query, Config
from selene.storage.chat_db import (
    save_message,
    load_current_session,
    _ensure_session_id,
    clear_current_session,
    list_past_sessions,
    switch_to_session,
    query_chat_history,
)

def _init_chat_state() -> None:
    """Initialize session state variables for chat history and session tracking."""
    _ensure_session_id()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = load_current_session()
    if "chat_persisted_count" not in st.session_state:
        st.session_state.chat_persisted_count = len(st.session_state.chat_history)

def _add_message(role: str, content: str, rag_sources: list[str] = None) -> None:
    """
    Append a message to the local state and persist it to the database.
    
    Args:
        role: "user" or "bot".
        content: The message text.
        rag_sources: Optional list of research sources used for the response.
    """
    st.session_state.chat_history.append({
        "role": role, 
        "content": content, 
        "timestamp": datetime.now().strftime("%I:%M %p")
    })
    save_message(role, content, len(st.session_state.chat_history)-1, rag_sources or [])
    st.session_state.chat_persisted_count = len(st.session_state.chat_history)

def render_chat() -> None:
    """
    Master render function for the chat page.
    Handles user input, RAG orchestration, and LLM streaming display.
    """
    _init_chat_state()
    render_header_with_back("back_chat")

    # Header
    col1, col2 = st.columns([3, 1])
    col1.markdown('<div class="page-title">Chat with Selene</div>', unsafe_allow_html=True)
    if col2.button("+ New", use_container_width=True):
        clear_current_session()
        st.rerun()

    # Past Sessions Sidebar (Simplified for brevity)
    sessions = list_past_sessions(limit=5)
    curr_id = st.session_state.get("chat_session_id")
    if [s for s in sessions if s['session_id'] != curr_id]:
        with st.expander("Past Conversations", expanded=False):
            for s in sessions:
                if s['session_id'] == curr_id: 
                    continue
                if st.button(f"{s['first_message'][:40]}...", key=s['session_id']):
                    switch_to_session(s['session_id'])
                    st.rerun()

    # Message Display
    for msg in st.session_state.chat_history:
        role = "assistant" if msg["role"] == "bot" else "user"
        with st.chat_message(role):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Ask about symptoms, HRT, or research..."):
        _add_message("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            resp_container = st.empty()
            
            # --- OPTIMIZATION STEP 1: CONTEXTUALIZE ---
            # Rewrite query using recent history to handle "what about side effects?"
            # We grab the last 4 messages (excluding the one we just added)
            history_buffer = st.session_state.chat_history[:-1][-4:]
            
            with st.spinner("Thinking..."):
                search_query = contextualize_query(prompt, history_buffer)
                
                # --- OPTIMIZATION STEP 2: PRECISE RETRIEVAL ---
                # Use the REWRITTEN query for RAG
                context, sources, _ = query_knowledge_base(search_query)
                
                # Retrieve relevant PAST conversations (excluding current session)
                chat_res = query_chat_history(
                    query=search_query, 
                    top_k=Config.CHAT_HISTORY_TOP_K,
                    role_filter="bot",
                    exclude_session_id=curr_id
                )
                
                # Format past chats
                chat_context = ""
                relevant_chats = [r for r in chat_res if r['distance'] < Config.CHAT_HISTORY_DISTANCE_THRESHOLD]
                if relevant_chats:
                    # Filter and Truncate
                    formatted_past = []
                    for r in relevant_chats:
                        content = r['content']
                        # CAP at 1000 chars: enough for detail, short enough for 4b attention
                        if len(content) > 1000:
                            content = content[:1000] + "... [Truncated for brevity]"
        
                        formatted_past.append(f"[Past Discussion]: {content}")
    
                    chat_context = "\n\n".join(formatted_past)

            # --- OPTIMIZATION STEP 3: GENERATE WITH ROLLING BUFFER ---
            # Pass the ORIGINAL prompt + RAW history + RAG context
            full_response = ""
            for chunk in call_medgemma_stream(
                prompt=prompt, # LLM sees original prompt
                context=context, 
                chat_context=chat_context, 
                recent_history=history_buffer, # LLM sees immediate history
            ):
                full_response += chunk
                resp_container.markdown(full_response + "▌")
            
            resp_container.markdown(full_response)
            
            # Sources Expander
            if sources or relevant_chats:
                with st.expander("Sources", expanded=False):
                    if sources:
                        st.markdown(f"**Research:** {', '.join(sources)}")
                    if relevant_chats:
                        st.markdown("**Related Past Discussions found.**")

        _add_message("bot", full_response, sources)
