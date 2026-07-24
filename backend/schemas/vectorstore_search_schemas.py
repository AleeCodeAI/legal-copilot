from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class SearchResultItem(BaseModel):
    """Represents a single retrieved document from the vector store."""
    model_config = ConfigDict(extra="ignore")
    
    id: str
    content: str
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata dictionary"
    )
    search_type: str = Field(
        description="Search method used ('keyword' or 'semantic')"
    )
    relevance_score: float = Field(description="Cohere reranking relevance score")


class CompleteSearchResponse(BaseModel):
    """Container holding separated search results for internal and external knowledge bases."""

    query: str
    internal_results: List[SearchResultItem] = Field(
        default_factory=list,
        description="Results retrieved from the internal table",
    )
    external_results: List[SearchResultItem] = Field(
        default_factory=list,
        description="Results retrieved from the external table",
    )