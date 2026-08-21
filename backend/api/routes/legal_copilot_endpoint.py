from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from app.legal_copilot import LegalCopilot
from schemas import SynthesizerResult

router = APIRouter(prefix="/master-pipeline", tags=["Master"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.post("/legal-copilot-run")
@limiter.limit("10/minute")
async def endpoint_run_copilot(request: Request, query: str):
    """
    Triggers the master pipeline executor.
    Takes the query, run retrieval and synthesizer pipeline the returns back structured output.
    """
    try:
        copilot = LegalCopilot()
        result: SynthesizerResult = await copilot.run(query=query)

        logger.info(f"Copilot finished; answer generated: {"True" if result.answer.answer != None else "False"}")

        data = {
                    "answer": result.answer.answer,
                    "synthesizer_reasoning": result.answer.reasoning_summary,
                    "citations": result.citations,
                }

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "answer_generated": ("True" if result.answer.answer != None else "False"),
                "result": data,
            },
        )

    except Exception as e:
        logger.error(f"Failed to run executor: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run executor: {str(e)}")