import sys
from pathlib import Path

from langchain_core.runnables import Runnable

sys.path.append(str(Path(__file__).parent.parent))
from llm.base_llm import BaseLLM

from framework.api_types.locale_type import LocaleType


class MultiLingualLLM:
    """Multi-lingual LLM client manager.

    This class manages multiple language model clients for different locales,
    allowing selection and retrieval of the appropriate LLM for a given locale.

    Args:
        None

    Returns:
        None

    """

    def __init__(
        self, default_locale: LocaleType = LocaleType.EN
    ) -> None:
        """Initialize the multilingual LLM."""
        self.llms = {}
        self.default_locale = default_locale

    def add_llm(self, locale: LocaleType, llm: BaseLLM) -> None:
        """Add an LLM for a specific locale."""
        self.llms[locale] = llm

    def remove_llm(self, locale: LocaleType) -> None:
        """Remove an LLM for a specific locale."""
        del self.llms[locale]

    def get_llm(self, locale: LocaleType) -> BaseLLM:
        """Get the LLM for a specific locale."""
        return self.llms.get(locale)

    def llm(self) -> Runnable:
        """Return a LangChain runnable of the implementing LLM."""
        return self.get_llm(self.default_locale).llm()
