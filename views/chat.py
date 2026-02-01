import streamlit as st
from datetime import datetime
from navigation import render_header_with_back
from med_logic import query_knowledge_base, call_medgemma, Config


# ============================================================================
# Chat Utilities
# ============================================================================


def _get_current_time() -> str:
    """Returns formatted current time."""
    return datetime.now().strftime("%I:%M %p")


def _init_chat_state():
    """Initialize chat session state."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def _add_message(role: str, content: str):
    """Add a message to chat history with timestamp."""
    st.session_state.chat_history.append(
        {
            "role": role,
            "content": content,
            "timestamp": _get_current_time(),
        }
    )


# ============================================================================
# Main Render Function
# ============================================================================


def render_chat():
    """Render the chat page."""

    # Initialize state
    _init_chat_state()

    # Render header
    render_header_with_back("back_chat")

    # Page title
    st.markdown(
        '<div class="page-title">Chat with Selene</div>', unsafe_allow_html=True
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

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
        # Add user message to history
        _add_message("user", prompt)

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            # Step 1: Retrieve context (silent)
            context, sources, full_results = query_knowledge_base(
                prompt, top_k=Config.RAG_TOP_K
            )

            if isinstance(full_results, dict) and "error" in full_results:
                context = ""
                sources = []

            # Step 2: Generate response with streaming
            response_placeholder = st.empty()
            full_response = ""

            for chunk in call_medgemma(prompt, context, stream=True):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)

            # Step 3: Show sources
            if sources:
                with st.expander("Research Sources", expanded=False):
                    for result in full_results:
                        if isinstance(result, dict) and "source" in result:
                            st.markdown(f"**{result['source']}**")
                            st.caption(
                                f"Relevance: {1 - result.get('distance', 0):.1%}"
                            )
                            st.text(result.get("text", "")[:300] + "...")
                            st.divider()

        # Save assistant response to history
        _add_message("bot", full_response)

    # Add JavaScript to style user messages white
    st.markdown(
        """
        <script>
        (function() {
            // Wait for DOM to load
            setTimeout(function() {
                // Find all chat messages
                const messages = document.querySelectorAll('[data-testid="stChatMessage"]');
                messages.forEach(function(msg) {
                    // Check if it has user avatar (hidden but still in DOM)
                    const hasUserAvatar = msg.querySelector('[data-testid="stChatMessageAvatarUser"]');
                    const hasAssistantAvatar = msg.querySelector('[data-testid="stChatMessageAvatarAssistant"]');
                    
                    if (hasUserAvatar) {
                        // User message - white background
                        msg.style.backgroundColor = '#ffffff';
                        msg.style.borderColor = '#EAEAEA';
                    } else if (hasAssistantAvatar) {
                        // Assistant message - light blue background
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
