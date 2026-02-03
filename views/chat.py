import streamlit as st
from datetime import datetime
from navigation import render_header_with_back
from med_logic import query_knowledge_base, call_medgemma, Config
from chat_db import (
    save_message,
    load_current_session,
    _ensure_session_id,
    clear_current_session,
    list_past_sessions,
    switch_to_session,
    query_chat_history,
)


# ============================================================================
# Chat Utilities
# ============================================================================


def _get_current_time() -> str:
    """Returns formatted current time."""
    return datetime.now().strftime("%I:%M %p")


def _init_chat_state():
    """
    Initialize chat session state.
    On first load (or page refresh), this pulls the current session's
    messages back from ChromaDB so the conversation survives reruns.
    """
    # Ensure we have a session ID (chat_db creates one if missing)
    _ensure_session_id()

    if "chat_history" not in st.session_state:
        # Try to restore from the DB — this is what makes persistence work
        # across page refreshes and app reruns
        persisted = load_current_session()
        st.session_state.chat_history = persisted

    # Track how many messages we've already persisted this session so we
    # don't double-write on rerun. Starts at the length of whatever we
    # just loaded (or 0 for a fresh session).
    if "chat_persisted_count" not in st.session_state:
        st.session_state.chat_persisted_count = len(st.session_state.chat_history)


def _add_message(role: str, content: str, rag_sources: list[str] | None = None):
    """
    Add a message to chat history AND persist it to ChromaDB in one step.
    The message_index is just the current length of history before we append —
    so it's 0 for the first message, 1 for the second, etc.
    """
    message_index = len(st.session_state.chat_history)
    timestamp_iso = datetime.now().isoformat()
    timestamp_display = datetime.now().strftime("%I:%M %p")

    # Append to in-memory history (drives the UI)
    st.session_state.chat_history.append(
        {
            "role": role,
            "content": content,
            "timestamp": timestamp_display,
        }
    )

    # Persist to ChromaDB (survives page refresh)
    save_message(
        role=role,
        content=content,
        message_index=message_index,
        rag_sources=rag_sources or [],
        timestamp=timestamp_iso,
    )

    # Keep the persisted count in sync
    st.session_state.chat_persisted_count = len(st.session_state.chat_history)


# ============================================================================
# Past Sessions Sidebar
# ============================================================================


def _render_past_sessions_sidebar():
    """
    Render a collapsible section listing recent past conversations.
    Each one shows a preview of the first user message and lets you tap
    back into it.
    """
    sessions = list_past_sessions(limit=10)

    # Filter out the current session so it doesn't show up in "past" chats
    current_sid = st.session_state.get("chat_session_id", "")
    sessions = [s for s in sessions if s["session_id"] != current_sid]

    if not sessions:
        return  # Nothing to show — don't render the section at all

    with st.expander("Past Conversations", expanded=False):
        for i, session in enumerate(sessions):
            # Parse the ISO timestamp into something readable
            try:
                started = datetime.fromisoformat(session["started_at"]).strftime(
                    "%b %d, %I:%M %p"
                )
            except (ValueError, TypeError):
                started = "Unknown"

            # Truncate the preview text and strip any newlines
            preview = session["first_message"].replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:80] + "..."

            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(
                    f'<div style="font-size:13px; color:#555; margin-bottom:2px;">'
                    f"{started} · {session['message_count']} messages</div>"
                    f'<div style="font-size:14px; color:#333;">{preview}</div>',
                    unsafe_allow_html=True,
                )

            with col2:
                if st.button(
                    "→",
                    key=f"resume_session_{i}",
                    help="Resume this conversation",
                    use_container_width=True,
                ):
                    switch_to_session(session["session_id"])
                    st.rerun()

            st.divider()


# ============================================================================
# Main Render Function
# ============================================================================


