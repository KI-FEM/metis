import sys
from pathlib import Path

from ..base_bot_test import BaseBotTest
from ..data import open_conversation_data
from ..prompt_patcher import PromptPatcher

sys.path.append(str(Path(Path(__file__).parent.parent.parent.parent / "src")))
from framework.chains.passthrough_chain import PassthroughChain


class TestPassthroughBot(BaseBotTest):
    """Test class for the PassthroughBot grouping tests together."""

    def setup_method(self):
        """Setup the bot for testing."""
        self.base_route = "passthrough"

    def test_default_endpoint(self, client):
        """Test '/' endpoint when starting a fresh chat."""
        response = self.post_request("/", self.default_data, client)
        assert response.status_code == 200
        assert response.json() == {
            "messages": [{
                "message": "Welcome! You can freely chat with me here.",
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

    def test_open_conversation(self, client, mocker, fake_llm):
        """Test the open conversation endpoint."""
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            prompt=[{
                "content": "Passthrough bot!", 
                "role": "system"
            }],
            name="passthrough"
        ).patch(mocker)
        response = self.post_request("/message", open_conversation_data, client)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["messages"][0]["message"] == "This is a fake response."

    def test_update_title(self, client, mocker, fake_llm):
        """Test the update title endpoint."""
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            prompt=[{
                "content": "Generate title!", 
                "role": "system"
            }],
            name="title-en"
        ).patch(mocker)
        response = self.post_request("/title", open_conversation_data, client)
        assert response.status_code == 200
        assert response.json() == {
            "title": "This is a fake response."
        }
        
    def test_summarize_chat(self, client, mocker, fake_llm):
        """Test that the summarize chat endpoint returns a summary based on the chat history."""
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            name="competence-summarization-en",
            prompt=[{
                "content": "Summarize pls!", 
                "role": "system"
            }],
        ).patch(mocker)
        
        # Create test data with more messages than MAX_MESSAGES_BEFORE_SUMMARIZATION
        test_data = {
            **open_conversation_data,
            "chat_history": [
                {
                    "message": f"Test message {i}",
                    "sender": "user" if i % 2 == 0 else "assistant",
                    "timestamp": f"2024-03-{str(i).zfill(2)}T10:00:00Z"
                } for i in range(70)  # More than MAX_MESSAGES_BEFORE_SUMMARIZATION
            ]
        }
        
        response = self.post_request("/summarize", test_data, client)
        assert response.status_code == 200
        response_data = response.json()
        
        assert "summary" in response_data
        assert "keep_last_messages_until" in response_data
        assert response_data["summary"] == "This is a fake response."
        assert response_data["keep_last_messages_until"] == 16  # KEEP_LAST_MESSAGES_UNTIL

    def test_chat_uses_summary(self, client, mocker, fake_llm):
        """Test that sending the chat endpoint a list of messages including a summary will use the summary."""
        # Create a spy to track what messages are passed to the LLM
        conversation_spy = mocker.spy(PassthroughChain, 'create_chain')
        mocker.patch("framework.llm.lite_llm.LiteLLM.llm", return_value=fake_llm)
        PromptPatcher().add_prompt(
            prompt=[{
                "content": "You are a helpful assistant.", 
                "role": "system"
            }],
            name="passthrough"
        ).patch(mocker)
        
        # Create test data with a summary in the chat history
        test_data = {
            **open_conversation_data,
            "chat_history": [
                {
                    "message": "Message that should be summarized",
                    "sender": "user",
                    "timestamp": "2024-03-01T09:00:00Z"
                },
                {
                    "message": "Previous conversation summary",
                    "sender": "assistant",
                    "summary": "This is a summary of previous messages",
                    "timestamp": "2024-03-01T10:00:00Z"
                },
                {
                    "message": "New message after summary",
                    "sender": "user",
                    "timestamp": "2024-03-01T10:01:00Z"
                }
            ]
        }
        
        response = self.post_request("/message", test_data, client)
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify the response structure
        assert len(response_data["messages"]) > 0
        assert response_data["messages"][0]["message"] == "This is a fake response."
        
        # Verify that the chain was created with the summarized conversation
        assert conversation_spy.called
        # Get the arguments passed to create_chain
        args, _ = conversation_spy.call_args
        # The prompt template is the second argument to create_chain
        assert len(args) >= 2
        prompt_template = args[2]
        assert prompt_template is not None
        
        # Verify the chat history used in the prompt
        # The conversation history should only include the summary message and the new message
        # not the original message that was summarized
        assert prompt_template.format() == """System: You are a helpful assistant.
AI: This is a summary of previous messages
Human: New message after summary"""
