"""Factory for creating ScaDS.AI assistant bots dynamically."""

import logging
import os
from typing import List, Optional

import httpx

from bots.scads.scads_assistant_bot import ScaDSAssistantBot
from framework.api_types.localized_string import LocalizedString

logger = logging.getLogger(__name__)


class ScaDSAssistantFactory:
    """Factory class for creating ScaDS.AI assistant bots.
    
    This factory fetches available assistant models from the ScaDS API
    and creates corresponding bot instances that can be registered
    with the application router.
    """

    # Default descriptions for known assistants
    ASSISTANT_METADATA = {
        "HPC-Buddy": {
            "name": LocalizedString("HPC Buddy", "HPC Buddy"),
            "short_description": LocalizedString(
                "High-Performance Computing assistant",
                "Assistent für Hochleistungsrechnen"
            ),
            "long_description": LocalizedString(
                "I'm the HPC Buddy! I can help you with questions about \
                    High-Performance Computing, cluster usage, \
                    job scheduling, and parallel computing.",
                "Ich bin der HPC Buddy! Ich kann dir bei Fragen \
                    zu Hochleistungsrechnen, Cluster-Nutzung, \
                    Job-Scheduling und parallelem Rechnen helfen."
            ),
        },
        "English-German-Translator": {
            "name": LocalizedString(
                "English-German Translator", 
                "Englisch-Deutsch Übersetzer"
            ),
            "short_description": LocalizedString(
                "Translate between English and German",
                "Übersetzung zwischen Englisch und Deutsch"
            ),
            "long_description": LocalizedString(
                "I can translate text between English and German. \
                    Just send me the text you want to translate!",
                "Ich kann Text zwischen Englisch und Deutsch übersetzen. \
                    Schicke mir einfach den Text, den du übersetzen möchtest!"
            ),
        },
        "ZIH-FAQ-Buddy": {
            "name": LocalizedString("ZIH FAQ Buddy", "ZIH FAQ Buddy"),
            "short_description": LocalizedString(
                "Answer questions about ZIH services",
                "Beantwortet Fragen zu ZIH-Diensten"
            ),
            "long_description": LocalizedString(
                "I can answer frequently asked questions about ZIH \
                    (Center for Information Services and High Performance \
                    Computing) services and resources.",
                "Ich kann häufig gestellte Fragen zu den Diensten und \
                    Ressourcen des ZIH (Zentrum für Informationsdienste \
                    und Hochleistungsrechnen) beantworten."
            ),
        },
        "Text-Simplifier": {
            "name": LocalizedString("Text Simplifier", "Text-Vereinfacher"),
            "short_description": LocalizedString(
                "Simplify complex text",
                "Komplexe Texte vereinfachen"
            ),
            "long_description": LocalizedString(
                "I can help simplify complex or technical text to make it \
                    easier to understand. Just paste the text you want me \
                    to simplify!",
                "Ich kann helfen, komplexe oder technische Texte zu \
                    vereinfachen, damit sie leichter zu verstehen sind. \
                    Füge einfach den Text ein, den ich vereinfachen soll!"
            ),
        },
        "Text-Improver": {
            "name": LocalizedString("Text Improver", "Text-Verbesserer"),
            "short_description": LocalizedString(
                "Improve and polish your text",
                "Verbessere und poliere deinen Text"
            ),
            "long_description": LocalizedString(
                "I can help improve your writing by enhancing clarity, grammar,\
                    and style. Send me the text you'd like me to improve!",
                "Ich kann helfen, dein Schreiben zu verbessern, indem ich \
                    Klarheit, Grammatik und Stil optimiere. Schicke mir den \
                    Text, den du verbessern möchtest!"
            ),
        },
    }

    # Default metadata
    DEFAULT_METADATA = {
        "color": "#63a44b",
        "priority": 0,
    }

    def __init__(self):
        """Initialize the factory."""
        self._cached_bots: Optional[List[ScaDSAssistantBot]] = None
        self._base_url: Optional[str] = None

    def _get_base_url(self) -> str:
        """Get the ScaDS API base URL."""
        if self._base_url is None:
            proxy_url = os.getenv("LITELLM_URL")
            if not proxy_url:
                raise ValueError("LITELLM_URL environment variable is not set.")
            self._base_url = f"{proxy_url.rstrip('/')}/v1/scads-assistants"
        return self._base_url

    async def fetch_available_models(self) -> List[dict]:
        """Fetch available assistant models from the ScaDS API.
        
        Returns:
            List of model dictionaries with 'id' and optional metadata.

        """
        try:
            base_url = self._get_base_url()
            logger.info(f"ScaDSFactory: Fetching models from {base_url}")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(base_url)
                
                if response.status_code != 200:
                    logger.warning(
                        f"ScaDSFactory: Failed to fetch models. "
                        f"Status: {response.status_code}"
                    )
                    return []
                
                data = response.json()
                models = [{"id": key, **value} 
                            if isinstance(value, dict) 
                            else {"id": key} 
                          for key, value in data.items()]
                
                logger.info(
                    f"ScaDSFactory: Found {len(models)} available models: {
                        [m['id'] for m in models]
                    }"
                )
                return models
                
        except Exception as e:
            logger.error(f"ScaDSFactory: Error fetching models: {e}")
            return []

    def _get_metadata_for_model(self, model_id: str) -> dict:
        """Get metadata (name, description, color) for a model.
        
        If the model is known, returns predefined metadata merged with defaults.
        Otherwise, generates generic metadata from the model ID.
        
        Args:
            model_id: The model identifier.
            
        Returns:
            Dictionary with name, short_description, long_description, color, priority.

        """
        # Start with default color and priority
        metadata = {
            "color": self.DEFAULT_METADATA["color"],
            "priority": self.DEFAULT_METADATA["priority"],
        }
        
        if model_id in self.ASSISTANT_METADATA:
            # Merge known assistant metadata with defaults
            metadata.update(self.ASSISTANT_METADATA[model_id])
        else:
            # Generate generic metadata from model ID
            display_name = model_id.replace("-", " ").replace("_", " ").title()
            metadata.update({
                "name": LocalizedString(display_name, display_name),
                "short_description": LocalizedString(
                    f"ScaDS.AI {display_name} assistant",
                    f"ScaDS.AI {display_name} Assistent"
                ),
                "long_description": LocalizedString(
                    f"I am the {display_name} assistant from ScaDS.AI. \
                    How can I help you today?",
                    f"Ich bin der {display_name} Assistent von ScaDS.AI. \
                    Wie kann ich dir heute helfen?"
                ),
            })
        
        return metadata

    def create_bot_from_model(self, model: dict) -> ScaDSAssistantBot:
        """Create a bot instance from model data.
        
        Args:
            model: Model dictionary with at least 'id' key.
            
        Returns:
            Configured ScaDSAssistantBot instance.

        """
        model_id = model.get("id", "unknown")
        metadata = self._get_metadata_for_model(model_id)
        
        bot = ScaDSAssistantBot(
            model_id=model_id,
            name=metadata["name"],
            short_description=metadata["short_description"],
            long_description=metadata["long_description"],
            color=metadata["color"],
            priority=metadata["priority"],
        )
        
        logger.info(
            f"ScaDSFactory: Created bot for '{model_id}' with id '{bot.id}'"
        )
        return bot

    async def create_all_bots(self, use_cache: bool = True) -> List[ScaDSAssistantBot]:
        """Create bot instances for all available ScaDS assistants.
        
        This method also rebuilds the ScadsAssistant enum with the current
        list of assistant IDs for type-safe validation.
        
        Args:
            use_cache: If True, returns cached bots if available.
            
        Returns:
            List of ScaDSAssistantBot instances.

        """
        if use_cache and self._cached_bots is not None:
            logger.info(
                f"ScaDSFactory: Returning {len(self._cached_bots)} cached bots"
            )
            return self._cached_bots
        
        models = await self.fetch_available_models()
        
        if not models:
            logger.warning("ScaDSFactory: No models available, no bots created")
            return []
        
        bots = []
        for model in models:
            try:
                bot = self.create_bot_from_model(model)
                bots.append(bot)
            except Exception as e:
                logger.error(
                    f"ScaDSFactory: Failed to create bot for model "
                    f"'{model.get('id', 'unknown')}': {e}"
                )
        
        self._cached_bots = bots
        logger.info(f"ScaDSFactory: Created {len(bots)} bots total")
        return bots

    def clear_cache(self) -> None:
        """Clear the cached bots to force refresh on next call."""
        self._cached_bots = None
        logger.info("ScaDSFactory: Cache cleared")

    def fetch_available_models_sync(self) -> List[dict]:
        """Fetch available assistant models synchronously.
        
        This is used during application startup when async is not available.
        
        Returns:
            List of model dictionaries with 'id' and optional metadata.

        """
        try:
            base_url = self._get_base_url()
            logger.info(
                f"ScaDSFactory: Fetching models synchronously from {base_url}"
            )
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(base_url)
                
                if response.status_code != 200:
                    logger.warning(
                        f"ScaDSFactory: Failed to fetch models. "
                        f"Status: {response.status_code}"
                    )
                    return []
                
                data = response.json()
                models = [{"id": key, **value} 
                          if isinstance(value, dict) 
                          else {"id": key} 
                          for key, value in data.items()]
                
                logger.info(
                    f"ScaDSFactory: Found {len(models)} available models: {
                            [m['id'] for m in models]
                        }"
                    )
                return models
                
        except Exception as e:
            logger.error(f"ScaDSFactory: Error fetching models: {e}")
            return []

    def create_all_bots_sync(self, use_cache: bool = True) -> List[ScaDSAssistantBot]:
        """Create bot instances synchronously for all available ScaDS assistants.
        
        This is used during application startup when async is not available.
        
        Args:
            use_cache: If True, returns cached bots if available.
            
        Returns:
            List of ScaDSAssistantBot instances.

        """
        if use_cache and self._cached_bots is not None:
            logger.info(f"ScaDSFactory: Returning {len(self._cached_bots)} cached bots")
            return self._cached_bots
        
        models = self.fetch_available_models_sync()
        
        if not models:
            logger.warning("ScaDSFactory: No models available, no bots created")
            return []
        
        bots = []
        for model in models:
            try:
                bot = self.create_bot_from_model(model)
                bots.append(bot)
            except Exception as e:
                logger.error(
                    f"ScaDSFactory: Failed to create bot for model "
                    f"'{model.get('id', 'unknown')}': {e}"
                )
        
        self._cached_bots = bots
        logger.info(f"ScaDSFactory: Created {len(bots)} bots total")
        return bots


# Global factory instance
scads_factory = ScaDSAssistantFactory()


def create_scads_bots_sync() -> List[ScaDSAssistantBot]:
    """Convenience function to create ScaDS bots synchronously.
    
    This function is meant to be called during application startup
    to register all available ScaDS assistant bots.
    
    Returns:
        List of ScaDSAssistantBot instances.

    """
    return scads_factory.create_all_bots_sync()
