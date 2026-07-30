from pydantic_ai import Agent, UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from tools import search_again_tool, read_chunks_tool 
from configs.settings import get_settings
from utils.color import Logger
from prompts import AGENT_SYSTEM_PROMPT
from schemas import CompleteSearchResponse, RetrievalResult
from database.vectorstore import VectorStore

import asyncio

class RetrievalAgent(Logger):
    """
    An asynchronous agent that orchestrates external search and file-reading tools.
    Leverages PydanticAI to enforce strict output schemas and manage self-healing retries.
    """
    name: str = "RetrievalAgent"
    color: str = Logger.GREEN

    def __init__(self):
        """
        Initializes the RetrievalAgent by loading settings, configuring the OpenRouter 
        model provider, and building the PydanticAI agent with specified tools and retry limits.
        """
        self.settings = get_settings()
        
        self.model = OpenAIChatModel(
            self.settings.openrouter.default_model,
            provider=OpenAIProvider(
                base_url=self.settings.openrouter.base_url,
                api_key=self.settings.openrouter.api_key,
            ),
        )

        self.agent = Agent(
            model=self.model,
            tools=[search_again_tool, read_chunks_tool],
            output_type=RetrievalResult,
            system_prompt=AGENT_SYSTEM_PROMPT,
            retries=self.settings.retrieval_agent.max_retries,
        )

        self.vector_store = VectorStore()

        self.log("RetrievalAgent Initialized with PydanticAI!")

    @staticmethod
    def _format_results(results) -> str:
        """
        Transforms raw vector store or search results into a clean, human-readable 
        string structure designed to maximize the LLM's context comprehension.
        """
        if not results:
            return "No results found."

        formatted = []
        for i, result in enumerate(results, start=1):
            preview = result.metadata.get("preview", "N/A")
            metadata = "\n".join(
                f"- {key}: {value}" for key, value in result.metadata.items() if key != "preview"
            )
            formatted.append(f"Result {i}\nID: {result.id}\n\nPreview:\n{preview}\n\nMetadata:\n{metadata}")

        return "\n\n".join(formatted)

    def _user_input(self, search_results: CompleteSearchResponse) -> str:
        """
        Compiles the primary user prompt by combining the original user query 
        with the freshly formatted internal and external search results.
        """
        return (
            f"Query:\n{search_results.query}\n\n"
            f"External Results:\n{self._format_results(search_results.external_results)}\n\n"
            f"Internal Results:\n{self._format_results(search_results.internal_results)}\n"
        )

    async def run(self, query: str) -> RetrievalResult:
        """
        Executes the main asynchronous agentic loop. Performs the initial complete search,
        manages tool calls, tracks token usage limits, and guarantees a strictly validated 
        RetrievalResult on completion.
        """
        self.log(f"Starting execution run for query: '{query}'")
        
        try:
            search_results = self.vector_store.complete_search(query=query)
            self.log("Complete search done!")
            
            user_input = self._user_input(search_results)

            result = await self.agent.run(
                user_input,
                usage_limits=UsageLimits(
                    request_limit=self.settings.retrieval_agent.max_iterations
                )
            )

            usage = result.usage
            self.log(
                f"Task Completed Successfully! "
                f"Requests: {usage.requests} | "
                f"Tokens -> In: {usage.input_tokens}, Out: {usage.output_tokens}, Total: {usage.total_tokens}"
            )
            
            final_data: RetrievalResult = result.output
            self.log(
                f"Result -> Sufficient: {final_data.sufficient} | "
                f"Selected Chunks Count: {len(final_data.selected_chunks)}"
            )
            print(result.all_messages_json().decode("utf-8"))
            return final_data

        except Exception as e:
            self.log(f"Agent failed or hit usage limits: {e}")
            self.log("Returning fallback response.")
            return RetrievalResult(
                sufficient="False",
                selected_chunks=[]
            )

if __name__ == "__main__":
    agent = RetrievalAgent()
    query = "How to respond to a three-day notice by the landlord? what happens if done incorrectly"
    
    result = asyncio.run(agent.run(query=query))
    print(result)