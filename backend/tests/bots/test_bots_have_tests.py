import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(Path(__file__).parent.parent.parent / "src")))
from bots.base_bot import BaseBot


@pytest.fixture
def get_all_bots(monkeypatch):
    """A helper function to get all bots from their files."""
    monkeypatch.setenv("LITELLM_URL", "some_url")
    monkeypatch.setenv("LITELLM_KEY", "some_key")
    bot_classes = []
    bot_folder = Path(Path(__file__).parent.parent.parent / "src/bots").resolve()

    for root, dirs, files in os.walk(bot_folder):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                relative_path = os.path.relpath(root, bot_folder).replace(
                    os.path.sep, "."
                )
                if relative_path == ".":
                    module_name = file[:-3]
                else:
                    module_name = relative_path + "." + file[:-3]
                module = importlib.import_module(f"src.bots.{module_name}")
                for name, obj in module.__dict__.items():
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, BaseBot)
                        and obj != BaseBot
                    ):
                        bot_classes.append(obj)

    return bot_classes


def test_bots_are_tested(get_all_bots):
    """Test that all bots are tested."""
    from bots.citation.citation_bot import CitationBot
    from bots.dissy.chatbot import Dissy
    from bots.grumci.grumci_bot import GrumciBuddy
    from bots.maschbau.maschbau import MaschBau
    from bots.passthrough.passthrough_bot import PassthroughBot
    from bots.scads.scads_assistant_bot import ScaDSAssistantBot
    from bots.st.st_buddy import StBuddy
    from bots.study.study_competence_bot import StudyCompetenceBot
    from bots.tokenius.chatbot import Tokenius

    from .citation.test_citation_bot import TestCitationBot
    from .dissy.test_dissy import TestDissy
    from .grumci.test_grumci_bot import TestGrumciBot
    from .maschbau.test_maschbau_bot import TestMaschbauBot
    from .passthrough.test_passthrough_bot import TestPassthroughBot
    from .scads.test_scads_assistant_bot import TestScaDSAssistantBot
    from .st.test_st_buddy import TestStBuddy
    from .study.test_study_competence_bot import TestStudyCompetenceBot
    from .tokenius.test_tokenius import TestTokenius
    bot_tests = {
        CitationBot.__name__: [TestCitationBot],
        Dissy.__name__:[TestDissy],
        PassthroughBot.__name__: [TestPassthroughBot],
        StBuddy.__name__: [TestStBuddy],
        StudyCompetenceBot.__name__: [TestStudyCompetenceBot],
        GrumciBuddy.__name__: [TestGrumciBot],
        MaschBau.__name__: [TestMaschbauBot],
        Tokenius.__name__: [TestTokenius],
        ScaDSAssistantBot.__name__: [TestScaDSAssistantBot]
    }

    for bot_class in get_all_bots:
        if (
            bot_class.__name__ not in bot_tests
            or bot_tests[bot_class.__name__] is None
            or len(bot_tests[bot_class.__name__]) == 0
        ):
            pytest.fail(
                f"Bot {bot_class} is not tested. Please add tests for it. "
                "If you added a test class, make sure to add it to the bot_tests"
                " dictionary."
            )
