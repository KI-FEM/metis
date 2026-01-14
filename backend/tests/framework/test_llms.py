import importlib
import sys
from pathlib import Path

import pytest
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable

from tests.bots.prompt_patcher import PromptPatcher

from .strings import lite_llm_prompt_template

# Add the path to the src folder to the sys.path
sys.path.insert(1, Path(Path(__file__).parent.parent.parent / "src").resolve())
from src.framework.api_types.locale_type import LocaleType
from src.framework.llm.base_llm import BaseLLM
from src.framework.llm.deep_eval_lite_llm import DeepEvalLiteLLM
from src.framework.llm.google_llm import GoogleLLM
from src.framework.llm.kisski_llm import KisskiLLM
from src.framework.llm.lite_llm import LiteLLM
from src.framework.llm.multilingual_llm import MultiLingualLLM
from src.framework.llm.ollama_llm import OllamaLLM
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
        try:
            llm_instance = llm_class()
        except Exception:
            llm_instance = llm_class(model_name="some_model")
        assert isinstance(llm_instance, llm_class)

        # Test llm() method
        llm = llm_instance.llm()
        assert isinstance(llm, Runnable)
        assert llm is not None

    @pytest.fixture(scope="class")
    def llm_classes(self):
        """Get all LLMs in the llm folder."""
        llm_classes = set()
        llm_folder = Path(
            Path(__file__).parent.parent.parent / "src/framework/llm"
        ).resolve()

        for file in llm_folder.iterdir():
            if file.suffix == ".py" and not file.name.startswith("__"):
                module_name = file.stem  # Remove .py extension
                module = importlib.import_module(f"src.framework.llm.{module_name}")
                for name, obj in module.__dict__.items():
                    if (
                        isinstance(obj, type)
                        and "BaseLLM" in str(obj.mro()[1])  # directly inherits BaseLLM
                        and obj != BaseLLM
                    ):
                        # add only if the class is not already in the set based on its name (__name__)
                        if obj.__name__ not in [cls.__name__ for cls in llm_classes]:
                            llm_classes.add(obj)

        return llm_classes

    def test_llms_existing(self, llm_classes, monkeypatch):
        """Test the existing LLMs."""
        skip_llms = [MultiLingualLLM, GoogleLLM, DeepEvalLiteLLM, OllamaLLM]

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
        print(f"LLM classes: {llm_classes}")
        llm_tests = {
            LiteLLM: [self.test_lite_llm],
            ScadsLLM: [self.test_scads_llm],
            KisskiLLM: [self.test_kisski_llm],
            MultiLingualLLM: [self.test_multilingual_llm],
            GoogleLLM: [self.test_google_llm],
            DeepEvalLiteLLM: [self.test_lite_llm],
            OllamaLLM: [self.test_ollama_llm],
        }

        llm_tests_names = [llm.__name__ for llm in llm_tests.keys()]

        for llm_class in llm_classes:
            print(f"Testing LLM class: {llm_class.__name__}")
            print(f"llm_class not in llm_tests: {llm_class.__name__ not in llm_tests_names}")
            if llm_class.__name__ not in llm_tests_names:
                pytest.fail(
                    f"LLM {llm_class.__name__} is not tested. Please add tests for it. "
                    "If you added tests, make sure to add them to the llm_tests"
                    " dictionary."
                )
            i = llm_tests_names.index(llm_class.__name__)
            llm_tests_values = list(llm_tests.values())
            print(f"llm_tests[llm_class] is None: {llm_tests_values[i] is None}")
            print(f"len(llm_tests[llm_class]) == 0: {len(llm_tests_values[i]) == 0}")
            if (llm_tests_values[i] is None
                or len(llm_tests_values[i]) == 0
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

    def test_google_llm(self, monkeypatch):
        """Test the GoogleLLM."""
        monkeypatch.setenv("GOOGLE_API_KEY", "some_key")
        client = GoogleLLM(model_name="some_model")
        llm = client.llm()
        assert isinstance(llm, Runnable)

        assert client.get_model_name() == "some_model"

    def test_ollama_llm(self, monkeypatch):
        """Test the OllamaLLM."""
        monkeypatch.setenv("OLLAMA_URL", "some_url")
        client = OllamaLLM(model_name="some_model")
        llm = client.llm()
        assert isinstance(llm, Runnable)

        assert client.get_model_name() == "some_model"

    def test_multilingual_llm(self, monkeypatch):
        """Test the MultiLingualLLM."""
        monkeypatch.setenv("SCADS_API_KEY", "some_key")
        monkeypatch.setenv("KISSKI_API_KEY", "some_key")
        lite_llm = LiteLLM(model_name="some_llm")
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
        lite_llm = LiteLLM(model_name="some_llm")
        assert (
            lite_llm.get_model_id() == "cyberagent/Llama-3.1-70B-Japanese-Instruct-2407"
        )
        chat = [
            {"content": "You are an assistant.", "role": "system"},
            {"content": "Hello {{name}}", "role": "user"},
        ]
        PromptPatcher().add_prompt(
            prompt=chat,
            name="title-en",
            prompt_type="chat",
        ).patch(mocker)

        assert (
            lite_llm.get_langfuse_prompt("title-en").template
            == lite_llm_prompt_template
        )
