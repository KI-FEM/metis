from langchain_huggingface import HuggingFaceEmbeddings

from framework.rag.embeddings.base_embedding import BaseEmbedding


class HFEmbedding(BaseEmbedding):
    """HuggingFace embedding model wrapper.

    This class wraps a HuggingFace embedding model for use in document retrieval
    and similarity search.

    Args:
        model_name (str): The name of the HuggingFace model to use.
        model_kwargs (dict): Additional keyword arguments for the model.

    Returns:
        None

    """

    def __init__(self, model_name="Qwen/Qwen3-Embedding-4B", model_kwargs=None) -> None:
        """Initialize the HuggingFace Embedding."""
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs
            or {
                "device": "cpu",
            },
        )