def render_chat():
    """Render the chat page."""

    # Initialize state + restore from DB if needed
    _init_chat_state()

    # Render header
    render_header_with_back("back_chat")

    # Page title row: title + "New Chat" button side by side
    title_col, btn_col = st.columns([3, 1])
    with title_col:
        st.markdown(
            '<div class="page-title" style="text-align:left; margin-bottom:0;">Chat with Selene</div>',
            unsafe_allow_html=True,
        )
    with btn_col:
        if st.button("+ New", key="new_chat_btn", use_container_width=True):
            clear_current_session()
            st.rerun()

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Past conversations (collapsible, only shows if there are any)
    _render_past_sessions_sidebar()

    # Display chat history using Streamlit's native chat components
    if not st.session_state.chat_history:
        st.info("Hello! I'm Selene, your menopause wellness companion.")

    # Display existing messages
    for message in st.session_state.chat_history:
        role = "assistant" if message["role"] == "bot" else "user"
        with st.chat_message(role):
            st.markdown(message["content"])
            if message.get("timestamp"):
                st.caption(message["timestamp"])

    # Chat input
    if prompt := st.chat_input("Ask about menopause research, HRT, symptoms..."):
        # Add user message — this persists it too
        _add_message("user", prompt)

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            # Step 1a: Retrieve from knowledge base (PDFs)
            context, sources, full_results = query_knowledge_base(
                prompt, top_k=Config.RAG_TOP_K
            )

            if isinstance(full_results, dict) and "error" in full_results:
                context = ""
                sources = []

            # Step 1b: Retrieve from chat history (past conversations).
            # Filter by distance threshold so we only include results that are
            # actually relevant — keeps the prompt tight for tiny-medgemma.
            # We pull only bot responses here: those are the actual answers,
            # which is what gives the model useful continuity.
            chat_context = ""
            chat_results = query_chat_history(
                query=prompt,
                top_k=Config.CHAT_HISTORY_TOP_K,
                role_filter="bot",
                exclude_session_id=st.session_state.get("chat_session_id"),
            )

            # Filter to results within the distance threshold and format
            relevant_past = [
                r for r in chat_results
                if r["distance"] <= Config.CHAT_HISTORY_DISTANCE_THRESHOLD
            ]

            if relevant_past:
                # Format each past answer as a labeled block so the model can
                # parse them clearly. Include the timestamp for temporal context.
                past_blocks = []
                for i, r in enumerate(relevant_past, 1):
                    try:
                        from datetime import datetime as dt
                        ts = dt.fromisoformat(r["timestamp"]).strftime("%b %d, %Y")
                    except (ValueError, TypeError):
                        ts = "earlier"
                    past_blocks.append(
                        f"[Past conversation from {ts}]\n{r['content']}"
                    )
                chat_context = "\n\n".join(past_blocks)

            # Step 2: Generate response with streaming — pass both contexts
            response_placeholder = st.empty()
            full_response = ""

            for chunk in call_medgemma(prompt, context, chat_context, stream=True):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)

            # Step 3: Show sources
            if sources or relevant_past:
                with st.expander("Sources", expanded=False):
                    if sources:
                        st.markdown("**Research (Knowledge Base)**")
                        for result in full_results:
                            if isinstance(result, dict) and "source" in result:
                                st.markdown(f"· {result['source']}")
                                st.caption(
                                    f"Relevance: {1 - result.get('distance', 0):.1%}"
                                )
                                st.text(result.get("text", "")[:300] + "...")
                                st.divider()

                    if relevant_past:
                        st.markdown("**Past Conversations**")
                        for r in relevant_past:
                            try:
                                from datetime import datetime as dt
                                ts = dt.fromisoformat(r["timestamp"]).strftime("%b %d, %Y")
                            except (ValueError, TypeError):
                                ts = "unknown"
                            st.caption(f"From {ts} · Relevance: {1 - r['distance']:.1%}")
                            st.text(r["content"][:300] + "...")
                            st.divider()

        # Save assistant response — pass along which RAG sources were used
        # so that metadata is complete for this exchange
        _add_message("bot", full_response, rag_sources=sources)

    # Add JavaScript to style user messages white
    st.markdown(
        """
        <script>
        (function() {
            setTimeout(function() {
                const messages = document.querySelectorAll('[data-testid="stChatMessage"]');
                messages.forEach(function(msg) {
                    const hasUserAvatar = msg.querySelector('[data-testid="stChatMessageAvatarUser"]');
                    const hasAssistantAvatar = msg.querySelector('[data-testid="stChatMessageAvatarAssistant"]');
                    
                    if (hasUserAvatar) {
                        msg.style.backgroundColor = '#ffffff';
                        msg.style.borderColor = '#EAEAEA';
                    } else if (hasAssistantAvatar) {
                        msg.style.backgroundColor = '#E8F0F8';
                        msg.style.borderColor = '#d0dff0';
                    }
                });
            }, 100);
        })();
        </script>
    """,
        unsafe_allow_html=True,
    )
