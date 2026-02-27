from typing import Any, List, TypedDict


class VectorDBConfig(TypedDict):
    """Configuration for the vector database."""

    module_db: str
    additional_args: List[Any]
