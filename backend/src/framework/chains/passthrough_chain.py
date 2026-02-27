import sys
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnableSerializable,
)

sys.path.append(str(Path(__file__).parent.parent))
from .base_chain import BaseChain


class PassthroughChain(BaseChain):
    """A chain that passes input directly to the LLM.

    This chain simply forwards the input prompt to the language model and returns
    the result, without any retrieval or augmentation.
    """

    def create_chain(
        self,
        llm: Runnable,
        prompt: PromptTemplate,
        session_id: str = None,
        tags: list[str] = None,
    ) -> RunnableSerializable:
        """Create a simple chain that passes input directly to the LLM."""
        self.chain = prompt | llm | StrOutputParser()
        return self.get_chain().with_config(
            callbacks=[BaseChain.get_langfuse_callback(session_id, tags)]
        )
