from bots.tokenius.localization.base_local import (
    BaseLocalization,
    validate_localization,
)

english_localization: BaseLocalization = {
    "greeting_message": (
        "Hello 👋 I am _Tokenius_ and I'm here to help you learn and understand concepts and secrets of Large Language Models. "
        "I'm excited to be your assistant and guide throughout this journey. "
        "\nWhere shall we start? 🤗"
    ),
    "no_competence_selected": (
        "Please select a competence first."
    ),
}

validate_localization(english_localization, BaseLocalization)
