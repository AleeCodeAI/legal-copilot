from pydantic import BaseModel, Field

class CompleteSearchEvalsSchema(BaseModel):
    """
    Schema for the Complete Search Evals prompt.
    This schema defines the structure of the prompt used for complete search evaluations.
    It includes fields for reasoning, sufficiency, and confidence.
    """

    reasoning: str = Field(description="The reasoning behind the evaluation of the search results.")
    sufficient: bool = Field(description="Indicates whether the search results were sufficient to answer the question.")
    confidence: float = Field(description="A confidence score (0-1) indicating the evaluator's confidence in their assessment of the search results.", ge=0, le=1)