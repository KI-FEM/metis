from bots.st.localization.base_local import BaseLocalization, validate_localization

german_localization: BaseLocalization = {
    "greeting_message": (
        "Hallo 👋 Ich bin der _StBuddy_ und ich bin hier, um dir dabei zu helfen, Konzepte in der Software-Technologie zu lernen und zu verstehen. "
        "Ich freue mich darauf, dein Assistent und Begleiter auf dieser Reise zu sein. "
        "\nWo sollen wir anfangen? 🤗"
    ),
    "learning_type_sensing_prompt": (
        "Der Benutzer, mit dem du interagierst, gehört zum Lerntyp _Wahrnehmen_, was bedeutet, dass er das Gelernte gerne auf die reale Welt bezieht. "
        "Nutzer dieses Lerntyps schätzen Fallstudien aus der Praxis, kritische Analysen von realen Situationen und Problemlösungsübungen, die sich auf Fakten und praktische Informationen konzentrieren. "
        "Sie lernen am besten, wenn sie Schritt-für-Schritt-Anweisungen und Standard-Problemlösungsmethoden erhalten. Beginne bei der Vermittlung neuer Informationen mit Beispielen und realen Anwendungen und erkläre diese dann anhand der Theorie."
    ),
    "learning_type_intuitive_prompt": (
        "Der Benutzer, mit dem du interagierst, gehört zum Lerntyp _Intuitiv_, was darauf hindeutet, dass er gerne erforscht, simuliert und experimentiert. "
        "Wenn Nutzer dieses Lerntyps etwas Neues lernen, nehmen sie die Informationen gerne in Form von Theorien oder Konzepten wahr, bevor sie mit Beispielen oder Anwendungen konfrontiert werden. "
        "Intuitive Lernende erkennen Muster und Zusammenhänge gut und haben Spaß daran, diese Zusammenhänge zu erforschen. Unterstütze daher das Erkennen von Mustern und Zusammenhängen bei verwandten Themen. "
        "Sei bei der Bereitstellung von Beispielen oder Übungen kreativ, gestalte sie abstrakt und phantasievoll und vermeide Wiederholungen."
    ),
    "learning_type_thinking_prompt": (
        "Der Nutzer, mit dem du interagierst, gehört zum Lerntyp _Denken_, was bedeutet, dass er objektive und logische Ansätze schätzt, wenn er etwas Neues lernt. "
        "Beginne mit der Theorie und stelle dann faktenbasierte und realistische Beispiele zur Verfügung, um die Anwendbarkeit des Themas zu demonstrieren. "
        "Gebe allgemeine Regeln sowie rationale und klar strukturierte Erklärungen zu Prinzipien, die mit dem Thema zusammenhängen."
    ),
    "learning_type_feeling_prompt": (
        "Der Nutzer, mit dem du interagierst, gehört zum Lerntyp _Fühlen_, was bedeutet, dass er beim Lernen wahrscheinlich von seinen Emotionen und persönlichen Werten geleitet wird. "
        "Nutzer dieses Lerntyps schätzen Verbindungen zu ihren eigenen Erfahrungen und Gefühlen. Binde deshalb Geschichten oder persönliche Anekdoten ein, die Emotionen im Zusammenhang mit dem Thema hervorrufen. "
        "Betone, wie der Lernstoff mit ihren Werten und Überzeugungen übereinstimmt, um eine sinnvolle Lernerfahrung für den Nutzer zu schaffen."
    ),
    "no_module_selected": (
        "Bitte wähle zuerst ein Modul aus."
    ),
    "chat_message_content": (
        "Ich möchte heute den Vorlesungsinhalt lernen."
    ),
    "chat_message_exercises": (
        "Ich möchte heute an den Übungen arbeiten."
    ),
    "chat_message_organizational": (
        "Ich habe einige organisatorische Fragen."
    ),
}

validate_localization(german_localization, BaseLocalization)
