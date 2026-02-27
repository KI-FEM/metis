import sys
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    Runnable,
    RunnablePassthrough,
    RunnableSerializable,
)

sys.path.append(str(Path(__file__).parent.parent))
from .base_chain import BaseChain


class RetrievalChain(BaseChain):
    """A chain that retrieves information from a vector database."""

    def create_chain(
        self,
        llm: Runnable,
        prompt: PromptTemplate,
        session_id: str = None,
        tags: list[str] = None,
    ) -> RunnableSerializable:
        """Create and save a chain to do RAG using the given LLM, VectorDB and prompt.

        Args:
            llm (Runnable): The language model as a LangChain Runnable to use.
            prompt (PromptTemplate): The prompt template as LangChain PromptTemplate.
            session_id (str): The session ID to use for tracing.
            tags (list[str]): The tags to use for tracing.

        Returns:
            RunnableSerializable: The LangChain chain object.

        """

        def format_docs(docs):
            """Simple method converting documents to a string separated by newlines."""
            return "\n\n".join(doc.page_content for doc in docs)

        rag_chain = (
            RunnablePassthrough.assign(context=lambda x: format_docs(x["context"]))
            | prompt
            | llm
            | StrOutputParser()
        )

        self.chain = rag_chain
        return self.get_chain().with_config(
            callbacks=[BaseChain.get_langfuse_callback(session_id, tags)]
        )
