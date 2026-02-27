from langfuse.client import ChatPromptClient, TextPromptClient
from langfuse.model import Prompt_Chat, Prompt_Text


class PromptPatcher:
    """A helper class that builds a mock that patches Langfuse to return prompts."""

    def __init__(self):
        """Initialize the prompt patcher."""
        self.prompt_clients = []

    def patcher(self):
        """Get the prompt patcher."""
        return self

    def add_prompt(
        self,
        prompt: list[dict[str, str]],
        name: str,
        prompt_type="chat",
        version=1,
        labels=None,
        tags=None
    ):
        """Add a prompt to the patcher."""
        if labels is None:
            labels = ["latest"]
        if tags is None:
            tags = []

        if prompt_type=="chat":
            self.prompt_clients.append(ChatPromptClient(Prompt_Chat(
                prompt=prompt,
                name=name,
                version=version,
                labels=labels,
                tags=tags,
                type=prompt_type)
            ))
        elif prompt_type=="text":
            self.prompt_clients.append(TextPromptClient(Prompt_Text(
                prompt=prompt,
                name=name,
                version=version,
                labels=labels,
                tags=tags,
                type=prompt_type)
            ))
        else:
            raise ValueError("Prompt type not supported.")

        return self

    def add_prompt_client(
        self,
        prompt_client: ChatPromptClient | TextPromptClient
    ):
        """Add a prompt client to the patcher."""
        self.prompt_clients.append(prompt_client)
        return self

    def duplicate(self):
        """Duplicate the currently saved prompts."""
        self.prompt_clients = [*self.prompt_clients, *self.prompt_clients]
        return self

    def patch(self, mocker):
        """Patch the get_prompt function with the previously set prompts."""
        mocker.patch(
            "langfuse.Langfuse.get_prompt", 
            side_effect=self.prompt_clients
        )
