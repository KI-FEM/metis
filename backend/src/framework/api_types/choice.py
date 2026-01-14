import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.api_types.request_format import LearnerModel, MessageType
from framework.api_types.response_format import Button, Source


class ChoiceDelta(BaseModel):
    """Represents a delta (change) in a chat completion choice.

    This class is used to represent incremental updates to a chat completion,
    such as new content, sender, sources, or model information.

    Args:
        content (Optional[str]): The content of the message.
        type (Optional[str]): The sender of the message.
        sources (Optional[list]): List of sources for the message.
        llm_model (Optional[str]): The name of the LLM model used.
        thoughts (Optional[str]): Optional thoughts or reasoning.
        instructions (Optional[list[str]]): Optional instructions for the frontend.
        trace_id (Optional[str]): Optional trace ID for tracking.

    Returns:
        None

    """

    content: Optional[str] = None
    storage: Optional[dict[str, Union[str, int, float, list, LearnerModel]]] = None
    instructions: Optional[list[str]] = None
    type: Optional[MessageType] = None
    thoughts: Optional[str] = None
    buttons: Optional[list[Button]] = None
    sources: Optional[dict[int, Source]] = None
    llm_model: Optional[str] = None
    citations: Optional[list[int]] = None
    trace_id: Optional[str] = None


class Choice(BaseModel):
    """Represents a single choice in a chat completion.

    This class is used to encapsulate a single choice, including the delta,
    finish reason, and any additional metadata.

    Args:
        delta (Optional[ChoiceDelta]): The delta for this choice.
        finish_reason (Optional[str]): The reason the choice was finished.

    Returns:
        None

    """

    delta: ChoiceDelta
    finish_reason: str


class ChatCompletionsChunk(BaseModel):
    """Represents a chunk of chat completions.

    This class is used to represent a chunk of chat completions, including the
    ID, choices, and creation timestamp.

    Args:
        id (str): The unique identifier for the chunk.
        choices (list[Choice]): The list of choices in the chunk.
        created (str): The creation timestamp.

    Returns:
        None

    """

    id: str
    choices: list[Choice]
    created: str

    @staticmethod
    def from_message(message: str) -> "ChatCompletionsChunk":
        """Creates a ChatCompletionsChunk from a message string.

        Args:
            message (str): The message content.

        Returns:
            ChatCompletionsChunk: The created ChatCompletionsChunk instance.

        """
        delta = ChoiceDelta(content=message)
        choice = Choice(delta=delta, finish_reason="")
        return ChatCompletionsChunk(
            id="", choices=[choice], created=datetime.now().isoformat()
        )


class MessageEvent(BaseModel):
    """Represents an event related to a chat message."""

    timestamp: str
    event: str  # e.g., "think"
    additional_info: Optional[dict] = None
