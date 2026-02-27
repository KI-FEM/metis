"""A module containing classes for language model generation."""

from .base_llm import BaseLLM
from .scads_llm import ScadsLLM

__all__ = ("ScadsLLM", "BaseLLM")

# Re-export classes so that they appear to be defined in this module.
for key, value in list(locals().items()):
    if getattr(value, "__module__", "").startswith("llm"):
        value.__module__ = __name__
