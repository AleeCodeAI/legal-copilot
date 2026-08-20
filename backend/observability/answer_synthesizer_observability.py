from langfuse import Langfuse
from langfuse.decorators import langfuse_context
from configs.settings import get_settings
from schemas import SynthesizerResult

class AnswerSynthesizerObservability:
    """Class to handle observability for the Answer Synthesizer using Langfuse."""

    def __init__(self):
        self.settings = get_settings()
        self.langfuse = Langfuse(
            secret_key=self.settings.langfuse.secret_key,
            public_key=self.settings.langfuse.public_key,
            host=self.settings.langfuse.host
        )

    def init_trace(self, session_id: str, query: str):
        """Initializes the trace metadata when the synthesizer run starts."""

        langfuse_context.update_current_trace(
            session_id=session_id,
            name="AnswerSynthesizer_Execution",
            tags=["answer-synthesizer", "Groq", "OpenRouter"],
            input={"user_query": query}
        )

    def log_generation(self, usage, output, prompt, model):
        """
        Logs a generation to Langfuse with token usage and cost information.

        Args:
            usage: The usage object from OpenAI SDK or pydantic-ai
            output: The output of the generation
            prompt: The prompt used for the generation
            model: the model used for generation
        """
        # Safely extract input/output tokens handling both OpenAI SDK and Pydantic-AI formats
        input_tokens = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", 0)
        total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens)

        # Calculate costs
        input_cost = (input_tokens / 1_000_000) * self.settings.openrouter.GPT_OSS_INPUT_PRICE
        output_cost = (output_tokens / 1_000_000) * self.settings.openrouter.GPT_OSS_OUTPUT_PRICE
        total_cost = round(input_cost + output_cost, 6)

        langfuse_context.update_current_observation(
            output=output,
            prompt=prompt,
            model=model,
            usage={
                "input": input_tokens,
                "output": output_tokens,
                "total": total_tokens,
                "unit": "TOKENS",
                "inputCost": input_cost,
                "outputCost": output_cost,
                "totalCost": total_cost,
            }
        )

        return input_cost, output_cost, total_cost

    def process_result(self, result: SynthesizerResult):
        """Logs the final output and dynamically scores it."""

        langfuse_context.update_current_trace(output=result.model_dump())

        if result.answer.answer != None and result.answer != "":
            langfuse_context.score_current_trace(
                name="synthesis-success",
                value=1,
                comment=f"Answer Generated Successfully!"
            )
        else:
            langfuse_context.score_current_trace(
                name="synthesis-success",
                value=0,
                comment=f"Answer couldn't generate!"
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
            name="synthesis-success",
            value=0,
            comment=f"Synthesizer crashed/failed: {error_msg}"
        )

    def flush(self):
        self.langfuse.flush()