from pydantic import BaseModel
from typing import Generic, TypeVar
from fastapi.routing import APIRoute
from fastapi import APIRouter, Request, Response
from fastapi.exceptions import RequestValidationError
from typing import Callable
import json
from fastapi.responses import JSONResponse

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str = "Success"


class WrappedAPIRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request) -> Response:
            data = await original_handler(request)

            if isinstance(data, JSONResponse):
                # FastAPI converts ALL route return types (dict, Pydantic model,
                # None, primitives) into JSONResponse before reaching here.
                json_data = json.loads(data.body)
                wrapped = BaseResponse(data=json_data)
                return JSONResponse(
                    status_code=data.status_code,
                    content=wrapped.model_dump(),
                )

            # Pass through non-JSON responses (FileResponse, StreamingResponse, etc.)
            return data

           

        return custom_handler


class WrappedRouter(APIRouter):
    def __init__(self, **kwargs):
        kwargs.setdefault("route_class", WrappedAPIRoute)
        super().__init__(**kwargs)