# SELENE — Technical Reference (Engineering & Maintainer Guide) 

> Author: Inna Campo
> Last updated: 2026-02-08  
> Purpose: A precise, technical description of SELENE’s design, data flows, runtime behavior, safety guardrails, and code responsibilities for engineers, reviewers, and future maintainers.

---

## Table of contents
1. System Overview 
2. High-Level Architecture 
3. Data & Knowledge Flow 
4. Reasoning Engine (MedGemma) 
5. User Interaction Flows (Home, Attune, Insights, SOS) 
6. Clinical Safety & Scope 
7. Privacy & Security 
8. Code Structure & Conventions 
9. Deployment & Runtime Considerations 
10. Testing & Validation 
11. Future Extensions & Technical Debt 
12. Assumptions (explicit) 

---

## 1. System Overview

### Purpose & scope
- SELENE is an on-device, **privacy-first** assistant for menopause-related neuroendocrine symptom tracking and clinically-informed insight generation.
- Primary capabilities:
  - Structured daily symptom capture ("Daily Attune" / Pulse).
  - Evidence-grounded retrieval (RAG) over a local medical knowledge base.
  - A hybrid reasoning pipeline (deterministic math layer + MedGemma LLM) to synthesize human-readable insights and risk assessments.
  - Local persistence of user data (profile, pulse history, chat sessions).
- Audience for this document: engineers, code reviewers, maintainers.

### Design goals
- **Privacy-first**: keep personal data local (USER_DATA_DIR). Limit network I/O to a local LLM server (Ollama) only.
- **On-device inference**: run models locally (configured via Ollama URL, default: localhost:11434).
- **Clinical safety**: deterministic rule-based checks and risk-tiered escalation logic reduce hallucination and ensure conservative advice.
- **Explainability & traceability**: RAG preserves source metadata for evidence attribution and post-hoc inspection.

### Non-goals and explicit limitations
- Not a medical device; not certified clinical software.
- Not intended to make diagnoses or issue prescriptions.
- Not a substitute for clinical evaluation—explicit referral triggers should direct users to clinicians.
- No built-in encrypted-at-rest storage (see “Assumptions” & “Privacy” for details).
- Not resilient to a fully compromised host: if the machine is compromised, confidentiality guarantees are limited.

---

## 2. High-Level Architecture

### Major components (modules & responsibilities)
- UI (Streamlit views):
  - `views/home.py` — dashboard
  - `views/pulse.py` — Daily Attune data capture
  - `views/chat.py` — interactive chat with RAG and streaming LLM
  - `views/clinical.py` — clinical summary & insights
- Persistence:
  - `data_manager.py` — JSON-based pulse and profile persistence
  - `chat_db.py` — chat session persistence (Chroma collection `chat_history`)
  - ChromaDB (under `user_data/user_med_db`) — `medical_docs` (knowledge base) + `chat_history`
- Reasoning & retrieval:
  - `med_logic.py` — RAG orchestration, caching, contextualization, MedGemma calls
  - `context_builder.py` / `context_builder_multi_agent.py` — user snapshot & pulse aggregation
  - `deterministic_analysis.py` — math layer: statistics, pattern detection, rule-based risk scoring
  - `insights_generator.py` — deterministic pre-processing + single MedGemma call for report generation (uses `context_builder_multi_agent` context)
  - `context_builder_multi_agent.py` — aggregates profile, pulse history, notes, and chat into a unified context for reports
- Knowledge ingestion & CLI:
  - `update_kb_chroma.py` — import/export tools for Chroma DB
- Configuration:
  - `settings.py` — single source of truth for paths, model names, TTLs, etc.

### On-device inference flow (simplified)
1. User sends input via UI (chat or ask for clinical summary).
2. `med_logic.contextualize_query()` rewrites follow-ups (cached).
3. `med_logic.query_knowledge_base()` queries Chroma (`medical_docs`) using the embedding function (settings.get_embedding_function()).
4. `med_logic._prepare_medgemma_request()` assembles:
   - system instruction (see Section 4)
   - [PATIENT PROFILE], [RESEARCH CONTEXT — CURATED], [RELEVANT PAST CONVERSATIONS], and immediate rolling buffer of recent chat.
