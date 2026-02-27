"""Configuration module that provides access to the application settings.

This module loads settings from a JSON file and exposes them as module-level variables.
"""
import json
from pathlib import Path

# Path to the configuration file
CONFIG_PATH = Path(__file__).parent / "config.json"

# Load configuration from JSON file
def _load_config():
    """Load configuration from the JSON file."""
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in configuration file: {CONFIG_PATH}")

# Initialize with default values
_config = _load_config()

# Function to reload configuration
def reload_config():
    """Reload configuration from the JSON file."""
    global _config
    _config = _load_config()
    
    # Dynamically update module-level variables to maintain compatibility
    # with code that uses direct imports
    global MAX_MESSAGES_BEFORE_SUMMARIZATION, KEEP_LAST_MESSAGES_UNTIL
    global MULTI_QUERY_RETRIEVER
    global MODELS_REFRESH_THRESHOLD, AI_MODELS

    MAX_MESSAGES_BEFORE_SUMMARIZATION = _config.get("MAX_MESSAGES_BEFORE_SUMMARIZATION",
                                                    64)
    KEEP_LAST_MESSAGES_UNTIL = _config.get("KEEP_LAST_MESSAGES_UNTIL", 16)
    MULTI_QUERY_RETRIEVER = _config.get("MULTI_QUERY_RETRIEVER", True)
    MODELS_REFRESH_THRESHOLD = _config.get("MODELS_REFRESH_THRESHOLD", 86400)
    AI_MODELS = _config.get("AI_MODELS", [])

# Function to save configuration
def save_config(updated_config=None):
    """Save configuration to the JSON file."""
    if updated_config:
        global _config
        _config.update(updated_config)
    
    with CONFIG_PATH.open("w") as f:
        json.dump(_config, f, indent=2)
    
    # Reload to ensure consistency
    reload_config()

# Function to get a configuration value
def get_config(key=None):
    """Get configuration value or the entire configuration if key is None."""
    if key is None:
        return _config
    return _config.get(key)

# Expose configuration values as module-level variables for backward compatibility
MAX_MESSAGES_BEFORE_SUMMARIZATION = _config.get("MAX_MESSAGES_BEFORE_SUMMARIZATION", 64)
KEEP_LAST_MESSAGES_UNTIL = _config.get("KEEP_LAST_MESSAGES_UNTIL", 16)
MULTI_QUERY_RETRIEVER = _config.get("MULTI_QUERY_RETRIEVER", True)
MODELS_REFRESH_THRESHOLD = _config.get("MODELS_REFRESH_THRESHOLD", 86400)
AI_MODELS = _config.get("AI_MODELS", [])
