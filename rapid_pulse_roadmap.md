source med_env/bin/activate

ollama run tiny-medgemma

Week 1: The "Visual Engine" (Privacy & Knowledge)
Goal: Create a working local chat that "reads" scientific papers without the internet.
Days 1–3: The "Local-First" Shell & Privacy Core
Build: Clickable mobile UI with a "Secure Enclave" indicator.
The Tech: Initializing a Local Vector Store (FAISS or ChromaDB) on the device.
Day 3 Stakeholder Demo: Show the "Airplane Mode" toggle. Ask a question, and show the app retrieving a quote from a locally stored medical PDF (e.g., NAMS 2024 Guidelines) with a source citation.
Days 4–7: The RAG Intelligence & "Pulse" Tracker
Build: Integrate a quantized Med-Gemma-2B or Llama-3-Mobile model. Connect the "Daily Pulse" tracking buttons (Sleep, Heat, Mood) to the local database.
The Tech: Implementing a Semantic Search layer that matches user logs to research "Embeddings."
Day 7 Stakeholder Demo: Log a "Hot Flash" and "Brain Fog." Ask the AI, "Why am I feeling this?" The AI responds: "Based on the 2025 Lancet study in our local library, your cluster of symptoms is typical of late-stage perimenopause..."
Week 2: The "Citizen Scientist" (Collaboration & Advocacy)
Goal: Show how private data can safely advance science and help the doctor.
Days 8–11: The Citizen Scientist & Federated Hook
Build: The Research Opt-In dashboard. Create the "Mathematical Summary" generator—it extracts trends from the user's data without identifying the user.
The Tech: A "Federated Learning" mockup. Show a progress bar: "Updating local model with the latest global research trends (Anonymized)."
Day 11 Stakeholder Demo: Show the "Knowledge Sync." Download a new "Research Patch" (e.g., a new study on Libido) and see the AI's knowledge base expand instantly without a full app update.
Days 12–14: The Clinician Bridge & Final Polish
Build: One-tap PDF Export. Finalize the "SOS Dashboard" for acute hot flash/rage relief.
The Tech: Auto-generating a professional clinical summary from the 14-day log.
Day 14 FINAL DEMO: The full loop:
Privacy: Show the "No Account" splash.
Intelligence: Ask a complex libido question; AI retrieves a cited, compassionate answer via RAG.
Advocacy: Export the 1-page PDF for the doctor.
Impact: Show the Citizen Scientist dashboard where the user's "trend" is contributed to a global menopause map.
📊 The "Show vs. Polish" Milestone Table
Sprint
What we SHOW (Stakeholder Value)
What we POLISH (Later)
Day 3
Local chat retrieving text from a PDF.
The UI animations and icons.
Day 6
Real-time correlation (e.g., Sleep vs. Mood).
Fine-tuning the AI's tone/voice.
Day 9
The "Citizen Scientist" Opt-in screen.
The backend federated server logic.
Day 12
The "Clinician Bridge" PDF generation.
Aesthetic layout of the PDF.
Day 14
The Full "SELENE" Working Prototype.
Edge-case error handling.

🛠 Your Developer "Day 1" Task List
To hit the Day 3 demo, your Lead AI Engineer must do these three things today:
Environment: Set up a local Python/Swift environment with LlamaIndex or LangChain for mobile.
Vector Store: Ingest 5 key Menopause Guidelines (PDFs) into a local FAISS index.
UI: Draft the "Daily Pulse" HUD in a low-fidelity wireframe so it can be made interactive by Day 3.




"""
# 1. Add navigation button on home page
if st.button("New Feature", key="btn_new"):
    go_to_page("new_feature")
    st.rerun()

# 2. Create render function
def render_new_feature():
    # Header with back button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back", key="back_new"):
            go_home()
            st.rerun()
    
    # Your page content here
    st.markdown('<div class="page-title">New Feature</div>', unsafe_allow_html=True)

# 3. Add to router
elif st.session_state.page == "new_feature":
    render_new_feature()
"""