5. LLM call via `med_logic.call_medgemma()` or streaming `call_medgemma_stream()` to local Ollama endpoint (`settings.OLLAMA_BASE_URL`).
6. Response is rendered in UI; messages + metadata saved to `chat_history` collection via `chat_db.save_message()`.

### Data boundary diagram (ASCII)
```
[UI (Streamlit)] 
    ↕ (prompt, cached history, session state)
[med_logic.py]
    ↕ (contextualize, cache)
[ChromaDB] <---> [settings.get_embedding_function()]   (local persistent DB under user_data)
    ↕
[Ollama (Local HTTP) -> MedGemma model]  (local LLM server on localhost)
    ↕
[deterministic_analysis.py]  (in-process deterministic analysis used in chat/report prompts)
```

---

## 3. Data & Knowledge Flow

### User input lifecycle
- Input -> UI (`views/chat.py` or `views/pulse.py`) -> med_logic pipeline.
- Chat messages are persisted to Chroma `chat_history` via `chat_db.save_message()` (IDs are deterministic: `sessionid_index`).
- Pulse (Daily Attune) entries are stored in JSON at `settings.PULSE_HISTORY_FILE` by `data_manager.save_pulse_entry()`.

### Prior conversation injection
- Previous session messages are semantically searchable using `chat_db.query_chat_history()`.
- Candidates are filtered by proximity (`distance < CHAT_HISTORY_DISTANCE_THRESHOLD`) and inserted into the LLM prompt under `[RELEVANT PAST CONVERSATIONS]`.
- Immediate “rolling buffer” of recent messages is also injected (max char cap ~1200).

### Vector-based retrieval (RAG)
- Knowledge base stored in Chroma `medical_docs`.
- Embeddings via `settings.get_embedding_function()` (SentenceTransformer).
- `med_logic.query_knowledge_base()` performs retrieval, formats chunks with `SOURCE` and `SECTION`, and returns (context, sources, full_results).
- `update_kb_chroma.py` provides tools to import Chroma exports, clear collection contents safely, and keep collection IDs stable.

### Evidence passed to the reasoning model
- `med_logic._prepare_medgemma_request()` composes:
  - System instruction (explicit constraints)
  - `[PATIENT PROFILE & RECENT SYMPTOMS]` (from `context_builder.build_user_context()`)
  - `[RESEARCH CONTEXT — CURATED, RECENT]` (from RAG formatted chunks)
  - `[RELEVANT PAST CONVERSATIONS]` (from `chat_db`)
  - `[IMMEDIATE CONVERSATION HISTORY]` (rolling buffer)
- The prompt is deliberately "double-wrapped" (question repeated post-context) to reduce context misalignment.

### Transient vs. persisted data
- Persisted:
  - `user_profile.json` (settings.PROFILE_PATH)
  - `pulse_history.json` (settings.PULSE_HISTORY_FILE) with rolling backups in `user_data/backups/pulse_history_*.json`
  - ChromaDB storage in `user_data/user_med_db` (`medical_docs`, `chat_history`)
  - Saved reports (optional) in `reports/`
  - Logs when enabled: `logs/selene.log` (toggle via `settings.LOG_TO_FILE`)
- Transient (in-memory only):
  - LLM request/response payloads (except saved chats + metadata)
  - Cache entries (TTL caches in `med_logic.py`)
  - streaming chunks from MedGemma
- Guarantee: the system is designed so **no user data is uploaded to external services by default**. Network I/O is limited to local Ollama endpoint and local file system access.

### What never leaves the device (by design)
- User profile, pulse entries, chat history, and local knowledge base contents **are not transmitted externally** by the provided code paths.
- Chroma telemetry is disabled (`CHROMA_TELEMETRY = False`). Transformers/HF offline flags are set in `settings.py`.

---

## 4. Reasoning Engine

