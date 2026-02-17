# SELENE Test Suite

Unit tests for the core deterministic and caching layers of SELENE.

## Running Tests

```bash
python3 -m pytest tests/ -v
```

## Test Files

### `test_deterministic_analysis.py` — 27 tests

Covers `deterministic_analysis.py`: the zero-latency statistical engine.

| Area | What's tested |
|---|---|
| **Symptom Mapping** | Known labels → numeric scores, numeric pass-through, numeric strings, `None`, unknown strings, unsupported types |
| **Symptom Statistics** | Insufficient data guard, stable/worsening/improving trend detection, percent-change calculation, missing key handling |
| **Pattern Detection** | Empty-data fallback, stable-data (no cycles), correlation computation, `PatternAnalysis` field types |
| **Cycle Detection** | Constant data (no cycle), insufficient length, strong weekly sinusoidal signal |
| **Risk Assessment** | Insufficient data, low risk, persistent poor sleep, severe hot flashes, multiple severe symptoms, concerning notes keyword scan, rapid deterioration, composite high-risk scoring |
| **Formatting Helpers** | `format_statistics_summary` content, `format_pattern_summary` with/without cycles & outliers |

### `test_context_builder.py` — 19 tests

Covers `context_builder.py` and `context_builder_multi_agent.py`: user-context aggregation for the LLM prompt.

| Area | What's tested |
|---|---|
| **Profile Hash** | Empty files → deterministic empty hash, hash includes profile fields, hash changes on profile update |
| **Profile Context** | Returns empty when no profile, formats stage + neuro symptoms from session state |
| **Pulse Context** | Empty history, sleep-issue counting, hot-flash counting, day-window filtering |
| **Pattern Analysis** | Empty history returns `{}`, sleep-disruption trend detection, `format_pulse_analysis_for_llm` output |
| **build_user_context** | Returns empty when all sections disabled, combines profile + pulse sections |
| **Multi-Agent Profile** | Defaults when file missing, loads existing profile, handles corrupt JSON |
| **Multi-Agent Notes** | Missing file, valid notes loading, date-range filtering |
| **Completeness Score** | Zero when empty, full score (1.0), partial score calculation |
| **Context Summary** | Formatted summary contains date range, entry counts, completeness percentage |

### `test_med_logic_cache.py` — 34 tests

Covers the caching infrastructure in `med_logic.py`.

| Area | What's tested |
|---|---|
| **CacheEntry** | Not expired within TTL, expired after TTL, zero-TTL expiry, value storage |
| **TTLCache Basics** | Miss returns `None`, set/get round-trip, key overwrite, expired entry returns `None`, clear |
| **TTLCache Eviction** | Oldest entry evicted when full, size respects `max_size` limit |
| **TTLCache Stats** | Hit/miss counters, stats reset after clear, expired entry counted as miss |
| **generate_cache_key** | Deterministic output, different args → different keys, prefix inclusion, no-prefix mode, SHA-256 hex length |
| **get_user_context_hash** | Delegates to profile hash, falls back on `ImportError` |
| **Cache Management** | `clear_all_caches`, `invalidate_user_context_cache` (leaves RAG untouched), `invalidate_rag_cache` (leaves user context untouched), `get_cache_stats` structure |
| **Thread Safety** | Concurrent writers + readers produce no exceptions |
