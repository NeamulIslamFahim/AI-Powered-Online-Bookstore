from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException):
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(_request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"success": False, "error": exc.errors()})

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(_request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"success": False, "error": exc.errors()})

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail})
        return JSONResponse(status_code=500, content={"success": False, "error": "Internal server error"})
