import contextlib
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.server.logger.custom_logger import logger


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Exception handler to handle Request validation errors
    Args:
        request (Request): Request object
        exc (RequestValidationError): Exception object

    Returns:
        JSONResponse: Returns error data in the desired format
    """
    if errors := exc.errors():
        # Use only the first error message
        first_error = errors[0]
        error_message = f"Request validation error at ({first_error['loc'][-1]}): {first_error['msg']}"
    else:
        # No error, default message
        error_message = 'Request validation error unknown'
    hex_code = hex(hash(exc))
    error_message = f'{error_message}: {hex_code}'
    logger.exception(f'{error_message} >> {str(exc)}')
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=get_error_response(error_message, status.HTTP_422_UNPROCESSABLE_ENTITY, exc.errors()))


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Exception handler to handle exception of type HTTPException
    Args:
        request (Request): Request object
        exc (HTTPException): Exception object

    Returns:
        JSONResponse: Returns error data in the desired format
    """
    # hex_code = hex(hash(exc))
    error_message = f'{str(exc.detail)}'
    logger.exception(f'{error_message} >> {str(exc)}')
    headers = {}
    with contextlib.suppress(AttributeError):
        headers = exc.headers
    return JSONResponse(status_code=exc.status_code, content=get_error_response(error_message, exc.status_code), headers=headers)


def get_error_response(message: str, code: int, detail: Any = None) -> dict[str, Any]:
    """Function to format error data

    Args:
        message (str): Error message
        code (int): Error code

    Returns:
        JSON: Returns error data in the desired format
    """
    error = {'status': 'FAIL', 'errorData': {'errorCode': code, 'message': message}}
    if detail:
        error['errorData'].update({'detail': detail})
    return jsonable_encoder(error)
