from bots.study.localization.base_local import BaseLocalization, validate_localization

german_localization: BaseLocalization = {
    "greeting_message": (
        "Hallo 👋 Ich bin der _Studienkompetenz Bot_. Ich bin hier, um dir bei deinen studienbezogenen Fragen zu helfen. 🧑‍🎓 "
        "Ich kann dir verschiedene Kompetenzen beibringen, dich auf eine bevorstehende Prüfung vorbereiten oder einfach über ein Problem sprechen, mit dem du aktuell konfrontiert bist. "
        "\nWie kann ich dir heute helfen? 🤗"
    ),
    "greeting_message_skill_selected": (
        "Hallo 👋 Ich bin der _Studienkompetenz Bot_. Ich bin hier, um dir bei deinen studienbezogenen Fragen zu helfen. 🧑‍🎓 "
        "Du hast das Modul {mod} ausgewählt. Wenn du so weit bist, klicke auf den Knopf unter meiner Nachricht, um tiefer in das Thema einzutauchen. 📚"
    ),
    "start_button": (
        "Lass uns beginnen"
    ),
    "select_module_message": (
        "Wähle ein Thema aus, über das du mehr erfahren möchtest. Anschließend gebe ich dir eine Übersicht über das Thema und wir können tiefer in die Details eintauchen. "
    ),
    "feedback_high_fit": (
        "Vielen Dank für dein Feedback! Es freut mich zu hören, dass du mit meiner Unterstützung zufrieden bist. 😊 "
    ),
    "feedback_low_fit": (
        "Vielen Dank für dein Feedback! Es tut mir leid zu hören, dass du nicht zufrieden sind. Versuche deinen Lerntyp in den Personalisierungseinstellungen zu ändern und teste es aus 🙏 "
    ),
    "selected_module_chat_message": (
        "Ich möchte mehr über {mod} lernen."
    ),
    "no_module_selected": (
        "Bitte wähle zuerst ein Modul aus."
    ),
    "quiz_submitted_message": (
        "Hat einen Quiz abgeschlossen."
    ),
    "includes_summary_text": (
        "Die bereitgestellte Chat-Historie enthält eine Zusammenfassung der früheren Konversation."
    ),
    "update_summary_text": (
        "Aktualisiere die folgende Zusammenfassung mit der neuen Information."
    ),
    "quiz_correct": (
        "Richtig! Gut gemacht."
    ),
    "quiz_incorrect": (
        "Das ist leider nicht richtig. Bitte überprüfe die Lösung."
    ),
    "quiz_slider_hint": (
        "Die richtige Antwort liegt in diesem Bereich."
    ),
    "bot_description": (
        "Ich bin Ihr persönlicher KI-Coach, der Sie bei studienbezogenen Themen wie Stressbewältigung, Resilienz und Selbstorganisation unterstützt. Nach den Prinzipien des systemischen Coachings arbeiten wir in diesem Chat zusammen, um Ihre Stärken zu erkennen und praktische, auf Sie zugeschnittene Lösungsstrategien zu entwickeln. Mein Ziel ist es, Sie durch gezielte Fragen zur Selbstreflexion anzuregen und Sie so zur Selbsthilfe zu befähigen.\n _Metis basiert auf KI und kann ungenaue Informationen liefern. Bitte überprüfe wichtige Informationen._"
    ),
    "quiz_response_updated": (
        "📝 Du hast den Quiz beantwortet. Dein Lernfortschritt wurde aktualisiert."
    ),
    "quiz_response_learning_unit_completed": (
        "✔️ Du hast alle Fragen zu der Lerneinheit {unit} beantwortet."
    ),
    "quiz_response_concept_increased_competence_level": (
        "🎉 Du hast das Konzept {concept} auf Kompetenzniveau {level} abgeschlossen."
    ),
    "quiz_response_concept_completed": (
        "🎓 Wow! Du hast das Konzept {concept} vollständig beherrscht."
    ),
    "quiz_response_competence_completed": (
        "⭐ Sehr gut! Du hast die Kompetenz {competence} vollständig beherrscht."
    ),
    "thinking_agent_finished": (
        "Anfrage analysiert und Aufgaben verteilt"
    )
}

validate_localization(german_localization, BaseLocalization)
