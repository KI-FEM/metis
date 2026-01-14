from bots.study.localization.base_local import BaseLocalization, validate_localization

english_localization: BaseLocalization = {
    "greeting_message": (
        "Hello 👋 I am _Study Competence Bot_. I am here to assist you with your study-related issues. 🧑‍🎓 "
        "I can teach you about various skills, prepare for an upcoming exam or just talk about a current issue you are facing. "
        "\nHow can I help you today? 🤗"
    ),    
    "greeting_message_skill_selected": (
        "Hello 👋 I am _Study Competence Bot_. I am here to assist you with your study-related issues. 🧑‍🎓 "
        "You have selected the {mod} module. If you are ready, click the button below to dive deeper into the topic. 📚"
    ),
    "start_button": (
        "Let's get started"
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
    "select_module_message": (
        "Select a topic you would like to learn more about. I will then give you an overview of the topic and we can dive deeper into the details."
    ),
    "feedback_high_fit": (
        "Thank you for your feedback! I am glad to hear that you are satisfied with my assistance. 😊 "
    ),
    "feedback_low_fit": (
        "Thank you for your feedback! I am sorry to hear that you are not satisfied. Try to change your learning type in the personalisation settings and test it out 🙏 "
    ),
    "selected_module_chat_message": (
        "I would like to learn more about {mod}, please."
    ),
    "no_module_selected": (
        "Please select a topic first."
    ),
    "quiz_submitted_message": (
        "Submitted a quiz."
    ),
    "includes_summary_text": (
        "The provided chat history includes a summary of the earlier conversation."
    ),
    "update_summary_text": (
        "Update the following summary with the new information."
    ),
    "bot_description": (
        "I am your personal AI coach, designed to support you with study-related topics like stress management, resilience, and self-organization. Following the principles of systemic coaching, we will work together in this chat to identify your strengths and develop practical strategies tailored to your success. My goal is to empower you for self-help by guiding your reflections with targeted questions.\n"
        "_Metis is based on AI and may provide inaccurate information. Please check important info._"
    ),
    "quiz_correct": (
        "Correct! Well done."
    ),
    "quiz_incorrect": (
        "That is not correct. Please review the solution."
    ),
    "quiz_slider_hint": (
        "The correct answer is in this range."
    ),
    "quiz_response_updated": (
        "📝 You have answered the quiz. Your learning progress has been updated."
    ),
    "quiz_response_learning_unit_completed": (
        "✔️ You have answered all questions for the learning unit {unit}."
    ),
    "quiz_response_concept_increased_competence_level": (
        "🎉 You have completed the concept {concept} at competence level {level}."
    ),
    "quiz_response_concept_completed": (
        "🎓 Wow! You have mastered the concept {concept}."
    ),
    "quiz_response_competence_completed": (
        "⭐ Perfect! You have mastered the competence {competence}."
    ),
    "thinking_agent_finished": (
        "Request analyzed and tasks distributed"
    )
}

validate_localization(english_localization, BaseLocalization)
