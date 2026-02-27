from typing import Optional

from langchain_core.documents import Document
from pydantic import BaseModel

from framework.api_types.request_format import Sender


class TitleResponse(BaseModel):
    """Represents a title response for a chat session.

    This class is used to return a generated title for the chat session.

    Args:
        title (str): The generated title.

    Returns:
        None

    """

    title: str


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
    store: dict[str, str] = {}


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

    label: str
    chunk: str
    url: str
    additional_metadata: dict = {}
    
    @staticmethod
    def from_document(
        doc: Document, 
        url_to_label: callable = None, 
        url_to_metadata: callable = None
    ) -> "Source":
        """Create a Source from a Document."""
        label = url_to_label(doc.metadata['source']) if callable(url_to_label) else (
            doc.metadata['Header 1'] if 'Header 1' in doc.metadata 
            else doc.metadata['source'])
        return Source(
            label=label, 
            chunk=doc.page_content,
            url=doc.metadata['source'],
            additional_metadata=url_to_metadata(doc.metadata['source']) 
                if callable(url_to_metadata) else {},
        )


class MetaInformation(BaseModel):
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
        message (str): The message content.
        sender (Optional[str]): The sender of the message.
        buttons (Optional[list[Button]]): List of buttons to display.
        meta_information (Optional[MetaInformation]): Additional metadata for
            the message.
        thoughts (Optional[str]): Optional thoughts or reasoning.

    Returns:
        None

    """

    message: str
    sender: Sender = Sender.ASSISTANT
    thoughts: Optional[str] = None
    buttons: list[Button] = []
    meta_information: MetaInformation = MetaInformation()


class Response(BaseModel):
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
    storage: dict[str, str] = {}
    instructions: list[str] = []
    
    @staticmethod
    def from_message(message: str, **data) -> "Response":
        """Initialize the Response with a single message."""
        return Response(messages=[MessageResponse(message=message)], **data)
        

class SummaryResponse(BaseModel):
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
