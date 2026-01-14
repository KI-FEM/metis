import os
from typing import Any, Optional

from pydantic import BaseModel, Field

from framework.db.db_types import PurposeDB


class AdminRequest(BaseModel):
    """Base model for admin requests."""

    key: str

    def validate_key(self) -> bool:
        """Validate the admin key against the environment variable."""
        return self.key == os.getenv("ADMIN_KEY")


class ConfigureTopicsRequest(AdminRequest):
    """Request model for configuring topics."""

    enabled: dict[str, bool]


class ConfigureTopicsResponse(BaseModel):
    """Response model for configuring topics."""

    success: bool
    error_message: str = ""


class ConfigUpdateRequest(AdminRequest):
    """Request model for updating configuration values."""

    updates: dict[str, Any] = Field(..., description="Config values to update")


class ConfigReadResponse(BaseModel):
    """Response model for reading configuration."""

    success: bool
    error_message: str = ""
    config: Optional[dict[str, Any]] = None
    purposes: Optional[dict[str, PurposeDB]] = None


class RefreshScadsBotsResponse(BaseModel):
    """Response model for refreshing ScaDS bots."""

    success: bool
    error_message: str = ""
    bots_added: list[str] = []
    bots_removed: list[str] = []
    total_bots: int = 0
