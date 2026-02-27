import logging
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableSerializable,
)
from langfuse.callback import CallbackHandler

sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger()
secret = os.getenv("LANGFUSE_SECRET")
if secret is None:
    load_dotenv()

class BaseChain(ABC):
    """Base class for all chains.

    This class provides the base interface for all chain implementations.

    Args:
        None

    Returns:
        None

    """

    chain: RunnableSerializable

    def __init__(self) -> None:
        """Initialize the chain."""
        self.chain = None

    def get_chain(self) -> RunnableSerializable:
        """Get the LangChain chain object."""
        return self.chain

    @abstractmethod
    def create_chain(
        self,
        llm: Runnable,
        prompt: PromptTemplate,
        session_id: str = None,
    ) -> RunnableSerializable:
        """Create the chain."""

    @staticmethod
    def get_langfuse_callback(
        session_id: str,
        tags: list[str] = None
    ) -> CallbackHandler:
        """Create a Langfuse callback handler for creating traces."""
        return CallbackHandler(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST"),
            environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT"),
            session_id=session_id,
            tags=tags,
            enabled=os.getenv("LANGFUSE_TRACING_ENABLED", "true") == "true",
        )
