from bots.st.localization.base_local import BaseLocalization, validate_localization

english_localization: BaseLocalization = {
    "greeting_message": (
        "Hello 👋 I am _StBuddy_ and I'm here to help you learn and understand concepts in software technology. "
        "I'm excited to be your assistant and guide throughout this journey. "
        "\nWhere shall we start? 🤗"
    ),
    "learning_type_sensing_prompt": (
        "The user you are interacting with is of the learning type Sensing, indicating that they like to relate the learned material to the real world. "
        "Therefore, they value real-world case studies, critical analyzes of real-world situations, and problem-solving exercises that focus on facts and practical information. "
        "They learn best when given step-by-step instructions and standard problem-solving methods. When providing new information, start with examples and real-world applications and then explain using theory."
    ),
    "learning_type_intuitive_prompt": (
        "The user you are interacting with is of the learning type Intuitive, indicating that they like to explore, simulate and experiment. "
        "When learning new things, they like to perceive information in form of theory or concept before being confronted with examples or application. "
        "Intuitive learners recognize patterns and connections well and enjoy exploring these connections. Therefore, support the recognition of patterns and relationships on related topics. "
        "When providing examples or exercises, be creative, make them abstract and imaginative, and avoid repetition."
    ),
    "learning_type_thinking_prompt": (
        "The user you are interacting with is of the learning type Thinking, meaning that they appreciate objective and logical approaches when learning new things. "
        "Start with theory and then provide fact-based and realistic examples to demonstrate the applicability of the topic. "
        "Provide general rules as well as rational and clearly structured explanations of principles related to the topic."
    ),
    "learning_type_feeling_prompt": (
        "The user you are interacting with is of the learning type Feeling, indicating that they are likely driven by their emotions and personal values when learning. "
        "They appreciate connections to their own experiences and feelings. Incorporate storytelling or personal anecdotes that evoke emotions related to the topic. "
        "Emphasize how the subject matter aligns with their values and beliefs to create a meaningful learning experience for them."
    ),
    "no_module_selected": (
        "Please select a topic first."
    ),
    "chat_message_content": (
        "I would like to study the lecture contents today."
    ),
    "chat_message_exercises": (
        "I would like to work on the exercises today."
    ),
    "chat_message_organizational": (
        "I have some organizational questions."
    ),
}

validate_localization(english_localization, BaseLocalization)
