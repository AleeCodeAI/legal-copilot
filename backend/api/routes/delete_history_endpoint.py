from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from database import delete_history

router = APIRouter(prefix="/history", tags=["History"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.delete("/delete-history/{history_id}")
@limiter.limit("100/minute")
async def endpoint_delete_history(request: Request, history_id: str):
    """
    Triggers the get history function.
    """
    try:
        did_delete = delete_history(history_id=history_id)
        if not did_delete:
            logger.info(f"Couldn't delete history with ID: {history_id}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "failure",
                    "history_id": history_id,
                    "message": "History not found",
                },
            )
        
        logger.info(f"Deleted history with ID: {history_id}")
        return JSONResponse(
                status_code=200,
                content={"status": "success", "deleted_history_id": history_id},
            )

    except Exception as e:
        logger.error(f"Failed to delete histories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete histories: {str(e)}")