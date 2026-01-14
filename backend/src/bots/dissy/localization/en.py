from bots.dissy.localization.base_local import (
    BaseLocalization,
    validate_localization,
)

english_localization: BaseLocalization = {
    "greeting_message": (
        "Hello 👋 I am _Dissy_ and I'm here to help you learn and understand concepts about distributed Systems. "
        "I'm excited to be your assistant and guide throughout this journey. "
        "\nWhere shall we start? 🤗"
    ),
    "no_competence_selected": (
        "Please select a competence first."
    ),
}

validate_localization(english_localization, BaseLocalization)
