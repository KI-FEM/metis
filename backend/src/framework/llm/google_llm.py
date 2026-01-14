import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.llm.base_llm import BaseLLM


class GoogleLLM(BaseLLM):
    """A class representing the Gemini LLMs.

    Requires the GOOGLE_API_KEY environment variables to be set.

    Args:
        model_name (str): The name of the model to use.

    Returns:
        None

    """

    def __init__(
        self,
        model_name=None,
    ) -> None:
        """Initialize the GoogleLLM object."""
        super().__init__()

        load_dotenv()

        if not model_name:
            raise ValueError(
                "Model name must be provided. If not already done, "
                "copy the .env.example file, rename to '.env' and set the model name."
            )
        else:
            self.model_name = model_name
            
    def get_model_name(self):
        """Get the name of the LLM model."""
        return self.model_name

    def llm(
        self,
        temperature=0.7,
        max_tokens=None,
        chat_id=None,
    ) -> ChatGoogleGenerativeAI:
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

        llm =  ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return llm
