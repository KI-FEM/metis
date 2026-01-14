"""ScaDS Assistant Bot - A proxy bot for ScaDS.AI assistants."""

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Union

from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

sys.path.append(str(Path(__file__).parent.parent.parent))
from bots.base_bot import BaseBot, TopicType
from framework.api_types.localized_string import LocalizedString
from framework.api_types.module import Module, Skill
from framework.api_types.request_format import MessageType, RequestModel
from framework.api_types.response_format import (
    MetaInformation,
    Response,
)

logger = logging.getLogger(__name__)


class ScaDSAssistantBot(BaseBot):
    """A bot that proxies requests to a ScaDS.AI assistant.
    
    This bot acts as a simple passthrough to external ScaDS.AI assistants,
    forwarding user messages and returning the assistant's responses.
    """

    def __init__(
        self,
        model_id: str,
        name: LocalizedString,
        short_description: LocalizedString,
        long_description: LocalizedString,
        color: str = "#2969e8",
        priority: int = 0,
    ) -> None:
        """Initialize the ScaDS Assistant Bot.
        
        Args:
            model_id: The unique identifier for the ScaDS assistant model.
            name: Localized display name for the bot.
            short_description: Localized short description.
            long_description: Localized detailed description.
            color: Hex color code for the bot's UI representation.
            priority: Display priority (higher = shown first).

        """
        # Create a safe identifier from the model_id
        # Replace special characters to make it URL-safe
        safe_id = f"scads_{model_id.lower().replace('-', '_').replace(' ', '_')}"
        
        super().__init__(
            identifier=safe_id,
            name=name,
            short_description=short_description,
            long_description=long_description,
            embeddings=None,
            bot_type=TopicType.BASIC,
            priority=priority,
            optional=True,
            enabled=True,
            color=color,
            avatar=None,
            tag="ScaDS.AI",
        )
        
        self.model_id = model_id
        self._base_url = None
        self._api_key = None

    def _get_scads_config(self) -> tuple[str, Optional[str]]:
        """Get the ScaDS API configuration.
        
        Returns:
            Tuple of (base_url, api_key).

        """
        if self._base_url is None:
            proxy_url = os.getenv("LITELLM_URL")
            if not proxy_url:
                raise ValueError("LITELLM_URL environment variable is not set.")
            self._base_url = f"{proxy_url.rstrip('/')}/v1/scads-assistants"
            self._api_key = os.getenv("LITELLM_KEY", "")
        return self._base_url, self._api_key

    def get_modules(self) -> List[Union[Module, Skill]]:
        """Return empty list - ScaDS assistants don't have modules."""
        return []

    async def init_chat(self, request: RequestModel) -> Response | StreamingResponse:
        """Initialize the chat with a greeting message."""
        logger.info(f"ScaDSAssistantBot ({self.model_id}): Initializing chat")
        
        locale = request.locale()
        greeting = self.long_description.get(locale)
        
        response = Response.from_message(greeting)
        response.messages[0].meta_information = MetaInformation(
            llm_model=self.model_id,
        )
        return response

    async def chat_invoke(self, request: RequestModel) -> Response | StreamingResponse:
        """Process a chat message by forwarding to the ScaDS assistant."""
        logger.info(f"ScaDSAssistantBot ({self.model_id}): Processing chat request")
        
        try:
            base_url, api_key = self._get_scads_config()
        except ValueError as e:
            logger.error(
                f"ScaDSAssistantBot ({self.model_id}): Configuration error: {e}"
            )
            return Response.from_message(f"Configuration Error: {e}")

        # Get the last user message
        messages = request.chat_history
        last_message = next(
            (msg.content for msg in reversed(messages) if msg.type == MessageType.USER),
            "No user message found",
        )
        
        logger.info(f"ScaDSAssistantBot ({self.model_id}): Sending to model")
        
        try:
            client = AsyncOpenAI(base_url=base_url, api_key=api_key)
            response = await client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": last_message}]
            )
            
            content = response.choices[0].message.content or ""
            logger.info(f"ScaDSAssistantBot ({self.model_id}): Received response")
            
            result = Response.from_message(content)
            result.messages[0].meta_information = MetaInformation(
                llm_model=self.model_id,
            )
            return result
            
        except Exception as e:
            logger.error(f"ScaDSAssistantBot ({self.model_id}): Error: {e}")
            return Response.from_message(f"Error communicating with assistant: {e}")
