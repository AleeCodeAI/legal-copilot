from langfuse import Langfuse
from langfuse.decorators import langfuse_context
from configs.settings import get_settings
from schemas import RetrievalAgentEvalsSchema

class AgentEvaluatorObservability:
    """Class to handle observability for the Retrieval Evaluator using Langfuse."""
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
            name="Retrieval_Evaluation_Run",
            tags=["evaluator", "groq"],
            input={"eval_query": query}
        )

    def log_generation(self, 
                       messages: list, 
                       output: RetrievalAgentEvalsSchema, 
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

    def process_result(self, result: RetrievalAgentEvalsSchema):
        """Logs the final evaluator result and scores the retrieval."""
        langfuse_context.update_current_trace(output=result.model_dump())

        langfuse_context.score_current_trace(
            name="retrieval-sufficient",
            value=1 if result.sufficient else 0,
            comment=f"Focused: {result.focused} | Confidence: {result.confidence} | Reasoning: {result.reasoning}"
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
            name="retrieval-sufficient",
            value=0,
            comment=f"Evaluator pipeline crashed: {error_msg}"
        )

    def flush(self):
        self.langfuse.flush()