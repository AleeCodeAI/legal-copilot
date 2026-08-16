from uuid import uuid4
from typing import Optional
from retrieval_agent.retrieval_agent import RetrievalAgent
from synthesizer.answer_synthesizer import AnswerSynthesizer
from schemas import RetrievalResult, Answer
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

    async def run(self, query: str) -> Answer:
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
        session_id = str(uuid4())
        
        try:
            self.log(f"Retrieving chunks [Session: {session_id}] [Query: {query}]")
            
            retrieval_result: Optional[RetrievalResult] = await self.retrieval_agent.run(
                query=query, 
                session_id=session_id
            )

            if not retrieval_result:
                self.log(f"No retrieval result produced for session {session_id}")
                return None

            self.log(
                f"Retrieval successful. Sufficient: {retrieval_result.sufficient}. "
                "Sending to Answer Synthesizer."
            )

            answer: Optional[Answer] = self.answer_synthesizer.answer(
                query=query,
                retrieval_result=retrieval_result, 
                session_id=session_id
            )

            if not answer:
                self.log(f"No answer produced for session {session_id} and query: {query}")
                return None

            self.log("Answer Synthesizer successfully produced answer")
            return answer
            
        except Exception as e:
            self.log(f"Pipeline failed for session {session_id} with error: {str(e)}")
            return None

if __name__ == "__main__":
    import asyncio

    copilot = LegalCopilot()
    query = """
    What are the legal distinctions between a single lodger and a tenant in a private residence, and what notice is required before a homeowner can remove a lodger who pays monthly rent?
    """

    answer = asyncio.run(copilot.run(query=query))

    print("========================================"*3)
    print(f"ANSWER: \n\n {answer.answer} \n\n")
    print(f"REASONING: \n\n {answer.reasoning_summary} \n\n")