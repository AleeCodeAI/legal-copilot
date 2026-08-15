from pydantic import BaseModel, Field, computed_field


class AnswerSynthesizerEvalsSchema(BaseModel):

    faithfulness: float = Field(
        description="A faithfulness score (0-1) indicating the synthesizer answer faithfulness.",
        ge=0,
        le=1,
    )

    completeness: float = Field(
        description="A completeness score (0-1) indicating the synthesizer answer completeness.",
        ge=0,
        le=1,
    )

    source_attribution: float = Field(
        description="A source attribution score (0-1) indicating how well the synthesizer attributed sources.",
        ge=0,
        le=1,
    )

    confidence: float = Field(
        description="A confidence score (0-1) indicating the evaluator's confidence in their assessment.",
        ge=0,
        le=1,
    )

    reasoning: str = Field(
        description="The reasoning behind the evaluation of the answer synthesis."
    )

    @computed_field
    @property
    def overall_score(self) -> float:
        """Average of the three evaluation scores."""

        return round(
            (
                self.faithfulness
                + self.completeness
                + self.source_attribution
            ) / 3,
            2,
        )

    @computed_field
    @property
    def verdict(self) -> str:
        """Overall evaluation verdict."""

        return "GOOD" if self.overall_score >= 0.75 else "BAD"