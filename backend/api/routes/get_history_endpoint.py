from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from database import get_history

router = APIRouter(prefix="/history", tags=["History"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("/")
@limiter.limit("50/minute")
async def endpoint_get_history(request: Request):
    """
    Retrieves all search history.
    """
    try:
        histories: list[dict] = get_history()

        logger.info(f"Got number of histories: {len(histories)}")

        return {
            "status": "success",
            "number_of_histories": len(histories),
            "result": histories,
        }

    except Exception as e:
        logger.exception("Failed to get histories")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get histories: {str(e)}",
        )