import sys
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.api_types.ai_models import LLM, LLMPurpose

from .learning_type import (
    AvailableLearningTypes,
    LearningTypeModel,
    LearningTypes,
)
from .locale_type import LocaleType


class Sender(Enum):
    """The sender of a message."""

    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class Message(BaseModel):
    """Represents a single chat message.

    This model is used to encapsulate a message exchanged in the chat, including
    the sender, content, and optional metadata.

    Args:
        message (str): The content of the message.
        sender (str): The sender of the message (e.g., 'user', 'assistant').
        summary (Optional[str]): Optional summary of the message.

    Returns:
        None

    """

    message: str
    sender: Sender


class Summary(Message):
    """The format of a summary message."""

    summary: str


class RequestModel(BaseModel):
    """Request model for chat and bot endpoints.

    This model contains all information sent from the frontend to the backend,
    including chat history, user data, and session state.

    Args:
        learning_type_id (AvailableLearningTypes): The ID of the learning type.
        chat_history (list[Message]): The list of previous messages in the conversation.
        language (str): The language code for localization.
        storage (dict): Key-value store for session-specific data.
        streaming (bool): Whether the response should be streamed.
        llm (Optional[LLM]): The requested language model.
        llm_purpose (Optional[str]): Purpose for which the LLM should be auto-selected.

    Returns:
        None

    """

    learning_type_id: AvailableLearningTypes
    language: str
    chat_history: list[Union[Message, Summary]]
    storage: dict[str, str] = {}
    llm: Optional[LLM] = None
    llm_purpose: Optional[LLMPurpose] = Field(
        None,
        description="The purpose of the LLM to use (e.g., 'optimal' or 'reasoning')",
    )
    streaming: bool = False

    def learning_type(self) -> LearningTypeModel:
        """Get the learning type for the request.

        Returns the learning type model based on the session store or defaults.

        Args:
            None

        Returns:
            LearningTypeModel: The learning type model.

        """
        return LearningTypes[self.learning_type_id.value].value

    def locale(self) -> LocaleType:
        """Get the locale for the request.

        Returns the locale type based on the language code provided in the request.

        Args:
            None

        Returns:
            LocaleType: The locale type for the request.

        """
        return LocaleType[self.language.upper()]

    def find_store(self, key: str, default=None) -> Union[str, None]:
        """Find the value of a store by key."""
        if key in self.storage:
            return self.storage[key]
        return default
