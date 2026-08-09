from pydantic import BaseModel, Field
from typing import Literal

class RetrievalAgentEvalsSchema(BaseModel):
    """
    Schema for the Retrieval Agent Evals prompt.
    It includes fields for reasoning, sufficiency, and confidence.
    """

    reasoning: str = Field(description="The reasoning behind the evaluation of the search results.")
    sufficient: Literal["True", "False"] = Field(description="Indicates whether the search results were sufficient to answer the question.")
    focused: Literal["True", "False"] = Field(description="indicates whether the search results were focused.")
    confidence: float = Field(description="A confidence score (0-1) indicating the evaluator's confidence in their assessment of the search results.", ge=0, le=1)