import logging
from openai import OpenAI

from schemas import Answer, RetrievalResult
from utils.color import Logger
from prompts.prompt_manager import PromptManager
from configs.settings import get_settings
from chunks_loader import get_chunks


logging.basicConfig(level=logging.INFO, format="%(message)s")


class AnswerSynthesizer(Logger):
    """
    Synthesizes a final legal research answer from retrieved evidence.

    The synthesizer receives the user's query and the chunks selected by the
    retrieval agent, formats the evidence into an LLM-friendly prompt, and
    generates a structured `Answer`. Groq is attempted first, with OpenRouter
    used as a fallback provider if the first call fails.
    """

    name: str = "AnswerSynthesizer"
    color: str = Logger.MAGENTA

    def __init__(self):
        """Initialize LLM clients, configuration, and the synthesizer prompt."""
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

        self.log("AnswerSynthesizer initialized")

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    @staticmethod
    def _format_internal_chunks(internal_chunks) -> str:
        """
        Format internal case records into a structured text representation.
        Args:
            internal_chunks: Retrieved internal case records containing
                case metadata and content.
        Returns:
            A formatted string containing the available internal cases.
        """
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
        """
        Format external legal source chunks into a structured text format.
        Args:
            external_chunks: Retrieved chunks from external legal sources.
        Returns:
            A formatted string containing the available external evidence.
        """
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

    def _user_prompt(
        self,
        query: str,
        retrieval_result: RetrievalResult,
    ) -> str:
        """
        Build the user prompt from the query and selected evidence.

        The selected chunk IDs are loaded and separated into internal cases
        and external legal sources before being formatted for the LLM.

        Args:
            query: The user's original legal research question.
            retrieval_result: Retrieval output containing the selected chunks.

        Returns:
            A formatted user prompt containing the query and retrieved evidence.
        """
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

    def _make_messages(self, user_prompt: str) -> list[dict]:
        """
        Construct the system and user messages sent to the LLM.
        Args:
            user_prompt: Formatted prompt containing the query and evidence.
        Returns:
            A list of chat messages compatible with the OpenAI API.
        """
        return [
            {"role": "system", "content": self.prompt.prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _call_llm(self, messages: list[dict]) -> Answer:
        """
        Generate a structured answer using the configured LLM providers.
        Providers are attempted sequentially. If a provider fails, the next
        provider is used as a fallback. The method raises the last encountered
        exception if all providers fail.

        Args:
            messages: System and user messages for the LLM.
        Returns:
            A parsed `Answer` object generated by the LLM.
        Raises:
            Exception: The last provider error if all providers fail.
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

                self.log("Answer successfully generated")
                return result

            except Exception as e:
                last_error = e
                self.log(f"{provider_name} failed: {e}")

        self.log("All LLM providers failed")
        raise last_error

    # ------------------------------------------------------------------
        # Main Method
    # ------------------------------------------------------------------

    def answer(
        self,
        query: str,
        retrieval_result: RetrievalResult,
    ) -> Answer:
        """
        Generate the final answer for a legal research query.

        Args:
            query: The user's legal research question.
            retrieval_result: Results produced by the retrieval pipeline,
                including the chunks selected as evidence.

        Returns:
            A structured `Answer` containing the synthesized response.

        Raises:
            Exception: If prompt construction, message creation, or all
                configured LLM providers fail.
        """
        try:
            user_prompt = self._user_prompt(
                query=query,
                retrieval_result=retrieval_result,
            )

            messages = self._make_messages(user_prompt=user_prompt)

            result = self._call_llm(messages=messages)
            return result

        except Exception as e:
            self.log(f"Answer synthesis failed: {e}")
            raise

if __name__ == "__main__":
    from pathlib import Path
    import json 

    data = Path(__file__).parents[2] / "data" / "evals_data" / "retrieval_agent_evals_data.json"

    with open(data, "r") as f:
        data = json.load(f)

    data = data[6]
    query = data["query"]
    retrieval_result = RetrievalResult(
        sufficient=data["sufficient"],
        selected_chunks=data["selected_chunks"],
        confidence=0.96,
        reasoning="The two provided chunks are highly relevant and complete to answer the query completely",
        refined_query=None    
        )

    synthesizer = AnswerSynthesizer()
    result = synthesizer.answer(query=query, retrieval_result=retrieval_result)
    print(query)
    print(result.answer)
    print(result.reasoning_summary)