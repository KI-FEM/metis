from typing import Union

from langchain_core.documents import Document
from pydantic import BaseModel, Extra

from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import (
    LearnerModel,
    MessageType,
)


class ErrorReport(BaseModel):
    """Represents an error report for a chat session.

    This class is used to report errors encountered during the chat session,
    including the error message and any additional context.

    Args:
        error (str): The error message.
        context (Optional[dict]): Additional context or data related to the error.

    Returns:
        None

    """

    error: str
    context: dict = {}


class BaseResponseModel(BaseModel):
    """Base model for responses."""

    error: ErrorReport | None = None


class TitleResponse(BaseResponseModel):
    """Represents a title response for a chat session.

    This class is used to return a generated title for the chat session.

    Args:
        title (str): The generated title.

    Returns:
        None

    """

    title: str
    
class CommentResponse(BaseResponseModel):
    """Represents a response for a message comment.

    Args:
        success (bool): Indicates if the comment was successfully generated.

    Returns:
        None

    """

    success: bool
    
class MessageVoteResponse(BaseResponseModel):
    """Represents a response for a message vote.

    This class is used to indicate whether the vote operation was successful.

    Args:
        success (bool): Indicates if the vote was successfully recorded.

    Returns:
        None

    """

    success: bool


class ButtonCallback(BaseModel):
    """Represents a callback for a button.

    This class defines the callback endpoint and data to be sent when a button
    is pressed in the chat UI.

    Args:
        endpoint (str): The endpoint to call.
        data (dict): The data to send to the endpoint.

    Returns:
        None

    """

    endpoint: str
    data: dict[str, str]


class Button(BaseModel):
    """Represents a button in the chat UI.

    This class is used to define a button that can be displayed in the chat
    interface, including its label, callback, and optional chat message or state
    store.

    Args:
        label (str): The text displayed on the button.
        callback (ButtonCallback): The callback to be triggered when the button
            is pressed.
        chat_message (Optional[str]): The message to send when the button is pressed.
        store (Optional[dict]): State to store when the button is pressed.

    Returns:
        None

    """

    chat_message: str
    label: str
    callback: ButtonCallback
    store: dict[str, Union[str, int, float, list, LearnerModel]] = {}


class Source(BaseModel):
    """Represents a source document for a message.

    This class is used to provide information about the source used for a message,
    such as a document or reference.

    Args:
        title (str): The title of the source.
        url (Optional[str]): The URL of the source.
        content (Optional[str]): The content of the source.

    Returns:
        None

    """

    title: str
    chunk: str
    thumbnail: str | None = None  # Base64 encoded image string
    year: int | None = None
    authors: list[str] = []
    original_language: LocaleType | None = None
    additional_metadata: dict = {}

    @staticmethod
    def from_document(
        doc: Document, meta2label: callable = None, meta2meta: callable = None
    ) -> "Source":
        """Create a Source from a Document."""
        label = (
            meta2label(doc.metadata)
            if callable(meta2label)
            else (doc.metadata["Header 1"] if "Header 1" in doc.metadata else doc.id)
        )
        return Source(
            title=label,
            chunk=doc.page_content,
            additional_metadata=meta2meta(doc.metadata)
            if callable(meta2meta)
            else doc.metadata,
        )


class MetaInformation(BaseModel, extra=Extra.allow):
    """Contains meta information for a message.

    This class holds metadata such as sources and the LLM model used for
    generating the message.

    Args:
        sources (Optional[dict[int, Source]]): The sources for the message identified by
            an integer id.
        llm_model (Optional[str]): The name of the LLM model used.

    Returns:
        None

    """

    sources: dict[int, Source] = None
    citations: list[int] = None
    llm_model: str = None


class MessageResponse(BaseModel):
    """Represents a message response from the bot.

    This class is used to encapsulate a message sent by the bot, including the
    message content, sender, optional buttons, and meta information.

    Args:
        content (str): The message content.
        type (Optional[str]): The sender of the message.
        buttons (Optional[list[Button]]): List of buttons to display.
        meta_information (Optional[MetaInformation]): Additional metadata for
            the message.
        thoughts (Optional[str]): Optional thoughts or reasoning.

    Returns:
        None

    """

    content: str
    type: MessageType = MessageType.ASSISTANT
    thoughts: str | None = None
    buttons: list[Button] = []
    meta_information: MetaInformation = MetaInformation()


class Response(BaseResponseModel):
    """Represents a response from the bot.

    This class encapsulates a list of message responses to be sent to the frontend.

    Args:
        messages (list[MessageResponse]): The list of message responses.
        storage (Optional[dict[str, str]]): Key-value store for session-specific data.
        instructions (Optional[list[str]]): Optional instructions for the frontend.

    Returns:
        None

    """

    messages: list[MessageResponse]
    storage: dict[str, Union[str, int, float, list, LearnerModel]] = {}
    instructions: list[str] = []

    @staticmethod
    def from_message(message: str, **data) -> "Response":
        """Initialize the Response with a single message."""
        return Response(messages=[MessageResponse(content=message)], **data)


class SummaryResponse(BaseResponseModel):
    """Represents a summary response for a chat session.

    This class is used to return a summary of the chat and the number of
    messages to keep after summarization.

    Args:
        summary (str): The summary text.
        keep_last_messages_until (int): Number of messages to keep after summarization.

    Returns:
        None

    """

    summary: str
    keep_last_messages_until: int
