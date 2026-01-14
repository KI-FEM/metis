import sys
from pathlib import Path

from deepeval.models.base_model import DeepEvalBaseLLM
from pydantic import BaseModel

sys.path.append(str(Path(Path(__file__).parent.parent.parent)))
from framework.chains.base_chain import BaseChain
from framework.llm.lite_llm import LiteLLM


class DeepEvalLiteLLM(DeepEvalBaseLLM):
    """DeepEvalLiteLLM is a wrapper for the LiteLLM class."""

    def __init__(self, model_name=None, temperature=0.7) -> None:
        """Initialize the DeepEvalLiteLLM class."""
        self.client = LiteLLM(model_name=model_name)
        self.model = LiteLLM(model_name=model_name).llm_chatopenai(
            temperature=temperature
        )
        self.temperature = temperature

    def load_model(self):
        """Load the LiteLLM model."""
        return self.model

    def generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        """Generate a response using the LiteLLM model."""
        callback = BaseChain.get_langfuse_callback()
        response = (
            self.client.llm_chatopenai(
                temperature=self.temperature,
            )
            .with_structured_output(schema)
            .with_config(
                callbacks=[callback],
                metadata={
                    "langfuse_session_id": "deepeval_lite_llm",
                    "langfuse_tags": ["deepeval_lite_llm"],
                }
            )
            .invoke(prompt)
        )

        return response

    async def a_generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        """Asynchronous generate method."""
        callback = BaseChain.get_langfuse_callback()
        response = (
            await self.client.llm_chatopenai(
                temperature=self.temperature,
            )
            .with_structured_output(schema)
            .with_config(
                callbacks=[callback],
                metadata={
                    "langfuse_session_id": "deepeval_lite_llm",
                    "langfuse_tags": ["deepeval_lite_llm"],
                }
            )
            .ainvoke(prompt)
        )

        return response

    def get_model_name(self):
        """Get the model name."""
        return self.client.get_model_name()
