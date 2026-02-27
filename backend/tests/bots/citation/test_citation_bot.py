import sys
from pathlib import Path

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSerializable

from ..base_bot_test import BaseBotTest
from ..data import open_conversation_data
from ..prompt_patcher import PromptPatcher

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))
from framework.api_types.learning_type import LearningTypes
from framework.api_types.locale_type import LocaleType
from framework.api_types.request_format import Message, Sender


class TestCitationBot(BaseBotTest):
    """Test class for the CitationBot grouping tests together."""

    def setup_method(self):
        """Setup the bot for testing."""
        self.base_route = "citation"

    def test_default_endpoint(self, client):
        """Test '/' endpoint when starting a fresh chat.

        It sends a POST request to '/' with an empty JSON payload.
        This should return a welcome message and the option to select a learning type.
        """
        response = self.post_request(
            "/", 
            self.default_data, 
            client)
        assert response.status_code == 200
        assert response.json() == {
            "messages": [{
                "message": (
                    "Welcome back 👋 You have previously selected the learning type"
                    " Feeling.\n\nYou can change your learning "
                    "type at any time by clicking the dropdown at the top of the "
                    "window."
                ),
                "sender": "assistant",
                'buttons': [
                    {
                        'callback': {
                            'data': {},
                            'endpoint': 'select_topic'
                            }, 
                        'chat_message': 'Start', 
                        'label': 'Start', 
                        'store': {}
                    }
                ],
                "meta_information": {
                    "sources": None,
                    "llm_model": None,
                    'citations': None,
                },
                "thoughts": None,
            }],
            "storage": {},
            "instructions": [],
        }

    def test_startchat_previously_learned_wrong_learning_type(self, client):
        """Test '/' endpoint when starting a chat with a wrong learning type."""
        response = self.post_request("/", {"learning_type_id": "asdf"}, client)
        assert response.status_code == 422

    def test_startchat_previously_learned_module(self, client):
        """Test '/startchat' endpoint with a selected learning type and module.

        It sends a POST request to '/startchat' with a JSON payload containing the
        previously learned learning type and module. This should return a welcome back
        message and the option to continue with the module or change the learning type.
        """
        response = self.post_request(
            "/",
            {
                **self.default_data,
                "storage": {
                    "selected_module": "Research",
                    "selected_topic": "Scientific work"
                },
            },
            client,
        )
        assert response.status_code == 200
        assert response.json() == {
            "messages": [{
                "message": (
                    "Welcome back 👋 You previously worked on the module "
                    "**Research**. \n"
                    "Do you want to continue with this module?"
                ),
                "sender": "assistant",
                "buttons": [
                    {
                        "chat_message": "Yes", 
                        "label": "Yes", 
                        "callback": {
                            "data": {"selected_module": "Research"}, 
                            "endpoint": "select_submodule"
                        },
                        "store": {}
                    },
                    {
                        "chat_message": "Change", 
                        "label": "Change", 
                        "callback": {
                            "data": {}, 
                            "endpoint": "select_topic"
                        },
                        "store": {}
                    },
                ],
                "meta_information": {
                    "sources": None,
                    "llm_model": None,
                    'citations': None,
                },
                "thoughts": None,
            }],
            "storage": {},
            "instructions": [],
        }

    def test_update_title(self, client, mocker, fake_llm):
        """Test the update title endpoint."""
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            prompt=[{
                "content": "Generate title!", 
                "role": "system"
            }],
            name="title-en",
            prompt_type="chat"
        ).patch(mocker)

        response = self.post_request("/title", open_conversation_data, client)
        assert response.status_code == 200
        assert response.json() == {
            "title": "This is a fake response."
        }

    def test_select_topic(self, client):
        """Test '/select_topic' endpoint when selecting a topic.

        It sends a POST request to '/select_topic' with a JSON payload containing
        the selected topic. This should return a message to select a topic.
        """
        response = self.post_request(
            "/select_topic", self.default_data, client
        )
        assert response.status_code == 200
        assert response.json() == {
            "messages": [{
                "message": (
                    "You selected learning type **Feeling**. I will adapt my teaching "
                    "style to your needs 😊 Please select a topic you want to learn "
                    "about."
                ),
                "sender": "assistant",
                "buttons": [
                    {
                        "chat_message": "Scientific work",
                        "label": "Scientific work",
                        "callback": {
                            "endpoint": "select_module",
                            "data": {"selected_topic": "Scientific work"}
                        },
                        "store": {"selected_topic": "Scientific work"}
                    }
                ],
                "meta_information": {
                    "sources": None,
                    'citations': None,
                    "llm_model": None,
                },
                "thoughts": None,
            }],
            "storage": {},
            "instructions": [],
        }

    def test_select_module(self, client):
        """Test method for the '/select_module' endpoint when selecting a module.

        It sends a POST request to '/select_module' with a JSON payload containing
        the selected module. This should return a message to select a module.
        """
        response = self.post_request(
            "/select_module",
            {
                **self.default_data, 
                "storage": {
                    "selected_topic": "Scientific work"
                }
            },
            client,
        )
        assert response.status_code == 200
        assert response.json() == {
            "messages": [{
                "message": (
                    "You selected the topic **Scientific work**. Next, select a module."
                ),
                "sender": "assistant",
                "buttons": [
                    {
                        "chat_message": "Citation",
                        "label": "Citation",
                        "callback": {
                            "endpoint": "select_submodule",
                            "data": {"selected_module": "Citation"}
                        },
                        "store": {"selected_module": "Citation"}
                    },
                    {
                        "chat_message": "Giving Presentations And Scientific Speaking",
                        "label": "Giving Presentations And Scientific Speaking",
                        "callback": {
                            "endpoint": "select_submodule",
                            "data": {"selected_module": "Giving_Presentations_And_Scientific_Speaking"}
                        },
                        "store": {"selected_module": "Giving_Presentations_And_Scientific_Speaking"}
                    },
                    {
                        "chat_message": "Language Specifics",
                        "label": "Language Specifics",
                        "callback": {
                            "endpoint": "select_submodule",
                            "data": {"selected_module": "Language_Specifics"}
                        },
                        "store": {"selected_module": "Language_Specifics"}
                    },
                    {
                        "chat_message": "Language Style",
                        "label": "Language Style",
                        "callback": {
                            "endpoint": "select_submodule",
                            "data": {"selected_module": "Language_Style"}
                        },
                        "store": {"selected_module": "Language_Style"}
                    },
                    {
                        "chat_message": "Research",
                        "label": "Research",
                        "callback": {
                            "endpoint": "select_submodule",
                            "data": {"selected_module": "Research"}
                        },
                        "store": {"selected_module": "Research"}
                    },
                    {
                        "chat_message": "Smaller Texts",
                        "label": "Smaller Texts",
                        "callback": {
                            "endpoint": "select_submodule",
                            "data": {"selected_module": "Smaller_Texts"}
                        },
                        "store": {"selected_module": "Smaller_Texts"}
                    },
                    {
                        "chat_message": "StructureOfAPaper",
                        "label": "StructureOfAPaper",
                        "callback": {
                            "endpoint": "select_submodule",
                            "data": {"selected_module": "StructureOfAPaper"}
                        },
                        "store": {"selected_module": "StructureOfAPaper"}
                    },
                    {
                        "chat_message": "Topic selection",
                        "label": "Topic selection",
                        "callback": {
                            "endpoint": "select_submodule",
                            "data": {"selected_module": "Topic selection"}
                        },
                        "store": {"selected_module": "Topic selection"}
                    },
                    {
                        "chat_message": "TU Dresden",
                        "label": "TU Dresden",
                        "callback": {
                            "endpoint": "select_submodule",
                            "data": {"selected_module": "TU_Dresden"}
                        },
                        "store": {"selected_module": "TU_Dresden"}
                    }
                ],
                "meta_information": {
                    "sources": None,
                    "llm_model": None,
                    'citations': None,
                },
                "thoughts": None,
            }],
            "storage": {},
            "instructions": [],
        }

    def test_select_submodule(self, client):
        """Test '/select_submodule' endpoint when selecting a submodule.

        It sends a POST request to '/select_submodule' with a JSON payload containing
        the selected submodule. This should return a message to start the submodule.
        """
        response = self.post_request(
            "/select_submodule",
            {
                **self.default_data,
                "storage": {
                    "selected_module": "Language_Style",
                    "selected_topic": "Scientific work"
                },
            },
            client,
        )
        assert response.status_code == 200
        assert response.json() == {
            "messages": [{
                "message": (
                    "You selected the module *Language_Style*. You can now ask your "
                    "own questions or start with one of the following questions: \n\n"
                    "How to speak in a scientific context?\nWhat are tips for improving"
                    " language style?"
                ),
                "sender": "assistant",
                "buttons": [],
                "meta_information": {
                    "sources": None,
                    'citations': None,
                    "llm_model": None,
                },
                "thoughts": None,
            }],
            "storage": {},
            "instructions": [],
        }

    def patch_create_chain(self, mocker):
        """Patch the create_chain function with the previously set prompts."""
        PromptPatcher().add_prompt(
            prompt=[
                {
                    "content": "{{citation_role}}\n{{learning_type_description}}\nHi", 
                    "role": "system"
                }
            ],
            name="citation-chat-en",
        ).add_prompt(
            prompt="This is the citation description.",
            name="citation-description-en",
            prompt_type="text"
        ).add_prompt(
            prompt="This is the learning type description.",
            name="learning_type_description-feeling-en",
            prompt_type="text"
        ).patch(mocker)

    def test_open_conversation(self, client, mocker, fake_llm):
        """Test method for the '/message' endpoint when sending a message.

        It sends a POST request to '/message' with a JSON payload containing a message.
        This should return a response message.
        """
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        self.patch_create_chain(mocker)
        response = self.post_request(
            "/message",
            {
                **open_conversation_data,
                "storage": {"selected_module": "Research", 
                            "selected_topic": "Scientific work"},
            },
            client,
        )
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"][0]["message"] == "This is a fake response."
        assert len(response_data["messages"][0]["meta_information"]["sources"]) == 4

    def test_update_chain(self, mocker, monkeypatch):
        """Test the update_chain method."""
        from bots.citation.citation_bot import load_module_db, update_chain
        monkeypatch.setenv("LITELLM_URL", "some_url")
        monkeypatch.setenv("LITELLM_KEY", "some_key")
        chat = [
            Message(message="Hi How are you?", sender=Sender.ASSISTANT),
            Message(message="I am good. How about you?", sender=Sender.USER)
        ]
        learning_type = LearningTypes.FEELING.value
        
        self.patch_create_chain(mocker)
        chain = update_chain(learning_type, chat)
        assert isinstance(chain, RunnableSerializable)
        vector_db = load_module_db("citation", LocaleType.EN)
        docs = vector_db.similarity_search("citation", k=1)
        assert len(docs) == 1
        