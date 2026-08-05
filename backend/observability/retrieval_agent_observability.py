from langfuse import Langfuse
from langfuse.decorators import langfuse_context
from configs.settings import get_settings
from schemas import RetrievalResult

class RetrievalAgentObservability:
    """Class to handle observability for the Retrieval Agent using Langfuse."""

    def __init__(self):
        self.settings = get_settings()
        self.langfuse = Langfuse(
            secret_key=self.settings.langfuse.secret_key,
            public_key=self.settings.langfuse.public_key,
            host=self.settings.langfuse.host
        )

    def init_agent_trace(self, session_id: str, query: str, max_iterations: int):
        """Initializes the trace metadata when the agent run starts."""

        langfuse_context.update_current_trace(
            session_id=session_id,
            name="RetrievalAgent_Execution",
            tags=["retrieval-agent", "pydantic-ai"],
            input={"user_query": query},
            metadata={"max_iterations": max_iterations}
        )

    def log_generation(self, usage, output, prompt):
        """
        Logs a generation to Langfuse with token usage and cost information.

        Args:
            usage: The usage object from pydantic-ai
            output: The output of the generation
            prompt: The prompt used for the generation
        """

        input_cost = (usage.input_tokens / 1_000_000) * self.settings.openrouter.GPT_OSS_INPUT_PRICE
        output_cost = (usage.output_tokens / 1_000_000) * self.settings.openrouter.GPT_OSS_OUTPUT_PRICE
        total_cost = round(input_cost + output_cost, 6)

        langfuse_context.update_current_observation(
            output=output,
            prompt=prompt,
            model=self.settings.openrouter.default_model,
            usage={
                "input": usage.input_tokens,
                "output": usage.output_tokens,
                "total": usage.total_tokens,
                "unit": "TOKENS",
                "inputCost": input_cost,
                "outputCost": output_cost,
                "totalCost": total_cost,
            },
            metadata={
                "requests": getattr(usage, "requests", None),
                "max_iterations": self.settings.retrieval_agent.max_iterations
                },
        )

        return input_cost, output_cost, total_cost

    def process_result(self, result: RetrievalResult):
        """Logs the final Pydantic model as output and dynamically scores it."""

        langfuse_context.update_current_trace(output=result.model_dump())

        if result.sufficient == "True":
            langfuse_context.score_current_trace(
                name="retrieval-success",
                value=1,
                comment=f"Sufficient. Confidence: {result.confidence} | Chunks: {len(result.selected_chunks)}"
            )
        else:
            langfuse_context.score_current_trace(
                name="retrieval-success",
                value=0,
                comment=f"Insufficient. Reasoning: {result.reasoning}"
            )

    def process_failure(self, error: Exception):
        """Logs exceptions and scores the trace as a failure."""
        error_msg = str(error)
        
        langfuse_context.update_current_observation(
            level="ERROR", 
            status_message=error_msg
        )
        langfuse_context.update_current_trace(
            metadata={"error_type": type(error).__name__, "error_details": error_msg}
        )

        langfuse_context.score_current_trace(
            name="retrieval-success",
            value=0,
            comment=f"Agent crashed/failed: {error_msg}"
        )

    def flush(self):
        self.langfuse.flush()