"""Custom output parsers for langchain."""
from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.output_parsers.transform import BaseCumulativeTransformOutputParser
from langchain_core.outputs import Generation


class DictOutputParser(BaseCumulativeTransformOutputParser[Dict[str, Any]]):
    """OutputParser that parses LLMResult into a dictionary.
    
    Preserves text and additional_kwargs from the LLM output.
    """

    def __init__(self):
        """Initialize the DictOutputParser."""
        super().__init__()
        self.diff = False  # Disable diff mode to get full content

    @classmethod
    def is_lc_serializable(cls) -> bool:
        """DictOutputParser is serializable."""
        return True

    @classmethod
    def get_lc_namespace(cls) -> list[str]:
        """Get the namespace of the langchain object."""
        return ["langchain", "schema", "output_parser"]

    def parse_result(
        self, result: List[Generation], *, partial: bool = False
    ) -> Dict[str, Any]:
        """Parse a list of candidate model Generations into a dictionary.

        Args:
            result: A list of Generations to be parsed.
            partial: Whether to parse the output as a partial result.

        Returns:
            A dictionary containing the text and additional_kwargs.

        """
        if not result:
            return {"answer": "", "additional_kwargs": {}}

        first_result = result[0]
        message = getattr(first_result, "message", None)
        return {
            "answer": first_result.text or "",
            "additional_kwargs": message.additional_kwargs if message else {},
        }

    def parse(self, text: str) -> Dict[str, Any]:
        """Parses the input text into a dictionary.

        Args:
            text: The input text.

        Returns:
            A dictionary containing the text.

        """
        return {"answer": text, "additional_kwargs": {}}

    @property
    def _type(self) -> str:
        """Return the output parser type for serialization."""
        return "json_output_parser"
