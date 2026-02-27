"""File containing data for testing the study bot."""

select_topic_data = {
    "storage": [{"key": "selected_module", "value": "resilience"}],
    "language": "en",
    "learning_type_id": "FEELING",
    "chat_history": """[{"from":"bot","message":"Hello 👋 I am _Study Competence Bot_. I am here to assist you with your study-related issues. 🧑‍🎓 I can teach you about various skills, prepare for an upcoming exam or just talk about a current issue you are facing. \\nHow can I help you today? 🤗","actions":[{"label":"Structure of a Paper","name":"select_topic","value":"StructureOfAPaper"}]}]""",
}

suggested_questions_data = {
    "messages": [
        'Why are learning strategies important for academic success?',
        'What role do monitoring strategies, such as self-questioning, play in learning?',
        'How can time management improve the learning process?',
        'Why is self-directed learning often neglected in schools?',
        'What practical methods help to apply learning strategies purposefully?',
    ],
    "storage": {}
}

open_conversation_data = {
    "storage": {"selected_module": "resilience", "chat_id": "123", "skill_level": "intermediate"},
    "language": "en",
    "learning_type_id": "FEELING",
    "chat_history": [
        {
            "message": "Hello 👋 I am _Study Competence Bot_. I am here to assist you with your study-related issues. 🧑‍🎓 I can teach you about various skills, prepare for an upcoming exam or just talk about a current issue you are facing. \nHow can I help you today? 🤗",
            "sender": "assistant",
            "buttons": [],
            "meta_information": {"sources": None, "llm_model": None},
        },
        {
            "message": "Select a topic you would like to learn more about. I will then give you an overview of the topic and we can dive deeper into the details.",
            "sender": "assistant",
            "buttons": [
                {
                    "chat_message": "I would like to learn more about Resilience, please.",
                    "label": "Resilience",
                    "callback": {
                        "endpoint": "select_module",
                        "data": {"value": "resilience"},
                    },
                    "store": {"selected_module": "resilience"},
                }
            ],
            "meta_information": {"sources": None, "llm_model": None},
        },
        {
            "sender": "user",
            "message": "I would like to learn more about Resilience, please.",
            "buttons": [],
            "meta_information": {},
        },
        {
            "message": 'Resilience refers to the ability to bounce back or rebound from adversity, originating from the Latin verb "resilire". It is a complex concept that involves successfully mastering risk situations, and is often linked to individual psychological perspectives. In the context of educational advancement, resilience is explored as a potential factor influencing one\'s ability to achieve a higher level of education despite challenges. By understanding the underlying principles of resilience, such as its connection to risk situations and successful mastery, we can begin to recognize patterns and relationships between resilience and educational outcomes, ultimately shedding light on the intricacies of this multifaceted concept.',
            "sender": "assistant",
            "buttons": [],
            "meta_information": {
                "sources": [
                    {
                        "label": "Educational Advancement and Resilience - Casper",
                        "chunk": "In this study, resilience is considered from an individual psychological perspective.",
                        "url": "/Users/rosteck/dev/studybot/backend/data/StudyCompetence/en/resilience/Casper_Bildungsaufstieg_und_Resilienz.md",
                    },
                    {
                        "label": "Educational Advancement and Resilience - Casper",
                        "chunk": "The literature search on resilience was conducted in October 2015 in the following catalogues and databases: Joint Union Catalogue including Online Contents (GVK-plus), Karlsruhe Virtual Catalogue (KVK), Scopus, PSYNDEX and PsycINFO.",
                        "url": "/Users/rosteck/dev/studybot/backend/data/StudyCompetence/en/resilience/Casper_Bildungsaufstieg_und_Resilienz.md",
                    },
                    {
                        "label": "Educational Advancement and Resilience - Casper",
                        "chunk": "In order to approach a working definition of resilience despite the different opinions, the word origin and various definitions from relevant works (Luthar & Cicchetti, 2000; Masten, 2014; Rutter, 1987) are first listed. Then, common elements of the definitions are highlighted and used to develop a working definition.The word resilience comes from the Latin language. The Latin verb resilire means to bounce back or rebound (Bibliographical Institute, 2015b: no page number).The English word resilience is translated as elasticity (PONS, 2015: no page number).",
                        "url": "/Users/rosteck/dev/studybot/backend/data/StudyCompetence/en/resilience/Casper_Bildungsaufstieg_und_Resilienz.md",
                    },
                    {
                        "label": "Educational Advancement and Resilience - Casper",
                        "chunk": "There is widespread agreement that resilience is linked to two conditions: firstly, there is a risk situation and secondly, the risk situation is successfully mastered (Fletcher & Sarkar, 2013; Fröhlich-Gildhoff & Rönnau-Böse, 2015; Masten et al., 2009). Before establishing the working definition of resilience, the understanding of risk situation and the understanding of successfully mastering a risk situation will first be explained. In doing so, content-related references to the topic of educational advancement will be made.",
                        "url": "/Users/rosteck/dev/studybot/backend/data/StudyCompetence/en/resilience/Casper_Bildungsaufstieg_und_Resilienz.md",
                    },
                ],
                "llm_model": "llama-3.3-70b",
            },
        },
        {
            "sender": "user",
            "message": "I don't know what to write.",
            "buttons": [],
            "meta_information": {},
        },
    ],
}

