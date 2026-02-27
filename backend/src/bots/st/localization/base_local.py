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
    learning_type_sensing_prompt: str  # descriptions of the learning types for prompts
    learning_type_intuitive_prompt: str
    learning_type_thinking_prompt: str
    learning_type_feeling_prompt: str
    no_module_selected: str  # message when no module is selected
    chat_message_content: str  # user messages for different chat options
    chat_message_exercises: str
    chat_message_organizational: str
