from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    """Liveness probe used by Docker / load balancers."""
    return JSONResponse({"status": "ok"})
