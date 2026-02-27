import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

sys.path.append(str(Path(__file__).parent.parent))
from llm.base_llm import BaseLLM


class KisskiLLM(BaseLLM):
    """A class representing an LLM hosted on Uni Göttingen's KISSKI server.
    
    Requires the KISSKI_API_KEY environment variable to be set.

    Currently available models (09-2024):
    - meta-llama-3.1-8b-instruct
    - meta-llama-3.1-70b-instruct
    - mixtral-8x7b-instruct
    - qwen2-72b-instruct 

    Args:
    ----
    model_name (str): The name of the KISSKI LLM model to use. Defaults to "meta-llama-\
      3.1-70b-instruct".
    base_url (str): The base URL of the KISSKI LLM API. Defaults to "https://chat-ai.academiccloud.de/v1".
    
    """

    def __init__(
        self,
        model_name="llama-3.3-70b-instruct",
        base_url="https://chat-ai.academiccloud.de/v1",
    ) -> None:  
        """Initialize the KISSKI LLM."""
        super().__init__()
        self.key = os.getenv("KISSKI_API_KEY")

        if self.key is None:
            load_dotenv()
            self.key = os.getenv("KISSKI_API_KEY")

        if self.key is None:
            raise ValueError(
                "KISSKI_API_KEY environment variable not found. If not already done, "
                "copy the .env.example file, rename to '.env' and set the API key."
            )

        self.model_name = model_name
        self.base_url = base_url

    def set_model_name(self, new_model_name: str) -> None:
        """Set the name of the LLM model, available on the KISSKI server."""
        self.model_name = new_model_name

    def llm(self, temperature=0.7, max_tokens=2048) -> ChatOpenAI:
        """Create a LangChain OpenAI runnable for the KISSKI API."""
        return ChatOpenAI(
            model=self.model_name,
            base_url=self.base_url,
            api_key=self.key,
            temperature=temperature,
            max_tokens=max_tokens,
            verbose=True,
            streaming=True,
        )
