import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

sys.path.append(str(Path(__file__).parent.parent))
from llm.base_llm import BaseLLM


class ScadsLLM(BaseLLM):
    """A class representing a ScaDS LLM.
    
    Requires the SCADS_API_KEY environment variable to be set.

    Args:
    ----
    model_name (str): The name of the ScaDS LLM model to use. Defaults to "meta-llama\
      /Meta-Llama-3.1-70B-Instruct".
    base_url (str): The base URL of the ScaDS LLM API. Defaults to "https://llm.scads.ai/v1".
    
    """

    def __init__(
        self,
        model_name="meta-llama/Llama-3.3-70B-Instruct",
        base_url="https://llm.scads.ai/v1",
    ) -> None:
        """Initialize the ScaDS LLM."""
        super().__init__()
        self.key = os.getenv("SCADS_API_KEY")

        if self.key is None:
            load_dotenv()
            self.key = os.getenv("SCADS_API_KEY")

        if self.key is None:
            raise ValueError(
                "SCADS_API_KEY environment variable not found. If not already done, "
                "copy the .env.example file, rename to '.env' and set the API key."
            )

        self.model_name = model_name
        self.base_url = base_url

    def set_model_name(self, new_model_name: str) -> None:
        """Set the name of the LLM model, available on the ScaDS server."""
        self.model_name = new_model_name

    def llm(self) -> ChatOpenAI:
        """Create a LangChain OpenAI runnable for the ScaDS API."""
        return ChatOpenAI(
            model=self.model_name,
            base_url=self.base_url,
            api_key=self.key,
            temperature=0.7,
            max_tokens=2048,
            verbose=True,
            streaming=True,
        )
