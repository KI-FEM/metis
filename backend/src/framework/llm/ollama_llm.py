import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.llm.base_llm import BaseLLM


class OllamaLLM(BaseLLM):
    """A class to interact with the Ollama LLM API."""

    def __init__(self, model_name=None, proxy_url=None) -> None:
        """Initialize the OllamaLLM object."""
        super().__init__()
        if not model_name:
            raise ValueError(
                "Model name must be provided. If not already done, "
                "copy the .env.example file, rename to '.env' and set the model name."
            )
        self.model_name = model_name
        if not proxy_url:
            load_dotenv()
            proxy_url = os.getenv("OLLAMA_URL")
        self.proxy_url = proxy_url

    def get_model_name(self):
        """Get the name of the LLM model."""
        return self.model_name

    def llm(self, temperature=0.7, max_tokens=None, chat_id=None):
        """Create a LangChain Runnable for the Ollama LLM API.

        The Runnable can be used to call the Ollama LLM API and generate a LLM response.
        """
        metadata = {
            # "generation_name"
            # "generation_id"
        }

        if self.proxy_url is None:
            raise ValueError(
                "OLLAMA_URL environment variable not found. If not already done, "
                "copy the .env.example file, rename to '.env' and set the URL."
            )

        return ChatOllama(
            model=self.model_name,
            temperature=temperature,
            base_url=self.proxy_url,
            metadata=metadata,
        )
