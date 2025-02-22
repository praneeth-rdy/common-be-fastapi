import contextlib
import time
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import ExpiredSignatureError, JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from app.server.logger.custom_logger import logger
from app.server.static import localization


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handles exceptions in HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next):
        response = await handle_exceptions(request, call_next)
        return response or await call_next(request)


async def handle_exceptions(request: Request, call_next) -> JSONResponse:
    """Middleware to catch all the Exceptions and send API process time over response headers"""
    try:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers['X-Process-Time'] = f'{round(process_time * 1000, 2)}'
    except RequestValidationError as error:
        hex_code = hex(hash(error))
        if errors := error.errors():
            # Use only the first error message
            first_error = errors[0]
            error_message = f"Request validation error at ({first_error['loc'][-1]}): {first_error['msg']}"
        else:
            # No error, default message
            error_message = 'Request validation error unknown'
        error_message = f'{error_message}: {hex_code}'
        logger.exception(f'{error_message} >> {str(error)}')
        response = JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=get_error_response(error_message, status.HTTP_422_UNPROCESSABLE_ENTITY, error.errors()))
    except ValueError as error:
        hex_code = hex(hash(error))
        error_message = f'{str(error)}: {hex_code}'
        logger.exception(f'{error_message} >> {str(error)}')
        response = JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=get_error_response(error_message, status.HTTP_422_UNPROCESSABLE_ENTITY))
    except ExpiredSignatureError as error:
        hex_code = hex(hash(error))
        error_message = f'{localization.EXCEPTION_TOKEN_INVALID}: {hex_code}'
        logger.exception(f'{error_message} >> {str(error)}')
        response = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=get_error_response(error_message, status.HTTP_401_UNAUTHORIZED))
    except JWTError as error:
        hex_code = hex(hash(error))
        error_message = f'{str(error)}: {hex_code}'
        logger.exception(f'{error_message} >> {str(error)}')
        response = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=get_error_response(error_message, status.HTTP_401_UNAUTHORIZED))
    except HTTPException as error:
        # hex_code = hex(hash(error))
        error_message = f'{str(error.detail)}'
        logger.exception(f'{error_message} >> {str(error.detail)}')
        headers = {}
        with contextlib.suppress(AttributeError):
            headers = error.headers
        response = JSONResponse(status_code=error.status_code, content=get_error_response(error_message, error.status_code), headers=headers)
    except Exception as error:  # pylint: disable=broad-except
        hex_code = hex(hash(error))
        error_message = f'{localization.EXCEPTION_GENERIC_ERROR}: {hex_code}'
        logger.exception(f'{error_message} >> {str(error)}')
        response = JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=get_error_response(error_message, status.HTTP_500_INTERNAL_SERVER_ERROR))
    return response


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