open_conversation_data_st_buddy = {
    "storage": {"selected_module": "content", "chat_id": "123"},
    "language": "en",
    "learning_type_id": "FEELING",
    "chat_history": [
        {
            "message": "Hello 👋 I am _StBuddy_ and I'm here to help you learn and understand concepts in software technology. I'm excited to be your assistant and guide throughout this journey. \nWhere shall we start? 🤗",
            "sender": "assistant",
            "buttons": [
                {
                    'callback': {
                        'data': {'value': 'content'},
                        'endpoint': 'select_module'
                    },
                    'chat_message': 'Content',
                    'label': 'Content',
                    'store': {'selected_module': 'content'}
                }
            ],
            "meta_information": {"sources": None, "llm_model": None},
        },
        {
            "sender": "user",
            "message": "I would like to learn more about the lecture content, please.",
            "buttons": [],
            "meta_information": {},
        },
        {
            "message": 'Resilience refers to the ability to bounce back or rebound from adversity, originating from the Latin verb "resilire". It is a complex concept that involves successfully mastering risk situations, and is often linked to individual psychological perspectives. In the context of educational advancement, resilience is explored as a potential factor influencing one\'s ability to achieve a higher level of education despite challenges. By understanding the underlying principles of resilience, such as its connection to risk situations and successful mastery, we can begin to recognize patterns and relationships between resilience and educational outcomes, ultimately shedding light on the intricacies of this multifaceted concept.',
            "sender": "assistant",
            "buttons": [],
            "meta_information": {
                "sources": [
                    {
                        "label": "Educational Advancement and Resilience - Casper",
                        "chunk": "In this study, resilience is considered from an individual psychological perspective.",
                        "url": "/Users/rosteck/dev/studybot/backend/data/StudyCompetence/en/resilience/Casper_Bildungsaufstieg_und_Resilienz.md",
                    },
                    {
                        "label": "Educational Advancement and Resilience - Casper",
                        "chunk": "The literature search on resilience was conducted in October 2015 in the following catalogues and databases: Joint Union Catalogue including Online Contents (GVK-plus), Karlsruhe Virtual Catalogue (KVK), Scopus, PSYNDEX and PsycINFO.",
                        "url": "/Users/rosteck/dev/studybot/backend/data/StudyCompetence/en/resilience/Casper_Bildungsaufstieg_und_Resilienz.md",
                    },
                    {
                        "label": "Educational Advancement and Resilience - Casper",
                        "chunk": "In order to approach a working definition of resilience despite the different opinions, the word origin and various definitions from relevant works (Luthar & Cicchetti, 2000; Masten, 2014; Rutter, 1987) are first listed. Then, common elements of the definitions are highlighted and used to develop a working definition.The word resilience comes from the Latin language. The Latin verb resilire means to bounce back or rebound (Bibliographical Institute, 2015b: no page number).The English word resilience is translated as elasticity (PONS, 2015: no page number).",
                        "url": "/Users/rosteck/dev/studybot/backend/data/StudyCompetence/en/resilience/Casper_Bildungsaufstieg_und_Resilienz.md",
                    },
                    {
                        "label": "Educational Advancement and Resilience - Casper",
                        "chunk": "There is widespread agreement that resilience is linked to two conditions: firstly, there is a risk situation and secondly, the risk situation is successfully mastered (Fletcher & Sarkar, 2013; Fröhlich-Gildhoff & Rönnau-Böse, 2015; Masten et al., 2009). Before establishing the working definition of resilience, the understanding of risk situation and the understanding of successfully mastering a risk situation will first be explained. In doing so, content-related references to the topic of educational advancement will be made.",
                        "url": "/Users/rosteck/dev/studybot/backend/data/StudyCompetence/en/resilience/Casper_Bildungsaufstieg_und_Resilienz.md",
                    },
                ],
                "llm_model": "llama-3.3-70b",
            },
        },
        {
            "sender": "user",
            "message": "I don't know what to write.",
            "buttons": [],
            "meta_information": {},
        },
    ],
}

