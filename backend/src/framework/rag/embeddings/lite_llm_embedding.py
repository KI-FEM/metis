
import os

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

from framework.rag.embeddings.base_embedding import BaseEmbedding


class LiteLLMEmbedding(BaseEmbedding):
    """Class to wrap the LiteLLM client for embeddings."""
    
    def __init__(
        self, 
        model_name: str = "qwen-3-embedding-4b", 
    ) -> None:
        """Initialize the LiteLLM Embedding."""
        self.proxy_url = os.getenv("LITELLM_URL")

        if self.proxy_url is None:
            load_dotenv()
            self.proxy_url = os.getenv("LITELLM_URL")

        self.key = os.getenv("LITELLM_KEY")
        if self.proxy_url is None:
            raise ValueError(
                "LITELLM_URL environment variable not found. If not already done, "
                "copy the .env.example file, rename to '.env' and set the URL."
            )

        self.embeddings = OpenAIEmbeddings(
            model=model_name, 
            api_key=self.key, 
            base_url=self.proxy_url,
        )
