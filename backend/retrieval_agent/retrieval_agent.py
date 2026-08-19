from pydantic_ai import Agent, UsageLimits
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from langfuse.decorators import langfuse_context, observe
from typing import List, Optional
import logging
from uuid import UUID

from configs.settings import get_settings
from utils.color import Logger
from prompts.prompt_manager import PromptManager
from schemas import CompleteSearchResponse, RetrievalResult
from observability import RetrievalAgentObservability
from database.vectorstore import VectorStore
from database import insert_retrieval

logging.basicConfig(level=logging.INFO, format="%(message)s")
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
        self.prompt = PromptManager().get_agent_system_prompt()

        self.model = OpenAIChatModel(
            self.settings.openrouter.default_model,
            provider=OpenAIProvider(
                base_url=self.settings.openrouter.base_url,
                api_key=self.settings.openrouter.api_key,
            ),
        )

        self.agent = Agent(
            model=self.model,
            tools=[self._read_chunks_tool],
            output_type=RetrievalResult,
            system_prompt=self.prompt.prompt,
            retries=self.settings.retrieval_agent.max_retries,
        )

        self.vector_store = VectorStore()
        self.obs = RetrievalAgentObservability()

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
            formatted.append(f"Result {i}\nID: {result.id}\n\nPreview:\n{preview}")

        return "\n\n".join(formatted)

    @observe(as_type="span", name="compile_user_input")
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

    @observe(as_type="span", name="read_chunks_tool")
    def _read_chunks_tool(
            self,
            ids: List[str],
            table_type: str = "external",
            include_neighbors: Optional[bool] = False,
        ):
        """
        Retrieve the full contents of one or more document chunks.

        Use this tool after identifying relevant chunks from a search. It expands
        the brief search previews into their complete text so the model can inspect
        the full legal context before answering.

        Args:
            ids: List of one or more unique chunk IDs returned by the search tool.
            table_type: The source database containing the chunks. Must be either
                "external" or "internal".
            include_neighbors: If True, also retrieves the chunks immediately
                before and after each requested chunk to provide additional
                contextual information.

        Returns:
            List[Dict[str, Any]]: A list of retrieved chunk records, including the
            chunk ID, full contents, metadata, and embedding.
        """
        self.log(f"ToolCall: Calling Read Chunks Tool with number of ids: {len(ids)} and table: {table_type}")
        try:
            results = self.vector_store.get_chunks(
                ids=ids,
                table_type=table_type,
                include_neighbors=include_neighbors,
            )
            cleaned_results = []
            for result in results:
                metadata = result.get("metadata") or {}
                cleaned_results.append({
                     "id": result.get("id"),
                     "contents": result.get("contents") or result.get("content"),
                     "headings": metadata.get("headings", [])
                    })

            return cleaned_results
        
        except Exception as e:
            self.log(f"ToolCall: Failed reading chunks with error: {e}")
            langfuse_context.update_current_observation(level="ERROR", status_message=str(e))
            return {"error": f"Failed to retrieve chunks: {str(e)}"}

    @observe(as_type="generation", name="agent_generation")
    async def _agent(self, user_input: str): 
        """
        Executes the PydanticAI agent with the provided user input, returning a 
        strictly validated RetrievalResult. Handles exceptions and logs errors.
        """
        try:
            result = await self.agent.run(
                            user_input,
                            usage_limits=UsageLimits(
                                request_limit=self.settings.retrieval_agent.max_iterations
                            )
                        )
            usage = result.usage
            input_cost, output_cost, total_cost = self.obs.log_generation(usage=usage, 
                                                                          output=result.output,
                                                                          prompt=self.prompt)
            costs = {
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": total_cost
            }
            return result, costs, usage
        
        except Exception as e:
            self.log(f"Agent execution failed: {e}")
            langfuse_context.update_current_observation(level="ERROR", status_message=str(e))
            raise 

    @observe()
    async def run(self, query: str, session_id: UUID) -> RetrievalResult:
        """
        Executes the main asynchronous agentic loop. Performs the initial complete search,
        manages tool calls, tracks token usage limits, and guarantees a strictly validated 
        RetrievalResult on completion. Supports a two-pass retrieval if the first fails.
        """
        self.log(f"Starting execution run for query: '{query}'")

        self.obs.init_agent_trace(
            session_id=str(session_id), 
            query=query, 
            max_iterations=self.settings.retrieval_agent.max_iterations
        )
        
        try:
            search_results = self.vector_store.complete_search(query=query)
            self.log("Initial complete search done!")
            
            user_input = self._user_input(search_results)

            result, costs, usage = await self._agent(user_input)
            
            final_data: RetrievalResult = result.output

            insert_retrieval(
                            execution_id=session_id,
                            pass_number="FIRST ITERATION",
                            sufficient=final_data.sufficient,
                            confidence=final_data.confidence,
                            reasoning=final_data.reasoning,
                            refined_query=final_data.refined_query,
                            selected_chunks=final_data.selected_chunks
                        )
            
            self.log(
                f"First Pass Completed! "
                f"Sufficient: {final_data.sufficient} | "
                f"Requests: {usage.requests} | "
                f"Tokens -> Total: {usage.total_tokens} | "
                f"Cost -> Input: ${costs.get('input_cost', 0)} | Output: ${costs.get('output_cost', 0)} | Total: ${costs.get('total_cost', 0)}"
            )
            
            if final_data.sufficient == "False" and final_data.refined_query:
                self.log(f"Data insufficient. Running second pass with refined query: '{final_data.refined_query}'")
                
                refined_search_results = self.vector_store.complete_search(query=final_data.refined_query)
                self.log("Refined complete search done!")
                
                refined_user_input = self._user_input(refined_search_results)
                
                refined_result, costs, usage = await self._agent(refined_user_input)
                final_data: RetrievalResult = refined_result.output

                insert_retrieval(
                                execution_id=session_id,
                                pass_number="SECOND ITERATION",
                                sufficient=final_data.sufficient,
                                confidence=final_data.confidence,
                                reasoning=final_data.reasoning,
                                refined_query=final_data.refined_query,
                                selected_chunks=final_data.selected_chunks
                                )
                self.log(
                    f"Second Pass Completed! "
                    f"Sufficient: {final_data.sufficient} | "
                    f"Requests: {usage.requests} | "
                    f"Tokens -> Total: {usage.total_tokens} | "
                    f"Cost -> Input: ${costs.get('input_cost', 0)} | Output: ${costs.get('output_cost', 0)} | Total: ${costs.get('total_cost', 0)}"
                )

            self.log(
                f"Final Result -> Sufficient: {final_data.sufficient} | "
                f"Selected Chunks Count: {len(final_data.selected_chunks)} | "
                f"Confidence: {final_data.confidence}"
            )

            self.obs.process_result(final_data)
            return final_data

        except Exception as e:
            self.log(f"Agent failed or hit usage limits: {e}")
            self.log("Returning fallback response.")

            self.obs.process_failure(e)

            return RetrievalResult(
                sufficient="False",
                selected_chunks=[],
                confidence=0.0,
                reasoning=f"Agent failed with error: {str(e)}",
                refined_query=None
            )

if __name__ == "__main__":
    import asyncio
    import uuid
    
    session_id = uuid.uuid4()
    agent = RetrievalAgent()
    query = "How to respond to a three-day notice by the landlord? what happens if done incorrectly"
    result = asyncio.run(agent.run(query=query, session_id=session_id))
    print(result)