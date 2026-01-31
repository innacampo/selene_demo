import streamlit as st
from med_logic import auto_boot_system, query_knowledge_base, call_medgemma

st.set_page_config(page_title="SELENE RAG")

# --- AUTOMATIC STARTUP ---
# This runs invisibly in the background on the first load
boot_status = auto_boot_system()

st.title("SELENE RAG")

# Optional: Show a small indicator in the sidebar instead of a big button
st.sidebar.success(boot_status)

# --- Chat Interface ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about the 2024 IMS Congress..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving research..."):
            # 1. Logic call
            context, sources = query_knowledge_base(prompt)

            # 2. Prompt construction
            full_prompt = (
                f"Using this context:\n{context}\n\nQuestion: {prompt}\nAnswer:"
            )

            # 3. Model call
            answer = call_medgemma(full_prompt)

            # 4. Display answer + expandable sources
            st.markdown(answer)
            with st.expander("View Research Sources"):
                st.write(f"Sources: {', '.join(sources)}")
                st.text(context)

    st.session_state.messages.append({"role": "assistant", "content": answer})
