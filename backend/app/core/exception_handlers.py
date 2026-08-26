"""FastAPI handlers for typed application failures."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import ApplicationError


async def application_error_handler(_request: Request, exc: ApplicationError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)
