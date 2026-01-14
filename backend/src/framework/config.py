# pragma: exclude file

"""Configuration module that provides access to the application settings.

This module loads settings from a JSON file and exposes them as module-level variables.
"""

import os
from pathlib import Path
from typing import Any, Optional

from framework.db.database import Database
from framework.db.db_types import PurposeCompleteDB, PurposeDB

# Path to the configuration file
CONFIG_PATH = Path(__file__).parent / "config.json"

db = Database()


# Function to save configuration
async def save_config(updated_config: dict[str, Any] | None = None):
    """Save configuration to the JSON file."""
    if updated_config:
        environment = get_environment()
        for key, value in updated_config.items():
            await get_db().set_config_value(key, value, environment)


def get_db() -> Database:
    """Get the database instance."""
    return db


def get_environment():
    """Get the current environment setting."""
    environment = os.getenv("LANGFUSE_TRACING_ENVIRONMENT") or "dev"
    if environment not in ["prod", "dev"]:
        environment = "dev"
    return environment


# Function to get a configuration value
async def get_config(key=None):
    """Get configuration value or the entire configuration if key is None."""
    environment = get_environment()
    if key:
        return await get_db().get_config_value(key, environment)
    return await get_db().get_all_config_values(environment)

async def get_purpose(purpose_code: Optional[str]) -> PurposeDB | None:
    """Get AI models for a specific purpose from the configuration."""
    purpose = await get_db().get_purpose(purpose_code)
    return purpose

async def get_all_purposes() -> list[PurposeDB]:
    """Get all purposes from the configuration."""
    return await get_db().get_all_purposes()

async def get_all_purposes_with_translation() -> list[PurposeCompleteDB]:
    """Get all purposes with translations from the configuration."""
    return await get_db().get_all_purposes_complete()

async def save_purpose(purpose: PurposeDB):
    """Save a purpose to the configuration."""
    await get_db().update_purpose(purpose)