### Model choice: MedGemma
- Configured model: `settings.LLM_MODEL = "MedAIBase/MedGemma1.5:4b"`.
- Rationale:
  - Domain-adapted medical reasoning (specialized training for menopause/clinical texts).
  - Size and local-run compatibility balance for edge devices when deployed via Ollama.
  - Controlled temperature & options set in `med_logic._prepare_medgemma_request()` (temperature <= 0.2 for patient-facing responses).

### Prompt structure & system instructions (summary)
- System Instruction high-level goals (exact text in `med_logic._prepare_medgemma_request()`):
  - Identity: "You are SELENE, a menopause reasoning engine."
  - Knowledge hierarchy: ground claims in curated research context, explain pathophysiology.
  - Tone & style: warm, grounding, avoid certain phrases; **no empathy preambles**, avoid formulaic statements.
  - Constraints: **Never prescribe**; suggest discussing with a clinician.
- Prompt assembly:
  - Sections appended: `[PATIENT PROFILE & RECENT SYMPTOMS]`, `[RESEARCH CONTEXT — CURATED, RECENT]`, `[RELEVANT PAST CONVERSATIONS]`, `[IMMEDIATE CONVERSATION HISTORY]`.
  - Double-wrap technique: repeat the primary patient question after context.

### Guardrails, safety boundaries, and uncertainty handling
- Deterministic checks in `deterministic_analysis.py` create rule-based risk scores.
  - `assess_risk_level(entries)` returns `level` ∈ {low, moderate, high} plus flags and a human-readable `rationale`.
- Risk scores are injected into prompts (chat + reports) to force conservative language and explicit referral phrasing; no separate agent gating layer.
- Prompt options favor low temperature and controlled decoding (`stop` tokens, `num_predict` limit).
- Halting & timeout behavior: `med_logic.call_medgemma` handles timeouts with explicit messages. Streaming call yields errors when necessary.

### Evidence attribution logic
- RAG returns `sources` (extracted from chunk `metadata['source']`) and formatted chunk headers (`SOURCE: <file> | SECTION: <section>`).
- Chat responses include an expander with sources; messages saved by `chat_db.save_message()` include `rag_sources` metadata (string-joined).
- `update_kb_chroma.py` supports section-aware JSON imports to maintain "source" metadata for attribution.

### How hallucination risk is mitigated
- Deterministic math and hybrid architecture:
  - Critical numeric and pattern detection tasks executed deterministically (`deterministic_analysis.py`).
  - LLM is used for interpretation and narrative synthesis only—interprets deterministic outputs and curated RAG context.
- Low temperature + stop tokens + conservative system instruction.
- Evidence anchor: LLM must reference the RAG context; source lists are surfaced to the user.
- Cache & rewriting policies reduce ambiguous short prompts (contextualization step rewrites follow-ups into standalone queries).

---

## 5. User Interaction Flows

### Home screen logic (`views/home.py`)
- Rendered with stage-specific UI content from `metadata/stages.json`.
- Buttons:
  - "Chat with Selene" -> `chat` view
  - "Clinical Summary" -> `clinical` view
  - "Daily Attune" -> `pulse` view

### Attune flow (Daily Pulse) (`views/pulse.py`) 💡
- Three pillars: Rest, Internal Weather, Clarity + Notes.
- On Save:
  - `data_manager.save_pulse_entry()` appends entry with timestamp to `pulse_history.json`.
  - Calls `med_logic.invalidate_user_context_cache()` to ensure next LLM queries use updated context.

