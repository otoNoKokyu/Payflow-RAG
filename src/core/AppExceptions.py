from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .BaseResponse import BaseResponse
class AppBaseException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

async def business_exception_handler(request: Request, exc: AppBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content=BaseResponse(
            success=False,
            message=exc.message,
            data=None
        ).model_dump()
    )

async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=BaseResponse(
            success=False,
            message="An internal server error occurred.",
            data=None
        ).model_dump()
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = first_error.get("msg", "Validation failed")
    loc = first_error.get("loc", [])
    
    # Extract the specific field name that failed (usually the last element in loc, e.g., ['body', 'description'])
    field_name = loc[-1] if loc else "Field"
    
    # For ValueError raised in field validators, Pydantic prefixes "Value error, "
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, "):]
    else:
        # For standard required field errors, make it clearer
        msg = f"{field_name}: {msg}"
        
    return JSONResponse(
        status_code=400,
        content=BaseResponse(
            success=False,
            message=msg,
            data=None
        ).model_dump()
    )

def setup_exception_handlers(app):
    app.add_exception_handler(AppBaseException, business_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)