submit_test_data = {
    "storage": {"selected_module": "resilience"},
    "language": "en",
    "learning_type_id": "FEELING",
    "chat_history": open_conversation_data["chat_history"],
    "questions": [
        {
            "id": 1,
            "question": "This is a question",
            "type": "single-choice",
            "options": [
                {
                    "id": 1,
                    "label": "This is an answer",
                    "correct": True
                }
            ]
        }
    ],
    "answers": [
      {
        "question_id": 1,
        "selected_options_ids": [1]
      },
    ]
}

router_learning_types_data = {
    "learning_types": [
        {
            "id": "FEELING",
            "title": {
                "en": "Feeling",
                "de": "Feeling",
            },
            "long_description": {
                "de": """Wäre es möglich dass du den Feeling Lernstil magst? 

Personen des Feeling-Lernstils beginnen lieber mit der Theorie, bevor sie diese anwenden, und bevorzugen einen menschenzentrierten Ansatz bei den Themen. Sie treffen Entscheidungen basierend auf persönlichen Werten und den Auswirkungen auf andere Menschen. Diese Lernenden schätzen Selbstbeteiligung und Zusammenarbeit, schätzen eine positive und optimistische Einstellung. 

- Magst du Geschichten oder persönliche Anekdoten? 
- Findest du es gut, wenn du auch andere voranbringen und unterstützen kannst? 
- Ist es dir wichtig, dass das was du lernst auch von Bedeutung ist? 

Die Wahrscheinlichkeit ist hoch, dass du den Feeling Lernstil magst!""",
                "en": """Is it possible that you are a feeling learner? 

Feeling learners prefer to start with theory before applying it and prefer a human-centered approach to topics. They make decisions based on personal values and the impact on other people. These learners value self-involvement and collaboration, and appreciate a positive and optimistic attitude. 

- Do you like stories or personal anecdotes? 
- Do you think it's good if you can also help and support others? 
- Is it important to you that what you learn is meaningful? 

There's a good chance that you're a feeling learner!""",
            },
            "short_description": {
                "en": "This person prefers: empathy, collaboration, values, personal connection, storytelling.",
                "de": "Diese Person orientiert sich an: Empathie, Zusammenarbeit, Werten, persönlicher Verbindung, Geschichten.",
            },
        },
        {
            "id": "SENSING",
            "title": {
                "en": "Sensing",
                "de": "Sensing",
            },
            "long_description": {
                "de": """Bist du ein Sensing-Lernender?

Dieser Lernstil bevorzugt es, mit praktischen Anwendungen zu beginnen bevor man sich der Theorie widmet. Diese Personen legen Wert auf Struktur, folgen Agenden oder Richtlinien und lernen am besten mit schrittweisen Methoden. Sie verlassen sich oft auf vergangene Erfahrungen und bewährte Ansätze der Problemlösung. 

- Sind dir konkrete Fakten und realistische Szenarien wichtig? 
- Schätzt du präzise Aufgaben und klare, umsetzbare Vorschläge? 
- Magst du praktische Informationen mehr als abstrakte Theorien? 

Dann lernst du wahrscheinlich anhand des Sensing Lernstils!""",
                "en": """Are you a sensing learner?

This learning style prefers to start with practical applications before moving on to theory. These individuals value structure, follow agendas or guidelines and learn best with step-by-step methods. They often rely on past experiences and proven approaches to problem solving. 

- Are concrete facts and realistic scenarios important to you? 
- Do you appreciate precise tasks and clear, actionable suggestions? 
- Do you like practical information more than abstract theories? 

Then you're probably a sensing learner!""",
            },
            "short_description": {
                "en": "This person prefers: practicality, structure, real-world examples, step-by-step methods, concrete facts.",
                "de": "Diese Person legt Wert auf: Praktikabilität, Struktur, reale Beispiele, schrittweise Methoden, konkrete Fakten.",
            },
        },
        {
            "id": "INTUITIVE",
            "title": {
                "en": "Intuitive",
                "de": "Intuitive",
            },
            "long_description": {
                "de": """Oder gefällt dir der Intuitive Lernstil? 

Für diesen Lernstil liegt der Fokus zuerst auf Theorie und Konzepten, danach widmet diese Person sich Verbindungen, Mustern oder Zusammenhängen. Diese Lernenden bevorzugen unstrukturierte Aktivitäten mit Wahlmöglichkeiten und ziehen selbstständiges Lernen und unabhängiges Arbeiten vor. Sie gedeihen bei der Lösung neuer, komplexer Probleme mit dem Wissen aus dem Kurs und der kritischen Analyse neuer Ideen. 

- Magst du kreative, abstrakte Aufgaben? 
- Lernst du gern neue Fähigkeiten und nutzt deine Fantasie? 
- Magst du abwechslungsreiche Übungen? 

Dann willst du wahrscheinlich eher den Intuitive Lernstil!""",
                "en": """Or are you an intuitive learner? 

For this learning style, the focus is first on theory and concepts, and then on connections, patterns or contexts. These learners prefer unstructured activities with choices and prefer self-directed learning and independent work. They thrive on solving new, complex problems using knowledge from the course and critically analyzing new ideas. 

- Do you like creative, abstract tasks? 
- Do you like learning new skills and using your imagination? 
- Do you like varied exercises? 

Then you're probably more of an intuitive learner!""",
            },
            "short_description": {
                "en": "This person prefers: theory, creativity, abstract tasks, independence, conceptual links.",
                "de": "Diese Person schätzt: Theorie, Kreativität, abstrakte Aufgaben, Unabhängigkeit, konzeptionelle Verbindungen.",
            },
        },
        {
            "id": "THINKING",
            "title": {
                "en": "Thinking",
                "de": "Thinking",
            },
            "long_description": {
                "de": """Könntest du den Thinking-Lernstil präferieren? 

Diese Personen bevorzugen es mit der Theorie zu beginnen und diese zu Lösung praktischer Aufgaben zu nutzen. Thinking-Lernstil schätzen logisch strukturierte Themen mit klaren Zielen, Ergebnissen und Vorgaben. Diese Lernenden legen Wert auf konkrete Informationen und rationale Grundlagen und treffen Entscheidungen objektiv, basierend auf Fakten, Logik und Prinzipien. 

- Magst du geplante Messungen deines Fortschritts? 
- Freust du dich wenn du Aufgaben abhaken kannst? 
- Magst du faktenbasierte, realistische Beispiele mehr als blumige Erzählungen? 

Da wirst du wahrscheinlich den Thinking-Lernstil mögen!""",
                "en": """Could you be a thinking learner? 

These people prefer to start with theory and use it to solve practical tasks. Thinking learners appreciate logically structured topics with clear goals, outcomes and objectives. These learners value concrete information and rational foundations and make decisions objectively, based on facts, logic and principles. 

- Do you like scheduled measurements of your progress? 
- Are you happy when you can tick off tasks? 
- Do you like fact-based, realistic examples more than flowery stories? 

You'll probably be a thinking learner!""",
            },
            "short_description": {
                "en": "This person prefers: logic, structure, objectives, facts, rationality.",
                "de": "Diese Person setzt auf: Logik, Struktur, Ziele, Fakten, Rationalität.",
            },
        },
    ]
}

