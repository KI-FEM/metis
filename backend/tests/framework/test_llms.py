import importlib
import os
import sys
from pathlib import Path

import pytest
from tests.bots.prompt_patcher import PromptPatcher
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable

from .strings import lite_llm_prompt_template

# Add the path to the src folder to the sys.path
sys.path.insert(1, Path(Path(__file__).parent.parent.parent / "src").resolve())
from src.framework.api_types.locale_type import LocaleType
from src.framework.llm.base_llm import BaseLLM
from src.framework.llm.kisski_llm import KisskiLLM
from src.framework.llm.lite_llm import LiteLLM
from src.framework.llm.multilingual_llm import MultiLingualLLM
from src.framework.llm.scads_llm import ScadsLLM


class TestLLMs:
    """Test class for the LLMs."""

    @pytest.fixture(scope="module")
    def prompts(self) -> PromptTemplate:
        """Get the prompts for the LLMs."""
        return PromptTemplate(
            template="You are a helpful assistant. {input}",
            input_variables=["input"],
        )

    def _test_llm(self, llm_class):
        # Initialize the LLM
        llm_instance = llm_class()
        assert isinstance(llm_instance, llm_class)

        # Test llm() method
        llm = llm_instance.llm()
        assert isinstance(llm, Runnable)
        assert llm is not None

    @pytest.fixture(scope="class")
    def llm_classes(self):
        """Get all LLMs in the llm folder."""
        llm_classes = []
        llm_folder = Path(
            Path(__file__).parent.parent.parent / "src/framework/llm"
        ).resolve()

        for file in os.listdir(llm_folder):
            if file.endswith(".py") and not file.startswith("__"):
                module_name = file[:-3]  # Remove .py extension
                module = importlib.import_module(f"src.framework.llm.{module_name}")
                for name, obj in module.__dict__.items():
                    if (
                        isinstance(obj, type)
                        and 'BaseLLM' in str(obj.mro()[1]) # directly inherits BaseLLM
                        and obj != BaseLLM
                    ):
                        llm_classes.append(obj)

        return llm_classes

    def test_llms_existing(self, llm_classes, monkeypatch):
        """Test the existing LLMs."""
        skip_llms = [ MultiLingualLLM ]
        
        monkeypatch.setenv("SCADS_API_KEY", "some_key")
        monkeypatch.setenv("KISSKI_API_KEY", "some_key")
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        for llm_class in llm_classes:
            if llm_class in skip_llms:
                continue
            self._test_llm(llm_class)

    def test_llms_are_tested(self, llm_classes):
        """Test that all LLMs are tested."""
        llm_tests = {
            ScadsLLM: [self.test_scads_llm],
            KisskiLLM: [self.test_kisski_llm],
            MultiLingualLLM: [self.test_multilingual_llm],
            LiteLLM: [self.test_lite_llm],
        }

        for llm_class in llm_classes:
            if (
                llm_class not in llm_tests
                or llm_tests[llm_class] is None
                or len(llm_tests[llm_class]) == 0
            ):
                pytest.fail(
                    f"LLM {llm_class} is not tested. Please add tests for it. "
                    "If you added tests, make sure to add them to the llm_tests"
                    " dictionary."
                )

    def test_scads_llm(self, monkeypatch):
        """Test the ScadsLLM."""
        # in case the .env file is not present
        monkeypatch.setenv("SCADS_API_KEY", "some_key")
        client = ScadsLLM()
        llm = client.llm()
        assert isinstance(llm, Runnable)

        client.set_model_name("some_model")
        assert client.model_name == "some_model"

    def test_kisski_llm(self, monkeypatch):
        """Test the KisskiLLM."""
        monkeypatch.setenv("KISSKI_API_KEY", "some_key")
        client = KisskiLLM()
        llm = client.llm()
        assert isinstance(llm, Runnable)

        client.set_model_name("some_model")
        assert client.model_name == "some_model"

    def test_multilingual_llm(self, monkeypatch):
        """Test the MultiLingualLLM."""
        monkeypatch.setenv("SCADS_API_KEY", "some_key")
        monkeypatch.setenv("KISSKI_API_KEY", "some_key")
        lite_llm = LiteLLM()
        scads_llm = ScadsLLM()
        multi_llm = MultiLingualLLM(default_locale=LocaleType.DE)
        multi_llm.add_llm(LocaleType.EN, lite_llm)
        multi_llm.add_llm(LocaleType.DE, scads_llm)
        assert multi_llm.default_locale == LocaleType.DE
        assert multi_llm.get_llm(LocaleType.EN) == lite_llm
        assert multi_llm.llm().model_config == scads_llm.llm().model_config

    @pytest.mark.skip(reason="Seems to crash CI?")
    def test_lite_llm(self, monkeypatch, mocker):
        """Test the LiteLLM."""
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        lite_llm = LiteLLM()
        assert lite_llm.get_model_id() == \
            "cyberagent/Llama-3.1-70B-Japanese-Instruct-2407"
        chat = [
            {"content": "You are an assistant.", "role": "system"},
            {"content": "Hello {{name}}", "role": "user"}
        ]
        PromptPatcher().add_prompt(
            prompt=chat,
            name="title-en",
            prompt_type="chat",
        ).patch(mocker)

        assert lite_llm.get_langfuse_prompt("title-en").template == \
            lite_llm_prompt_template
