from pydantic import BaseModel, Field

class Answer(BaseModel):
    """
    Pydantic Schema of the final response generated for the query.
    """
    answer: str = Field(
        description="The final answer generated to the query"
        )
    reasoning_summary: str = Field(
        description="A concise summary of the reasoning used to support the answer."
    )
