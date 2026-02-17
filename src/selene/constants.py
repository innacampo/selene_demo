"""
Shared Domain Constants for SELENE.

Centralizes mappings and lookup tables used across multiple modules
(deterministic_analysis, context_builder_multi_agent, etc.) to avoid
duplicated definitions drifting out of sync.
"""

# Standardized symptom label → numeric score mapping.
# Used by: deterministic_analysis.py, context_builder_multi_agent.py
SYMPTOM_SEVERITY_MAP = {
    # 0 = No symptoms, 10 = Maximum disruption
    "Restorative": 0,
    "Fragmented": 5,
    "3 AM Awakening": 9,
    
    "Cool": 0,
    "Warm": 4,
    "Flashing": 7,
    "Heavy": 10,
    
    "Focused": 0,
    "Neutral": 4,
    "Brain Fog": 9,
}

# Valid string labels for each pulse pillar (used by data_manager validation).
VALID_REST_VALUES = {"3 AM Awakening", "Fragmented", "Restorative"}
VALID_CLIMATE_VALUES = {"Cool", "Warm", "Flashing", "Heavy"}
VALID_CLARITY_VALUES = {"Brain Fog", "Neutral", "Focused"}

# Concise neuro-symptom labels for LLM context injection.
# Single source of truth — imported by context_builder.py
NEURO_SYMPTOM_MAP = {
    "3am_wakeup": "The 3 AM Wakeup (nighttime waking with anxiety)",
    "word_search": "The Word Search (difficulty finding words)",
    "short_fuse": "The Short Fuse (chemical irritability, not situational)",
}

# Extended descriptions displayed in the onboarding UI.
# Single source of truth — imported by onboarding.py
NEURO_SYMPTOM_DESCRIPTIONS = {
    "3am_wakeup": "The 3 AM Wakeup: Feeling wide awake and anxious in the middle of the night.",
    "word_search": "The Word Search: Difficulty finding common words or losing your train of thought.",
    "short_fuse": "The Short Fuse: A new, intense irritability that feels chemical rather than situational.",
}