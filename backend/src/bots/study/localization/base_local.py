from typing import Any, Dict, TypedDict


def validate_localization(localization: Dict[str, Any], base_class: type) -> None:
    """Validate that the localization dictionary has all the required keys."""
    missing_keys = [
        field for field in base_class.__annotations__ if field not in localization
    ]
    if missing_keys:
        raise ValueError(f"Missing keys in localization: {missing_keys}")


class BaseLocalization(TypedDict):
    """Base class for localization of messages for study competence bot."""

    greeting_message: str  # greeting message when starting the chat with the bot
    greeting_message_skill_selected: str
    start_button: str
    select_module_message: str
    feedback_low_fit: str
    feedback_high_fit: str
    selected_module_chat_message: str
    no_module_selected: str
    quiz_submitted_message: str
    includes_summary_text: str
    update_summary_text: str
    bot_description: str
    quiz_response_updated: str
    quiz_response_learning_unit_completed: str
    quiz_response_concept_increased_competence_level: str
    quiz_response_concept_completed: str
    quiz_response_competence_completed: str
    thinking_agent_finished: str
