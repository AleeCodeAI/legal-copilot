from pathlib import Path 
from database.vectorstore import VectorStore
from .report_generator import generate_markdown_report
from configs.settings import get_settings
from prompts.prompt_manager import PromptManager
from schemas import CompleteSearchEvalsSchema, CompleteSearchResponse
from openai import OpenAI
from utils.color import Logger
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

class CompleteSearchEvals(Logger):
    """
    A class for evaluating complete search functionality.
    """
    name: str = "CompleteSearchEvals"
    color: str = Logger.YELLOW

    def __init__(self):
        self.store = VectorStore()
        self.settings = get_settings()
        self.prompt = PromptManager().get_complete_search_evals().prompt

        self.client = OpenAI(api_key=self.settings.openrouter.api_key,
                             base_url=self.settings.openrouter.base_url)

        self.evals_data = Path(__file__).parents[3] / "data" / "evals_data" / "complete_search_evals_data.json"
        self.execution_result = Path(__file__).parent / "results" / "complete_search_execution_results.json"
        self.evals_report = Path(__file__).parent / "results" / "evals_report.md"

        self.log("CompleteSearchEvals initialized successfully.")

    def _load_evals_data(self):
        """
        Load evaluation data from the JSON file.
        """
        try:
            with open(self.evals_data, 'r') as file:
                data = json.load(file)
            self.log("Evaluation data loaded successfully.")
            return data
        except Exception as e:
            self.log(f"Error loading evaluation data: {e}")
            raise

    def _save_execution_results(self, results: list[dict]):
        """
        Save execution results to a JSON file.
        """
        try:
            with open(self.execution_result, 'w') as file:
                json.dump(results, file, indent=4)
            self.log("Execution results saved successfully.")
        except Exception as e:
            self.log(f"Error saving execution results: {e}")
            raise

    def _save_markdown_report(self, report):
        """
        Save the generated Markdown report to a file.
        """
        try:
            with open(self.evals_report, "w", encoding="utf-8") as f:
                f.write(report)
            self.log(f"Markdown report saved to {self.evals_report}")
        except Exception as e:
            self.log(f"Error saving Markdown report: {e}")
            raise

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
            headings = result.metadata.get("headings", "N/A")
            formatted.append(f"Result {i}\n ID: {result.id}\n Chunk Content:\n{result.content}\n Headings:\n{headings}")
    
        return "\n\n".join(formatted)

    def _user_input(self, search_results: CompleteSearchResponse) -> str:
        """
        Compiles the primary user prompt by combining the original user query 
        wit the freshly formatted internal and external search results.
            """
        return (
                f"Query:\n{search_results.query}\n\n"
                f"External Results:\n{self._format_results(search_results.external_results)}\n\n"
                f"Internal Results:\n{self._format_results(search_results.internal_results)}\n"
            )

    def _make_messages(self, user_input: str) -> list[dict]:
        """
        Constructs the message structure for the LLM, including system and user messages.
        """
        return [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": user_input}
        ]

    def _call_llm(self, messages: list[dict]) -> CompleteSearchEvalsSchema:
        """
        Calls the LLM with retries and returns the response.
        """
        last_exception = None

        for attempt in range(1, self.settings.groq.max_retries + 1):
            try:
                response = self.client.chat.completions.parse(
                    model=self.settings.groq.default_model,
                    messages=messages,
                    temperature=self.settings.groq.temperature,
                    response_format=CompleteSearchEvalsSchema
                )
                result: CompleteSearchEvalsSchema = response.choices[0].message.parsed
                return result

            except Exception as e:
                last_exception = e
                self.log(
                    f"LLM call failed (attempt {attempt}/{self.settings.groq.max_retries}): {e}"
                )

                if attempt < self.settings.groq.max_retries:
                    time.sleep(1)  

        raise last_exception

    def evaluate(self):
        """
        Evaluate the complete search functionality.
        """
        try:
            evals_data = self._load_evals_data()
            if evals_data is None:
                self.log("No evaluation data to process.")
                return None

            execution_results = []

            for item in evals_data:
                query = item.get("query")
                self.log(f"QUERY: {item.get("id")}")
                search_results = self.store.complete_search(query)
                self.log(f"Search Done for Query: {query}")

                user_input = self._user_input(search_results=search_results)
                self.log("User input made for search results")

                messages = self._make_messages(user_input=user_input)
                self.log("Messages made for llm call")

                result = self._call_llm(messages)
                self.log(f"Evaluation result is generated with suffcient: {result.sufficient} and confidence: {result.confidence}")

                execution_result = {
                    "query": query,
                    "sufficient": result.sufficient,
                    "confidence": result.confidence,
                    "reasoning": result.reasoning
                }
                execution_results.append(execution_result)

                time.sleep(15) # due to Cohere and Groq API rate limit, sleep for 15 seconds to avoid hitting the limit

            self._save_execution_results(execution_results)
            self.log(f"Execution results saved to {self.execution_result}")

            report = generate_markdown_report(execution_results)
            self._save_markdown_report(report)
            self.log(f"Markdown report generated and saved to {self.evals_report}")

            return execution_results
        
        except Exception as e:
                self.log(f"Error during evaluation: {e}")
                return None

if __name__ == "__main__":
    evaluator = CompleteSearchEvals()
    print(evaluator.evaluate())