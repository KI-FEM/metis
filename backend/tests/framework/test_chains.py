import importlib
import os
import sys
from pathlib import Path

import pytest
from langchain_core.language_models import FakeListLLM
from langchain_core.prompts import PromptTemplate

sys.path.append(str(Path(Path(__file__).parent.parent.parent / "src")))
from framework.chains.base_chain import BaseChain
from framework.chains.passthrough_chain import PassthroughChain
from framework.chains.retrieval_chain import RetrievalChain
from framework.llm.lite_llm import LiteLLM
from framework.rag.embeddings.hf_embedding import HFEmbedding


class TestChains:
    """Test class for the chains."""

    @pytest.fixture
    def llm_client(self) -> LiteLLM:
        """LLM client."""
        return LiteLLM()

    @pytest.fixture
    def prompts(self) -> PromptTemplate:
        """Prompts."""
        return PromptTemplate(
            template="You are a helpful assistant. {input}",
            input_variables=["input"],
        )

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM that returns a predictable response."""
        return FakeListLLM(responses=["This is a mock response from the LLM."])

    @pytest.fixture
    def embeddings(self) -> HFEmbedding:
        """Embeddings."""
        return HFEmbedding(
            model_kwargs={"device": "cpu"},
        )

    @pytest.fixture
    def get_all_chains(self) -> list[BaseChain]:
        """Get all chains in the chains folder."""
        chain_classes = []
        chain_folder = Path(
            Path(__file__).parent.parent.parent / "src/framework/chains"
        ).resolve()
        for file in os.listdir(chain_folder):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]  # Remove .py extension
                module = importlib.import_module(f"src.framework.chains.{module_name}")
                for name, obj in module.__dict__.items():
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, BaseChain)
                        and obj != BaseChain
                    ):
                        chain_classes.append(obj)
        return chain_classes

    def test_chains_are_tested(self, get_all_chains):
        """Test that all chains are tested."""
        chain_tests = {
            PassthroughChain: [self.test_passthrough_chain],
            RetrievalChain: [self.test_retrieval_chain],
        }

        for chain in get_all_chains:
            if (
                chain not in chain_tests
                or not chain_tests[chain]
                or len(chain_tests[chain]) == 0
            ):
                pytest.fail(
                    f"Chain {chain} is not tested. Add a test for it in test_chains.py."
                    " If you added a test, make sure it is added to the chain_tests "
                    "dictionary."
                )

    @pytest.mark.asyncio
    async def test_passthrough_chain(self, prompts, mock_llm, monkeypatch):
        """Test the passthrough chain."""
        # Disable Langfuse tracing
        monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "testing")
        monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "false")
        monkeypatch.setenv("LANGFUSE_HOST", "https://asdf.invalid")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "some_public_key")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "some_secret_key")

        # Initialize the passthrough chain
        passthrough = PassthroughChain()

        # Create the chain with test inputs
        chain = passthrough.create_chain(
            llm=mock_llm, prompt=prompts, session_id="test_session", tags=["test"]
        )

        # Create second chain using the DictOutputParser
        dict_chain = passthrough.create_chain(
            llm=mock_llm, prompt=prompts, session_id="test_session", tags=["test"], use_dict_output_parser=True
        )

        # Verify that the chain is properly created
        from langchain_core.runnables import RunnableSerializable

        assert isinstance(chain, RunnableSerializable)
        assert isinstance(dict_chain, RunnableSerializable)

        # Test that the chain processes input correctly
        test_input = {"input": "What is the capital of France?"}
        result = await chain.ainvoke(test_input)

        dict_test_input = {"input": "What is the capital of France?"}
        dict_result = await dict_chain.ainvoke(dict_test_input)

        # Verify the result matches our mock LLM response
        assert result == "This is a mock response from the LLM."
        assert dict_result == {"answer": "This is a mock response from the LLM.", "additional_kwargs": {}}

    @pytest.mark.asyncio
    async def test_retrieval_chain(self, prompts, mock_llm, monkeypatch):
        """Test the retrieval chain."""
        # Disable Langfuse tracing
        monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "testing")
        monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "false")
        monkeypatch.setenv("LANGFUSE_HOST", "https://asdf.invalid")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "some_public_key")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "some_secret_key")

        # Initialize the retrieval chain
        retrieval = RetrievalChain()

        # Create the chain with test inputs
        chain = retrieval.create_chain(
            llm=mock_llm, prompt=prompts, session_id="test_session", tags=["test"]
        )

        # Verify that the chain is properly created
        from langchain_core.runnables import RunnableSerializable

        assert isinstance(chain, RunnableSerializable)

        # Create mock documents for the context
        from langchain_core.documents import Document

        mock_docs = [
            Document(page_content="Paris is the capital of France."),
            Document(page_content="France is in Europe."),
        ]

        # Test the chain with mock documents as context
        test_input = {"input": "What is the capital of France?", "context": mock_docs}

        # Invoke the chain and verify the output
        result = await chain.ainvoke(test_input)

        # Verify the result dict contains our mock response as the answer
        assert "This is a mock response from the LLM." in result["answer"]
