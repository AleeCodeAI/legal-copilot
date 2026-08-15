from langfuse import Langfuse
from langfuse.decorators import langfuse_context
from configs.settings import get_settings
from schemas import AnswerSynthesizerEvalsSchema

class SynthesizerEvaluatorObservability:
    """Class to handle observability for the Answer Synthesizer Evaluator using Langfuse."""
    def __init__(self):
        self.settings = get_settings()
        self.langfuse = Langfuse(
            secret_key=self.settings.langfuse.secret_key,
            public_key=self.settings.langfuse.public_key,
            host=self.settings.langfuse.host
        )

    def init_eval_trace(self, session_id: str, query: str):
        """Initializes the trace metadata when evaluating a single query."""
        langfuse_context.update_current_trace(
            session_id=session_id,
            name="Answer_Synthesizer_Evaluation_Run",
            tags=["synthesizer_evaluator", "groq"],
            input={"eval_query": query}
        )

    def log_generation(self, 
                       messages: list, 
                       output: AnswerSynthesizerEvalsSchema, 
                       usage, 
                       model: str,
                       prompt):
        
        """Logs the generation payload and token usage."""
        langfuse_context.update_current_observation(
            input=messages,
            prompt=prompt,
            output=output.model_dump(),
            model=model,
            usage={
                "input": usage.prompt_tokens if usage else 0,
                "output": usage.completion_tokens if usage else 0,
                "total": usage.total_tokens if usage else 0,
                "unit": "TOKENS"
            }
        )

    def process_result(self, result: AnswerSynthesizerEvalsSchema):
        """Logs the final evaluator result and scores the answer synthesis."""
        langfuse_context.update_current_trace(output=result.model_dump())

        # Scoring based on the 'verdict' literal ("GOOD" or "BAD")
        langfuse_context.score_current_trace(
            name="synthesizer-verdict",
            value=1 if result.verdict == "GOOD" else 0,
            comment=f"Verdict: {result.verdict} | Confidence: {result.confidence} | Reasoning: {result.reasoning}"
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
            name="synthesizer-verdict",
            value=0,
            comment=f"Evaluator pipeline crashed: {error_msg}"
        )

    def flush(self):
        self.langfuse.flush()