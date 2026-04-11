from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    """Liveness probe used by Docker / load balancers."""
    return JSONResponse({"status": "ok"})


@router.get("/info")
async def app_info() -> dict:
    """
    Public metadata used by the frontend.

    Returns:
      vault_name — leaf folder name of the Obsidian vault, used to build
                   obsidian://open?vault=<vault_name>&file=<note> URIs.
    """
    from api.dependencies import get_config
    config = get_config()
    return {"vault_name": config.vault_path.name}
