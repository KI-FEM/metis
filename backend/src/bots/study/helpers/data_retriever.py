import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from bots.study.helpers.data_structure import structure
from framework.api_types.locale_type import LocaleType


def get_questions(topic: str, locale: LocaleType, module: str=None) -> dict:
    """Get the questions of the given submodule."""
    questions = []
    if module is None:
        all_questions = [
            question
            for module_iter in structure["topics"][topic]["modules"].values()
            for submodule in structure["topics"][topic]["modules"][module_iter][
                "submodules"
            ].values()
            for question in submodule["example_questions"]
        ]
    else:
        all_questions = [
            question
            for submodule in structure["topics"][topic]["modules"][module][
                "submodules"
            ].values()
            for question in submodule["example_questions"]
        ]
    questions = [question[locale.value] for question in all_questions]
    return questions
