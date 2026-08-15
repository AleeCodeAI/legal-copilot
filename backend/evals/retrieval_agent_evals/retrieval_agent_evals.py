from pathlib import Path
from .report_generator import generate_markdown_report
from configs.settings import get_settings
from prompts.prompt_manager import PromptManager
from schemas import RetrievalAgentEvalsSchema
from openai import OpenAI
from langfuse.decorators import observe
from utils.color import Logger
from evals.evals_observability.agent_evaluator_observability import AgentEvaluatorObservability  
import json
import time
import uuid
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

class RetrievalAgentEvals(Logger):
    """
    A class for evaluating retrieval agent quality.
    """
    name: str = "RetrievalAgentEvals"
    color: str = Logger.CYAN

    def __init__(self):
        self.settings = get_settings()
        self.prompt = PromptManager().get_retrieval_agent_evals()
        self.obs = AgentEvaluatorObservability()

        self.client = OpenAI(
            api_key=self.settings.groq.api_key,
            base_url=self.settings.groq.base_url
        )

        self.evals_data = Path(__file__).parents[3] / "data" / "evals_data" / "retrieval_agent_evals_data.json"
        self.execution_result = Path(__file__).parent / "results" / "retrieval_agent_execution_results.json"
        self.evals_report = Path(__file__).parent / "results" / "evals_report.md"

        self.log("RetrievalAgentEvals initialized successfully.")

    def _load_evals_data(self):
        try:
            with open(self.evals_data, 'r') as file:
                data = json.load(file)
            self.log("Evaluation data loaded successfully.")
            return data
        except Exception as e:
            self.log(f"Error loading evaluation data: {e}")
            raise

    def _save_execution_results(self, results: list[dict]):
        try:
            with open(self.execution_result, 'w') as file:
                json.dump(results, file, indent=4)
            self.log("Execution results saved successfully.")
        except Exception as e:
            self.log(f"Error saving execution results: {e}")
            raise

    def _save_markdown_report(self, report):
        try:
            with open(self.evals_report, "w", encoding="utf-8") as f:
                f.write(report)
            self.log(f"Markdown report saved to {self.evals_report}")
        except Exception as e:
            self.log(f"Error saving Markdown report: {e}")
            raise

    @staticmethod
    def _format_chunks(chunks):
        if not chunks:
            return "None"
        return "\n\n".join(
            f"CHUNK ID: {chunk.get('id')}\n"
            f"CONTENT:\n{chunk.get('content', '')}"
            for chunk in chunks
        )

    def _user_input(self, item) -> str:
        if not item:
            return "No results found."

        query = item.get("query")
        internal_chunks = item.get("internal_chunks", [])
        external_chunks = item.get("external_chunks", [])

        return (
            f"QUERY:\n{query}\n\n"
            f"INTERNAL CHUNKS:\n{self._format_chunks(internal_chunks)}\n\n"
            f"EXTERNAL CHUNKS:\n{self._format_chunks(external_chunks)}"
        )

    def _make_messages(self, user_input: str) -> list[dict]:
        return [
            {"role": "system", "content": self.prompt.prompt},
            {"role": "user", "content": user_input}
        ]

    @observe(as_type="generation", name="agent-evals-generation")
    def _call_llm(self, messages: list[dict]):
        """
        Calls the LLM with retries, tracks via Langfuse, and returns the response and usage.
        """
        last_exception = None

        for attempt in range(1, self.settings.groq.max_retries + 1):
            try:
                response = self.client.chat.completions.parse(
                    model=self.settings.groq.default_model,
                    messages=messages,
                    temperature=self.settings.groq.temperature,
                    response_format=RetrievalAgentEvalsSchema
                )
                
                result: RetrievalAgentEvalsSchema = response.choices[0].message.parsed
                usage = response.usage
                
                self.obs.log_generation(
                    messages=messages, 
                    output=result, 
                    usage=usage, 
                    model=self.settings.groq.default_model,
                    prompt=self.prompt
                )
                
                return result

            except Exception as e:
                last_exception = e
                self.log(f"LLM call failed (attempt {attempt}/{self.settings.groq.max_retries}): {e}")
                
                if attempt < self.settings.groq.max_retries:
                    time.sleep(1)  

        raise last_exception

    @observe()
    def _evaluate_single_item(self, item, session_id) -> dict:
        """Evaluates a single query/chunk payload within a Langfuse trace context."""
        query = item.get("query")
        self.log(f"EVALUATING QUERY: {query}")
        
        self.obs.init_eval_trace(session_id=session_id, query=query)

        try:
            user_input = self._user_input(item=item)
            messages = self._make_messages(user_input=user_input)

            self.log("calling LLM to evaluate")
            result = self._call_llm(messages)
            
            self.log(f"Evaluation complete. Sufficient: {result.sufficient}, Focused: {result.focused}, Confidence: {result.confidence}")
            
            self.obs.process_result(result)

            return {
                "query": query,
                "sufficient": result.sufficient,
                "focused": result.focused,
                "confidence": result.confidence,
                "reasoning": result.reasoning
            }

        except Exception as e:
            self.obs.process_failure(e)
            self.log(f"Error evaluating item '{query}': {e}")
            return None

    def evaluate(self):
        """
        Main loop to evaluate the retrieval agent quality.
        """
        try:
            evals_data = self._load_evals_data()
            if not evals_data:
                self.log("No evaluation data to process.")
                return None

            execution_results = []
            session_id = str(uuid.uuid4()) 

            for item in evals_data:
                exec_result = self._evaluate_single_item(item, session_id)
                
                if exec_result:
                    execution_results.append(exec_result)

                # API rate limit buffer
                time.sleep(2) 

            self._save_execution_results(execution_results)
            self.log(f"Execution results saved to {self.execution_result}")

            report = generate_markdown_report(execution_results)
            self._save_markdown_report(report)
            self.log(f"Markdown report generated and saved to {self.evals_report}")

            self.obs.flush()

            return execution_results
            
        except Exception as e:
            self.log(f"Error during batch evaluation: {e}")
            self.obs.flush()
            return execution_results

if __name__ == "__main__":
    evaluator = RetrievalAgentEvals()
    print(evaluator.evaluate())