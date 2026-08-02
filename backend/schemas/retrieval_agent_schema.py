from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field

class RetrievalResult(BaseModel):
    "result of retrieval agent"
    sufficient: Literal["True", "False"] = Field(description="a boolean that refers to if enough data is retrieved")
    selected_chunks: List[str] = Field(description="list of chunk IDs by retrieval agent")
    confidence: float = Field(description="confidence score of retrieval agent", ge=0, le=1)
    reasoning: str = Field(description="brief explanation of retrieval agent's decision")
    refined_query: str | None = Field(default=None, description="refined query for next retrieval iteration")