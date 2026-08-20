from uuid import uuid4
from typing import Optional
from retrieval_agent.retrieval_agent import RetrievalAgent
from synthesizer.answer_synthesizer import AnswerSynthesizer
from schemas import RetrievalResult, SynthesizerResult
from database import (insert_execution, 
                      mark_execution_failure, 
                      mark_execution_success,
                      insert_history)
from utils.color import Logger
import logging 

logging.basicConfig(level=logging.INFO, format="%(message)s")

class LegalCopilot(Logger):
    """
    Orchestrates the Retrieval-Augmented Generation (RAG) pipeline for legal queries.

    This class serves as the primary coordinator, passing the user's query to the 
    RetrievalAgent to fetch relevant legal context, and then forwarding those 
    results to the AnswerSynthesizer to generate a final, structured response.

    Attributes:
        name (str): The identifier for this agent, used primarily for logging.
        color (str): The color constant applied to console logs for this class.
    """
    
    name: str = "LegalCopilot"
    color: str = Logger.BLUE

    def __init__(self):
        """
        Initializes the LegalCopilot along with its required sub-agents.
        """
        self.retrieval_agent = RetrievalAgent()
        self.answer_synthesizer = AnswerSynthesizer()

        self.log("Initialized the LegalCopilot")

    async def run(self, query: str) -> SynthesizerResult:
        """
        Executes the end-to-end retrieval and synthesis process for a user query.

        Generates a unique session ID to track the query through the pipeline. 
        If the retrieval step yields insufficient data, or if the synthesizer 
        fails to produce an answer, the process aborts gracefully.

        Args:
            query (str): The legal question or prompt provided by the user.

        Returns:
            Answer: A structured object containing the synthesized response.
                    Returns None if the pipeline fails, is missing data, 
                    or encounters an unexpected exception.
        """
        session_id = uuid4()

        insert_execution(
            execution_id=session_id,
            query=query,
        )

        try:
            self.log(
                f"Retrieving chunks \n"
                f"[Session: {session_id}] \n"
                f"[Query: {query}]"
            )

            retrieval_result: Optional[RetrievalResult] = (
                await self.retrieval_agent.run(
                    query=query,
                    session_id=session_id,
                )
            )

            if not retrieval_result:
                raise ValueError(
                    "Retrieval agent did not return a result."
                )

            synthesizer_result: Optional[SynthesizerResult] = (
                self.answer_synthesizer.answer(
                    query=query,
                    retrieval_result=retrieval_result,
                    session_id=session_id,
                )
            )

            if not synthesizer_result:
                raise ValueError(
                    "Answer synthesizer did not return a result."
                )

            insert_history(
                history_id=session_id,
                query=query,
                answer=synthesizer_result.answer.answer,
                citations=synthesizer_result.citations
            )

            mark_execution_success(execution_id=session_id)

            return synthesizer_result

        except Exception as e:

            mark_execution_failure(
                execution_id=session_id,
                error_message=str(e),
            )

            self.log(
                f"Pipeline failed for session "
                f"{session_id}: {str(e)}"
            )

            return None

if __name__ == "__main__":
    import asyncio

    copilot = LegalCopilot()
    query = """
    What deductions can a California landlord legally make from a tenant's security deposit, and how long does the landlord have to return the remaining balance after the tenant moves out?
    """

    answer = asyncio.run(copilot.run(query=query))

    print("========================================"*3)
    print(f"ANSWER: \n\n {answer.answer.answer} \n\n")
    print(f"REASONING: \n\n {answer.answer.reasoning_summary} \n\n")