localized_title_prompt_output = """System: This is the competence description.\nThis is the learning type description.\nHi
Human: Hello StudyBot.
AI: Hi How are you?
Human: I am good. How about you?"""

localized_title_prompt_output_st_buddy = """System: This is the st description.\nThis is the learning type description.\nHi
Human: Hello StBuddy.
AI: Hi How are you?
Human: I am good. How about you?"""

test_get_topics_data = {
            "topics": [
            {
                "endpoint": "passthrough",
                "title": {
                    "de": "Freier Chat",
                    "en": "Free Chat",
                },
                "short_description": {
                    "de": "Chatte offen mit unserer KI.",
                    "en": "Chat freely with our AI.",
                },
                "long_description": {
                    "de": (
                        "Chatte offen mit unserer KI. Du kannst jede Frage stellen,"
                        " die du möchtest."
                    ),
                    "en": "Chat freely with our AI. You can ask any question you like.",
                },
                "modules": [],
                "type": "basic",
                "features": [
                    "title", "inspirations", "streaming", "summary", "aimodel"
                ],
                "priority": 0,
                "color": '#ea964d',
                "enabled": True
            },
            {
                "endpoint": "citation",
                "title": {
                    "de": "Wissenschaftliches Schreiben",
                    "en": "Scientific Writing",
                },
                "short_description": {
                    "de": "Lerne wissenschaftliche Arbeiten zu schreiben",
                    "en": "Learn how to write scientific papers",
                },
                "long_description": {
                    "de": "Dieses Thema ist veraltet und wird aktuell nicht mehr unterstützt. Dieser Bot hilft dir, wissenschaftliche Arbeiten zu schreiben.",
                    "en": "This is an old topic that is not supported at the moment. This bot will help you learn how to write scientific papers."
                },
                "modules": [
                    {'id': 'Citation', 'title': {'de': 'Citation', 'en': 'Citation'}},
                    {'id': 'Giving_Presentations_And_Scientific_Speaking', 'title': {'de': 'Giving Presentations And Scientific Speaking', 'en': 'Giving Presentations And Scientific Speaking'}},
                    {'id': 'Language_Specifics', 'title': {'de': 'Language Specifics', 'en': 'Language Specifics'}},
                    {'id': 'Language_Style', 'title': {'de': 'Language Style', 'en': 'Language Style'}},
                    {'id': 'Research', 'title': {'de': 'Research', 'en': 'Research'}},
                    {'id': 'Smaller_Texts', 'title': {'de': 'Smaller Texts', 'en': 'Smaller Texts'}},
                    {'id': 'StructureOfAPaper', 'title': {'de': 'StructureOfAPaper', 'en': 'StructureOfAPaper'}},
                    {'id': 'Topic selection', 'title': {'de': 'Topic selection', 'en': 'Topic selection'}},
                    {'id': 'TU_Dresden', 'title': {'de': 'TU Dresden', 'en': 'TU Dresden'}}
                ],
                "type": "basic",
                "features": [
                    "title",
                ],
                "priority": 0,
                "color": '#ea4d79',
                "enabled": True
            },
        ]
        }