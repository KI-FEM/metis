import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.chat_models.litellm import ChatLiteLLM
from langchain_core.prompts import (
    BasePromptTemplate,
    ChatPromptTemplate,
    PromptTemplate,
)
from langchain_openai import ChatOpenAI
from langfuse import Langfuse

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.api_types.ai_models import LLMPurpose, PurposeListConfigModel
from framework.api_types.request_format import Message
from framework.config import AI_MODELS
from framework.llm.base_llm import BaseLLM

langfuse = Langfuse()

class LiteLLM(BaseLLM):
    """A class representing the LiteLLM proxy server.
    
    Requires the LITELLM_URL and LITELLM_KEY environment variables to be set.

    Args:
        model_name (str): The name of the model to use. Defaults to "llama-3.3".

    Returns:
        None

    """

    def __init__(
        self,
        model_name=None,
    ) -> None:
        """Initialize the LiteLLM object."""
        super().__init__()
        self.proxy_url = os.getenv("LITELLM_URL")

        if self.proxy_url is None:
            load_dotenv()
            self.proxy_url = os.getenv("LITELLM_URL")

        self.key = os.getenv("LITELLM_KEY")
        if self.proxy_url is None:
            raise ValueError(
                "LITELLM_URL environment variable not found. If not already done, "
                "copy the .env.example file, rename to '.env' and set the URL."
            )

        if not model_name:
            purposes = PurposeListConfigModel.model_validate(AI_MODELS)
            model_default = next(
                (purpose.models[0] for purpose in purposes.purposes
                 if purpose.id == LLMPurpose.OPTIMAL.value),
                None
            )
            self.model_name = model_default
        else:
            self.model_name = model_name


    def get_model_name(self):
        """Get the name of the LLM model."""
        return self.model_name

    def handle_braces(self, message: str) -> str:
        """Switch curly braces of inputs with double curly braces and other way."""
        converted = re.sub(r"{{\s*(\w+)\s*}}", 
                           r"TEMP_OPEN_PLACEHOLDER\g<1>TEMP_CLOSE_PLACEHOLDER",
                           message)
        converted = re.sub(r'(?<!\\)\{', '{{', converted)
        converted = re.sub(r'(?<!\\)\}', '}}', converted)
        converted = re.sub(r"TEMP_OPEN_PLACEHOLDER\s*(\w+)\s*TEMP_CLOSE_PLACEHOLDER", 
                           r"{\g<1>}",
                           converted)
        return converted

    def sanitize_message(self, message: str) -> str:
        """Sanitize a message from the user, replacing dangerous characters."""
        message = re.sub(r"(?<!\\)\\", r"\\", message)
        message = re.sub(r"(?<!\\)\{", r"{{", message)
        message = re.sub(r"(?<!\\)\}", r"}}", message)
        return message

    def get_langfuse_prompt(
        self,
        name: str,
        chat: list[Message] = None,
        label="latest",
        prompt_type="chat"
    ) -> BasePromptTemplate:
        """Get a prompt from langfuse server and convert it to a usable object."""
        # handle chat and text prompts differently
        # chat prompts are a list of messages, while text prompts are a string
        if prompt_type == "chat":
            langfuse_prompt = langfuse.get_prompt(name, type="chat", label=label)
            converted_prompt = []
            added_chat = False

            # walk through all messages in the prompt
            for msg in langfuse_prompt.prompt: 
                # if the message is a user message and the content is {{chat_history}}
                # we should add the chat history to the prompt
                if msg["role"] == "user" and msg['content'] == "{{chat_history}}":
                    if chat is not None:
                        added_chat = True   
                        converted_prompt.extend([
                            {
                                "role": msg.sender.value, 
                                "content": self.sanitize_message(msg.message)
                            } for msg in chat
                        ])
                        chat = None
                # else we add the message to the prompt and also handle the braces
                else:
                    converted_prompt.append({
                        **msg,
                        "content": self.handle_braces(msg["content"]) 
                    })

            # if the chat history was not added before, but there exists one, add it
            if not added_chat and chat is not None:
                converted_prompt.extend([
                    {
                        "role": msg.sender.value, 
                        "content": self.sanitize_message(msg.message) 
                    } for msg in chat
                ])

            # create the LangChain PromptTemplate from the converted prompt
            chat_messages = [
                (msg["role"], msg["content"])
                for msg in converted_prompt
            ]
            chat_prompt = ChatPromptTemplate.from_messages(chat_messages)
            chat_prompt.metadata = {
                "langfuse_prompt": langfuse_prompt
            }
            return chat_prompt
        elif prompt_type == "text":
            langfuse_prompt = langfuse.get_prompt(name, type="text", label=label)
            prompt_str = langfuse_prompt.get_langchain_prompt()
            # create the LangChain PromptTemplate from the prompt string
            return PromptTemplate.from_template(
                prompt_str,
                metadata={"langfuse_prompt": langfuse_prompt}
            )
        else:
            raise ValueError("Prompt type not supported.")

    def set_model_name(self, new_model_name: str) -> None:
        """Set the name of the LLM model, available on the LiteLLM server."""
        self.model_name = new_model_name

    def llm(
        self,
        temperature=0.7,
        max_tokens=None,
        chat_id=None,
        json_mode=False
    ) -> ChatLiteLLM:
        """Create a LangChain Runnable for the LiteLLM API.
        
        The Runnable can be used to call the LiteLLM API and generate a LLM response.
        """
        # possible metadata to add to the request for Langfuse tracing
        # instead, we use Langfuse's CallbackHandler to add the metadata
        # to the request when creating the chain
        metadata = {
            #"generation_name"
            #"generation_id"
            #"trace_id"
            #"trace_user_id"
            #"session_id"
        }
        if chat_id is not None:
            metadata["session_id"] = chat_id

        llm =  ChatLiteLLM(
            model=self.model_name,
            api_base=self.proxy_url,
            api_key=self.key,
            temperature=temperature,
            custom_llm_provider='openai',
            max_tokens=max_tokens,
            max_retries=1, # retries is handled by LiteLLM proxy server
            streaming=True,
            metadata=metadata,
            extra_body={
                "metadata": metadata,
            },
        )

        # if json_mode is True, we bind the LLM to return a JSON object
        # Note: not all LLMs support JSON mode
        if json_mode:
            return llm.bind(response_format={"type": "json_object"})

        return llm

    def llm_chatopenai(
        self,
        temperature=0.7,
        max_tokens=None,
        chat_id=None,
        json_mode=False
    ) -> ChatOpenAI:
        """Create a ChatOpenAI runnable for the LiteLLM API.
        
        Useful for tool-calling, since the ChatLiteLLM does not support tool-calling.
        """
        metadata = {
            #"generation_name"
            #"generation_id"
            #"trace_id"
            #"trace_user_id"
            #"session_id"
        }
        if chat_id is not None:
            metadata["session_id"] = chat_id

        llm =  ChatOpenAI(
            model=self.model_name,
            base_url=self.proxy_url,
            api_key=self.key,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=1,
            streaming=True,
            extra_body={
                "metadata": metadata,
            },
        )
        if json_mode:
            return llm.bind(response_format={"type": "json_object"})
        
        return llm