### Insight generation (`insights_generator.py`) 📊
- Single-LLM pipeline with deterministic pre-processing:
  - `generate_insights_report()` builds context via `context_builder_multi_agent.build_complete_context()` (profile, pulse entries, notes, user chat; date-filtered).
  - Validation gates: requires ≥3 pulse entries in the selected range and `data_completeness_score >= 0.4` (profile/pulse/notes/chat coverage); otherwise returns an error string instead of calling the LLM.
  - Deterministic layer (`DeterministicAnalyzer`) computes statistics, patterns, and risk (`assess_risk_level`) and injects them into the prompt.
  - A single MedGemma call generates markdown with four required sections (“How You've Been”, “What Your Body Is Telling You”, “Patterns & Connections”, “For Your Provider”).
  - PDF export is handled in `views/clinical.py` via `generate_insights_pdf()` (Markdown → HTML → PDF with `xhtml2pdf`).

### Clinical summary view (`views/clinical.py`)
- Date-range picker drives the report period; reports are cached in `st.session_state` per range to avoid redundant generation.
- Uses `generate_insights_report()` and stores `clinical_report` + `clinical_metrics`; on validation failure the user sees the error string instead of stale content.
- Export button builds PDF via `format_report_for_pdf()` + `generate_insights_pdf()` with a stage/timestamp header and disclaimer.

### SOS / urgent behavior
- Not a literal "SOS button" in UI; "SOS mode" described here as reaction to high-risk flags.
- Deterministic `assess_risk_level()` sets `level` (low/moderate/high) and flags (e.g., `persistent_poor_sleep`, `severe_hot_flashes`, `concerning_user_notes`).
  - `score >= 6` → `high` → Report/LLM copy uses urgent language and **explicit** referral: "Seek urgent evaluation within X days" plus warning signs (e.g., chest pain, sudden severe headache).
  - If immediate emergency signs are present (keywords like "emergency" in notes or certain high flag combinations), instructions include immediate medical attention and red-flag warning signs.
- UI should present high-risk messaging with explicit action items, and avoid prescriptive medical orders.

### Edge cases & interruption handling
- If Ollama is unavailable, `med_logic.is_ollama_running()` / `start_ollama()` provide checks and attempts to start service; calling functions return errors or safe fallback messages.
- If Chroma DB is empty, RAG returns an empty context and code gracefully degrades (message shows “Database is empty”).
- Streaming interruptions yield partial content and error messages from `call_medgemma_stream()`.

---

## 6. Clinical Safety & Scope

### What SELENE can do
- Track symptom trends and provide evidence-grounded, clinician-style interpretations.
- Surface sources for claims and provide a structured report to bring to a clinician.
- Detect patterns and trigger conservative risk recommendations.

### What SELENE cannot/does not do
- No diagnoses (explicitly forbidden).
- No prescriptions or medication recommendations that are beyond general educational statements (code enforces "Never prescribe" in system instructions).
- Not a replacement for emergency services.

### Referral triggers (deterministic rules)
- Examples:
  - Persistent poor sleep (mean < 4/10) + severe hot flashes + severe brain fog → `multiple_severe_symptoms` → increases `risk_score`.
  - Rapid deterioration (drop > 2 points week-over-week) → `rapid_deterioration` flag.
  - Concerning user notes containing "emergency", "unbearable", etc. → `concerning_user_notes`.
- Action mapping:
  - Low: monitoring, continue tracking.
  - Moderate: recommend scheduling evaluation within 1–4 weeks.
  - High: recommend urgent evaluation (within 1 week) or immediate medical attention if emergency sign present.

### Language constraints
- System instruction and agent-level constraints enforce:
  - No prescriptive language (no "You should start [medication]" lines).
  - Use of referral and safety-focused language.
  - Avoid phrases marked as disallowed in the system instruction.

### Risk-tiered response strategy
- Deterministic rules produce a `risk_score` and `flags` (reproducible and auditable).
- Agents combine deterministic outputs with measured LLM interpretation for nuance.
- High-risk outputs are conservative and explicitly recommend clinician evaluation and key data points to bring.

---

## 7. Privacy & Security

### Local-only processing guarantees
- All user data (profile, pulse, chat) and the knowledge base (Chroma collections) are stored locally under `settings.USER_DATA_DIR` by default.
- The LLM interaction is intended to occur to a local Ollama endpoint. `settings.py` sets `TRANSFORMERS_OFFLINE=1`, `HF_DATASETS_OFFLINE=1`, `HF_HUB_OFFLINE=1`, and `CHROMA_TELEMETRY=False`.

### Storage model
- File-based: `user_data/pulse_history.json`, `user_data/user_profile.json`.
- Vector DB: local Chroma persistent store at `user_data/user_med_db`.
- Chat sessions are stored as Chroma documents with metadata (`session_id`, `role`, `timestamp`, `rag_sources`).
- Reports optionally stored under `reports/`.

### Encryption assumptions (explicit)
- **Current codebase does not implement encryption at rest.** Recommendation: apply OS-level full-disk encryption or integrate per-file encryption (e.g., an optional user-provided key).
- Transport: if Ollama or other service is configured to an external endpoint, transport encryption is required (HTTPS). Default is localhost; still, confirm environment isolation.

### Threat model
- Protects against accidental network leakage and default external telemetry:
  - CHROMA_TELEMETRY disabled.
  - HF/transformers offline env flags set.
- Does not protect against:
  - Host compromise (malicious software or root access).
  - Misconfiguration where remote LLM endpoints are permitted (must be audited).
- Recommended hardening for production:
  - Disk encryption, least-privilege OS accounts, model access limited to localhost, audit logs, secure backups.

---

## 8. Code Structure & Conventions

### Directory layout (key files)
- Top-level modules:
  - `app.py` — Streamlit app runner
  - `med_logic.py` — RAG + LLM orchestration & caching
  - `context_builder.py` / `context_builder_multi_agent.py` — build patient context
  - `data_manager.py` — persist pulse entries with validation, backups, and cache invalidation
  - `chat_db.py` — chat persistence + semantic retrieval
  - `deterministic_analysis.py` — math layer, pattern detection, risk rules
  - `insights_generator.py` — deterministic pre-processing + single-LLM report generation
  - `update_kb_chroma.py` — CLI import/export for Chroma
  - `settings.py` — configuration

### Responsibilities of key modules
- `med_logic.py`:
  - Provide caches (`TTLCache`) and cache invalidation hooks.
  - Contextualize queries and perform RAG retrieval.
  - Assemble LLM prompt payload and make calls to local Ollama.
- `deterministic_analysis.py`:
  - Implement reproducible numeric analyses and safety rules.
- `context_builder.py`:
  - Collect and format user profile and pulse data for injection.
- `context_builder_multi_agent.py`:
  - Assemble report context (profile, pulse entries, notes, chat history) and compute completeness scores.
- `chat_db.py`:
  - Persist and retrieve chat messages, enable session management.
- `data_manager.py`:
  - Validate pulse entries, perform atomic writes with backups, and invalidate dependent caches.
- `insights_generator.py`:
  - Validate context completeness, run deterministic analysis, and generate the markdown report plus PDF output via the clinical view.

### State management strategy
- Short-lived caches with TTL (`med_logic.TTLCache`).
- Streamlit UI state is in `st.session_state`.
- Persistent state on disk (JSON) and Chroma for semantic search.

### UI vs logic separation
- UI files (`views/`) call logic functions; domain logic remains in `med_logic`, `deterministic_analysis`, and `insights_generator`.
- Business rules and safety checks are implemented in deterministic modules (not embedded in UI).

### Extensibility considerations
- `update_kb_chroma.py` supports import tools keeping collection IDs intact to avoid stale references.

---

## 9. Deployment & Runtime Considerations

### Supported platforms
- Primary development target: Linux (CI & developer environment).
- Streamlit and Ollama-based stack can run on macOS and Windows, subject to local model support and hardware resources.

### Resource constraints
- LLMs (MedGemma) require significant RAM/VRAM. Ollama hosting may require GPU or optimized CPU inference.
- Sentencetransformer embedding uses CPU if no GPU; embedding large KBs has CPU and memory cost.

### Performance considerations
- Caching:
  - `contextualize_query` (TTL 300s)
  - `rag_cache` (TTL 600s)
  - `user_context_cache` (TTL 180s)
- Deterministic analysis (`deterministic_analysis.py`) is zero-latency (numpy/scipy) and designed to avoid LLM calls where possible.
- Streaming responses reduce apparent latency to users.

### Logging
- Console logging defaults to `DEBUG`; file logging is enabled by default (`LOG_TO_FILE=True`) and writes to `../logs/selene.log` with rotation (10 MB x5).

### Failure modes & graceful degradation
- Ollama down → `med_logic.is_ollama_running()` returns false; user receives an error message, deterministic modules can continue to produce pattern results.
- Chroma DB unavailable or empty → RAG returns empty context; agent responses degrade to deterministic summaries or a helpful message.
- Timeouts in `call_medgemma` are handled and surfaced with explicit error text.
- Insight report generation returns validation errors (insufficient pulse entries or low completeness) without invoking the LLM, preventing stale report reuse.

---

## 10. Testing & Validation

### Unit testing strategy
- Deterministic tests:
  - `deterministic_analysis.analyze_symptom_statistics()` with synthetic pulse entries (edge cases: missing values, short histories).
  - `assess_risk_level()` unit tests to assert flag combinations and thresholds.
- Integration:
  - `med_logic.contextualize_query()` behavior (mock Ollama responses).
  - RAG retrieval (`query_knowledge_base()`) with test Chroma DB snapshots.
- Persistence:
  - `data_manager.save_pulse_entry()` round-trip tests (file IO + cache invalidation).

### Reasoning validation
- Fixed input-output test vectors for `call_medgemma()` where MedGemma returns known outputs (use local stub / mock server).
- Human-in-the-loop evaluation on sample patient profiles to confirm tone and constraint adherence.

### Safety testing
- Automated tests verifying:
  - No prescriptive language appears in LLM outputs for a suite of prompt variations.
  - High-risk triggers generate recommended referral messages.
- Fuzz testing for prompt truncation / huge context inputs.

### UX validation
- Flow-based tests for:
  - Chat contextualization correctness (follow-up rewrite coverage).
  - Attune input validation and persistence.
  - Report generation correctness and PDF formatting.

---

## 11. Future Extensions (non-committal) & Technical Debt

### Planned evolutions (examples)
- Optional per-user encryption at rest (configurable key management).
- Local model quantization and switchable model variants (e.g., MedGemma 1.5 4b → quantized 4b/2b variants).
- Auditable logging framework (secure local logs, optional secure upload for debugging).
- E2E automated tests emulating human interactions.

### Explicitly deferred features
- Federated learning or telemetry-enabled central analytics (deliberately excluded for privacy-first goal).
- Full regulatory compliance / medical device certification (out of scope).

### Known technical debt
- No per-file encryption nor user key management.
- Chroma DB growth strategy not implemented (no sharding/archive of old sessions).
- Some hardcoded timeouts and magic numbers (e.g., `MAX_HISTORY_CHARS = 1200`) documented but may need dynamic tuning.

---

## 12. Assumptions (explicit)
- The host device is trusted and not compromised.
- Ollama and local model files are available locally or via a local host endpoint; the system is not configured to use remote LLM endpoints in the default repo configuration.
- Disk-level encryption and OS security are the recommended mechanism for protecting data at rest unless the operator integrates additional encryption.
- CHROMA_TELEMETRY and offline mode flags (`TRANSFORMERS_OFFLINE`, `HF_DATASETS_OFFLINE`, `HF_HUB_OFFLINE`) set in `settings.py` are respected by installed libraries.

---

## Appendix

### Notable config values (in `settings.py`) 
- `DB_PATH = 'user_data/user_med_db'`
- `LLM_MODEL = 'MedAIBase/MedGemma1.5:4b'`
- `EMBEDDING_MODEL = 'all-MiniLM-L6-v2'`
- `RAG_TOP_K = 2`
- Cache TTLs: contextualized_queries 300s, rag_cache 600s, user_context_cache 180s.

### Example of RAG-context formatting
- Each RAG chunk formatted as:
```
[SOURCE: <file> | SECTION: <section>]
<document text>
```
This is the data fed under `[RESEARCH CONTEXT — CURATED, RECENT]` to the LLM to improve traceability.