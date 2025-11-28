from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["healthcheck"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})
