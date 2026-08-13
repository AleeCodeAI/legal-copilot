import logging
from openai import OpenAI

from schemas import Answer, RetrievalResult
from utils.color import Logger
from prompts.prompt_manager import PromptManager
from configs.settings import get_settings
from .chunks_loader import get_chunks
from observability import AnswerSynthesizerObservability
from langfuse.decorators import observe, langfuse_context

logging.basicConfig(level=logging.INFO, format="%(message)s")


class AnswerSynthesizer(Logger):
    """
    Synthesizes a final legal research answer from retrieved evidence.
    """

    name: str = "AnswerSynthesizer"
    color: str = Logger.MAGENTA

    def __init__(self):
        """Initialize LLM clients, configuration, and observability context."""
        self.log("Initializing AnswerSynthesizer...")

        self.settings = get_settings()
        self.prompt = PromptManager().get_answer_synthesizer_prompt()

        self.openrouter = OpenAI(
            api_key=self.settings.openrouter.api_key,
            base_url=self.settings.openrouter.base_url,
        )
        self.groq = OpenAI(
            api_key=self.settings.groq.api_key,
            base_url=self.settings.groq.base_url,
        )

        self.gpt_oss_model = self.settings.openrouter.default_model

        self.obs = AnswerSynthesizerObservability()

        self.log("AnswerSynthesizer initialized")

    # ------------------------------------------------------------------
    # Internal Methods wrapped with Spans
    # ------------------------------------------------------------------

    @staticmethod
    def _format_internal_chunks(internal_chunks) -> str:
        if not internal_chunks:
            return "No internal cases provided."

        formatted = []
        for i, chunk in enumerate(internal_chunks, start=1):
            formatted.append(
                f"Case: {i}\n"
                f"Case ID: {chunk['case_id']}\n"
                f"Case Content: {chunk['content']}\n"
                f"Case Attorneys: {chunk['attorneys']}\n"
                f"Case Date: {chunk['date']}"
            )

        return "\n\n".join(formatted)

    @staticmethod
    def _format_external_chunks(external_chunks) -> str:
        if not external_chunks:
            return "No external sources provided."

        formatted = []
        for i, chunk in enumerate(external_chunks, start=1):
            formatted.append(
                f"Chunk: {i}\n"
                f"Chunk Content: {chunk['content']}\n"
                f"Chunk Headings: {chunk['headings']}\n"
                f"Chunk Page No: {chunk['page_number']}"
            )

        return "\n\n".join(formatted)

    @observe(name="prompt_formatting", as_type="span")
    def _user_prompt(
        self,
        query: str,
        retrieval_result: RetrievalResult,
    ) -> str:
        """Constructs prompt and records it as a span."""
        internal_chunks, external_chunks = get_chunks(
            ids=retrieval_result.selected_chunks
        )

        return (
            f"QUERY:\n{query}\n\n"
            f"EXTERNAL CHUNKS:\n"
            f"{self._format_external_chunks(external_chunks)}\n\n"
            f"INTERNAL CASES:\n"
            f"{self._format_internal_chunks(internal_chunks)}"
        )

    @observe(name="construct_messages", as_type="span")
    def _make_messages(self, user_prompt: str) -> list[dict]:
        return [
            {"role": "system", "content": self.prompt.prompt},
            {"role": "user", "content": user_prompt},
        ]

    @observe(name="synthesizer_generation", as_type="generation")
    def _call_llm(self, messages: list[dict], user_prompt: str) -> Answer:
        """
        Executes the LLM request and logs generation metrics via observability.
        """
        self.log("Calling LLM providers for answer synthesis...")

        providers = [
            ("Groq", self.groq, self.gpt_oss_model),
            ("OpenRouter", self.openrouter, self.gpt_oss_model),
        ]

        last_error = None

        for provider_name, client, model in providers:
            try:
                self.log(f"Trying LLM provider: {provider_name}")

                raw = client.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=Answer,
                    temperature=0.3,
                )

                result = raw.choices[0].message.parsed
                
                if hasattr(raw, "usage") and raw.usage:
                    self.obs.log_generation(
                        usage=raw.usage,
                        output=result.model_dump(),
                        prompt=self.prompt,
                        model=self.gpt_oss_model
                    )

                self.log("Answer successfully generated")
                return result

            except Exception as e:
                last_error = e
                self.log(f"{provider_name} failed: {e}")

        self.log("All LLM providers failed")
        raise last_error

    # ------------------------------------------------------------------
    # Main Execution Method 
    # ------------------------------------------------------------------

    @observe(name="AnswerSynthesizer_Execution")
    def answer(
        self,
        query: str,
        retrieval_result: RetrievalResult,
        session_id: str = "default_session"
    ) -> Answer:
        """
        Main pipeline entry point. Initializes traces, executes spans, and handles logging.
        """
        # 1. Initialize trace
        self.obs.init_trace(
            session_id=session_id, 
            query=query
        )

        try:
            # 2. Build Prompt (Span 1)
            user_prompt = self._user_prompt(
                query=query,
                retrieval_result=retrieval_result,
            )

            # 3. Construct Messages (Span 2)
            messages = self._make_messages(user_prompt=user_prompt)

            # 4. Invoke LLM (Generation Step)
            result = self._call_llm(messages=messages, user_prompt=user_prompt)

            # 5. Score output success
            self.obs.process_result(result)
            return result

        except Exception as e:
            self.log(f"Answer synthesis failed: {e}")
            self.obs.process_failure(e)
            raise
        finally:
            self.obs.flush()


if __name__ == "__main__":
    from pathlib import Path
    import json 

    data_path = Path(__file__).parents[2] / "data" / "evals_data" / "retrieval_agent_evals_data.json"

    if data_path.exists():
        with open(data_path, "r") as f:
            data = json.load(f)

        data = data[8]
        query = data["query"]
        retrieval_result = RetrievalResult(
            sufficient=data["sufficient"],
            selected_chunks=data["selected_chunks"],
            confidence=0.96,
            reasoning="The two provided chunks are highly relevant and complete to answer the query completely",
            refined_query=None    
        )

        synthesizer = AnswerSynthesizer()
        result = synthesizer.answer(query=query, retrieval_result=retrieval_result, session_id="test_session_123")
        print("Query:", query)
        print("Answer:", result.answer)
        print("Reasoning:", result.reasoning_summary)