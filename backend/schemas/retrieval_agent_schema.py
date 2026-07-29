from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field

class RetrievalResult(BaseModel):
    "result of retrieval agent"
    sufficient: Literal["True", "False"] = Field(description="a boolean that refers to if enough data is retrieved")
    selected_chunks: List[str] = Field(description="list of chunk IDs by retrival agent")