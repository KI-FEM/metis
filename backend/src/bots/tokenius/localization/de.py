from bots.tokenius.localization.base_local import (
    BaseLocalization,
    validate_localization,
)

german_localization: BaseLocalization = {
    "greeting_message": (
        "Hallo 👋 Ich bin _Tokenius_ und ich bin hier, um dir dabei zu helfen, die "
        "Konzepte und Geheimnisse von Large Language Models zu lernen und zu verstehen. "
        "Ich freue mich darauf, dein Assistent und Begleiter auf dieser Reise zu sein. "
        "\nWo sollen wir anfangen? 🤗"
    ),
    "no_competence_selected": (
        "Bitte wähle zuerst eine Kompetenz aus."
    ),
}

validate_localization(german_localization, BaseLocalization)
