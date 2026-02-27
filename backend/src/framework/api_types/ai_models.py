from enum import Enum
from typing import Optional

from pydantic import BaseModel

from framework.api_types.locale_type import LocaleType


class LLMPurpose(Enum):
    """Purpose of the LLM."""

    OPTIMAL = "optimal"
    REASONING = "reasoning"
    GERMAN = "german"
    GEMINI = "gemini"


class ChatConfig(BaseModel):
    """Configuration from the backend for the chat in the frontend.
    
    Args:
        max_messages_before_summarization (int): The maximum number of messages before
            summarization is triggered.

    """

    max_messages_before_summarization: int


class PurposeModel(BaseModel):
    """The selection a user can take to change the model that is used.
    
    Abstracts the difficult LLM names behind a user-friendly label. We decide for the 
    user which LLM is used for which purpose.
    """

    id: LLMPurpose
    label: dict[LocaleType, str]
    description: dict[LocaleType, str]
    icon: str
    healthy: bool


class AIModelsResponse(BaseModel):
    """Response model for models with status."""

    purposes: list[PurposeModel]
    timestamp: float
    config: ChatConfig
    error: Optional[str] = None


class PurposeConfigModel(BaseModel):
    """Model under which LLMs are saved in the config file."""

    id: str
    label: dict[LocaleType, str]
    description: dict[LocaleType, str]
    icon: str
    models: list[str]

class PurposeListConfigModel(BaseModel):
    """Model for the list of purposes in the config file."""

    purposes: list[PurposeConfigModel]

class LLMStatus(str, Enum):
    """Status of the LLM."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class LLM(BaseModel):
    """Represents a language model (LLM) configuration.

    This class is used to represent a language model in the code.

    Args:
        id (str): The unique identifier for the LLM in LiteLLM.
        model_name (str): The base name of the LLM.
        label (str): The label of the LLM for endusers.
        api_base_url (str): The base URL for the LLM API.
        status (LLMStatus): The status of the LLM ('healthy' / 'unhealthy').

    Returns:
        None

    """

    id: str
    model_name: str
    label: str
    api_base_url: Optional[str] = None
    status: LLMStatus


class CachedAIModels(BaseModel):
    """List of AI models with a timestamp for caching, retrieving and updating."""

    models: list[LLM]
    timestamp: float

class CachedPurposes(BaseModel):
    """List of purposes with a timestamp for caching, retrieving and updating."""

    purposes: list[PurposeModel]
    timestamp: float
