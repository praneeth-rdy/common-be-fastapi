import asyncio
import contextlib

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

import app.server.database.core_data as core_service
from app.server.logger.custom_logger import logger
from app.server.static import constants
from app.server.static.collections import Collections
from app.server.utils import token_util


class RequestsTrackerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log IP addresses for each request and user ID if the request has an Authorization header.
    """

    SENSITIVE_HEADERS = ['authorization', 'cookie', 'set-cookie']

    async def dispatch(self, request: Request, call_next):
        # Check if the request method is GET; if not, track the request address

        asyncio.create_task(self.track_request_address(request))
        response = await call_next(request)
        asyncio.create_task(self.log_api_requests(request, response))
        return response

    async def log_api_requests(self, request: Request, response: Response):
        if self.should_skip_logging(request):
            return

        host = self.get_client_ip(request)
        # Filter sensitive headers from request and response
        request_headers = {key: value for key, value in request.headers.items() if key not in self.SENSITIVE_HEADERS}
        # response_headers = {key: value for key, value in response.headers.items() if key not in self.SENSITIVE_HEADERS}

        logger_ctx = logger.bind(client_ip=host, url=request.url, method=request.method, status=response.status_code, request_headers=request_headers)
        logger_ctx.debug('Request received')

    async def track_request_address(self, request: Request):
        if self.should_skip_logging(request):
            return

        host = self.get_client_ip(request)
        user_id = self.extract_user_id(request)[0]

        query_params = dict(request.query_params)

        # Extract request body (if needed)
        body = await request.json() if request.method in ['POST', 'PUT', 'PATCH'] else {}
        masked_body = self.mask_sensitive_data(body)

        data = {'user_id': user_id, 'service': constants.LOGGER_SERVICE_NAME, 'ip': host, 'method': request.method, 'path': f'{request.url.path}', 'query_params': query_params}
        await core_service.create_one_time_series(collection_name=Collections.REQUEST_TRACKER, meta_data=data, body=masked_body)

    def extract_user_id(self, request: Request):
        user_id = ''
        bearer_token = ''
        if 'authorization' in request.headers:
            token = request.headers.get('authorization').split()
            if len(token) == 2 and token[0].lower() == 'bearer' and token[1] not in ['', ' ', 'null']:
                with contextlib.suppress(Exception):
                    bearer_token = token[1]
                    if user := token_util.verify_jwt_token(token[1]):
                        user_id = user['user_id']
        return user_id, bearer_token

    @staticmethod
    def get_client_ip(request: Request):
        forwarded = request.headers.get('X-Forwarded-For')
        return forwarded.split(',')[0] if forwarded else request.client.host

    @staticmethod
    def should_skip_logging(request: Request):
        return request.url.path in ['/']

    @staticmethod
    def mask_sensitive_data(data):
        sensitive_fields = ['password', 'new_password', 'current_password', 'access_token', 'refresh_token']  # Add more fields as needed

        def mask_string(value):
            return '*' * len(value)

        def mask_dict(data: dict[str, any]):
            for key, value in data.items():
                if key in sensitive_fields and isinstance(value, str):
                    data[key] = mask_string(value)

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    mask_dict(item)

        if isinstance(data, dict):
            mask_dict(data)

        return data
