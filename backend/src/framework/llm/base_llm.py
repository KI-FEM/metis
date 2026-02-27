from abc import ABC, abstractmethod

from langchain_core.runnables import Runnable


class BaseLLM(ABC):
    """An abstract class representing an LLM."""

    def __init__(self) -> None:
        """Initialize the LLM."""

    @abstractmethod
    def llm(self) -> Runnable:
        """Abstract method returning a LangChain runnable of the implementing LLM."""
        raise NotImplementedError(
            "Do not use BaseLLM. Instead, subclasses should implement this method"
        )
    
    def get_model_name(self) -> str:
        """Return the model name of the LLM."""
        return self.__class__.__name__
