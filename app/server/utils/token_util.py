import asyncio
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from fastapi.param_functions import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jose import jwt
from starlette.requests import Request

import app.server.database.core_data as core_service
from app.server.config import config
from app.server.static import enums, localization
from app.server.static.collections import Collections
from app.server.static.enums import AccountStatus, TokenType
from app.server.utils import date_utils

security_basic = HTTPBasic()


def authorize_docs(credentials: HTTPBasicCredentials = Depends(security_basic)):
    correct_username = secrets.compare_digest(credentials.username, config.DOC_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, config.DOC_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_USERNAME_PASSWORD_INVALID, headers={'WWW-Authenticate': 'Basic'})
    return credentials.username


def create_jwt_token(payload: dict[str, Any], expires_delta: timedelta = timedelta(days=1), token_type: TokenType = TokenType.BEARER) -> tuple[str, int]:
    """Creates jwt token

    Args:
        payload (dict): json object that needs to be encoded
        expires_delta (Optional[timedelta], optional): token expiry in timedelta. Defaults to timedelta(days=1).

    Returns:
        [str]: encoded jwt token
    """
    to_encode = payload.copy()
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    exp_timestamp = int(expire.timestamp() * 1000)
    to_encode |= {'token_type': token_type, 'iat': now, 'exp': expire}
    return jwt.encode(to_encode, config.JWT_SECRET, algorithm='HS256'), exp_timestamp


def verify_jwt_token(token: str, remove_reserved_claims: bool = False) -> dict[str, Any]:
    """Verifies jwt token signature

    Args:
        token (jwt-token): token that needs to be verified

    Returns:
        [JSON]: JSON payload of the decoded token
    """
    decoded_token = jwt.decode(token, config.JWT_SECRET, algorithms=['HS256'])
    if remove_reserved_claims:
        reserved_claims = ['iss', 'sub', 'aud', 'exp', 'nbf', 'iat', 'jti']
        for key in reserved_claims:
            if key in decoded_token:
                del decoded_token[key]
    return decoded_token


async def update_last_active(user_id: int) -> None:
    await core_service.update_one(Collections.USERS, data_filter={'_id': user_id}, update={'$set': {'last_active': date_utils.get_current_timestamp()}})


async def get_current_user(user_data: dict[str, Any], token: str) -> dict[str, Any]:
    pipelines: list[dict[str, Any]] = [
        {'$match': {'user_id': user_data['user_id'], 'user_type': user_data['user_type'], 'is_deleted': False, '$or': [{'access_token': token}, {'token': token}]}},
        {
            '$lookup': {
                'from': Collections.USERS,
                'let': {'user_id': '$user_id', 'user_type': '$user_type'},
                'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': ['$_id', '$$user_id']}, {'$eq': ['$user_type', '$$user_type']}, {'$eq': ['$is_deleted', False]}]}}}],
                'as': 'user',
            }
        },
        {'$unwind': '$user'},
        {'$replaceRoot': {'newRoot': '$user'}},
    ]
    if user_data['token_type'] == TokenType.RESET_PASSWORD.value:
        collection = Collections.REQUEST_TOKENS
    else:
        collection = Collections.ACCESS_TOKENS

    users = await core_service.query_read(collection, pipelines)

    return users[0] if users else {}


async def get_current_admin(user_data: dict[str, Any], token: str) -> dict[str, Any]:
    pipelines: list[dict[str, Any]] = [
        {'$match': {'user_id': user_data['user_id'], 'user_type': user_data['user_type'], 'is_deleted': False, '$or': [{'access_token': token}, {'token': token}]}},
        {
            '$lookup': {
                'from': Collections.ADMINS,
                'let': {'user_id': '$user_id', 'user_type': '$user_type'},
                'pipeline': [{'$match': {'$expr': {'$and': [{'$eq': ['$_id', '$$user_id']}, {'$eq': ['$user_type', '$$user_type']}, {'$eq': ['$is_deleted', False]}]}}}],
                'as': 'user',
            }
        },
        {'$unwind': '$user'},
        {'$replaceRoot': {'newRoot': '$user'}},
    ]
    if user_data['token_type'] == TokenType.RESET_PASSWORD.value:
        collection = Collections.REQUEST_TOKENS
    else:
        collection = Collections.ACCESS_TOKENS

    users = await core_service.query_read(collection, pipelines)

    return users[0] if users else {}


class JWTAuthUser:
    """
    A class used to manage JWT Authentication for a User.

    Attributes:
        access_levels (list): List of access levels the user requires.
        token_type (TokenType): Expected token type for validation.
    """

    # Using HTTP Bearer token security schema

    def __init__(self, access_levels: list[str], token_type: TokenType = TokenType.BEARER):
        """
        The JWTAuthUser constructor.

        Args:
            access_levels (list): List of access levels required by the user.
            token_type (TokenType): Expected token type (defaults to TokenType.BEARER).
        """
        self.access_levels = access_levels
        self.token_type = token_type

    async def _validate_token(self, request):
        """
        Validate the token from the request
        """
        # Extract the token from the cookies
        token = request.cookies.get('access_token')
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_TOKEN_INVALID)
        # Verify the JWT token
        token_data = verify_jwt_token(token.strip())
        if token_data['token_type'] != self.token_type.value:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_TOKEN_INVALID)
        return token_data, token

    async def _get_user(self, token_data, token):
        if token_data['user_type'] == enums.Role.SUPER_ADMIN:
            user = await get_current_admin(token_data, token)
        else:
            user = await get_current_user(token_data, token)

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_TOKEN_INVALID)
        return user

    async def _handle_super_admin(self, token_data, existing_user):
        # Check if the user's account is active
        if existing_user['account_status'] != AccountStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_ACCOUNT_INACTIVE)

        # Check if the user has the required access levels
        if token_data['user_type'] not in self.access_levels:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=localization.EXCEPTION_FORBIDDEN_ACCESS)

        # Update the last active time for the user
        asyncio.create_task(update_last_active(token_data['user_id']))

        return token_data

    def _get_cleaned_url_path(self, request):
        url_path = request.url.path
        # Remove any path parameters from the url_path
        for param_value in request.path_params.values():
            param_value_escaped = re.escape(param_value)
            url_path = re.sub(f'/{param_value_escaped}', '', url_path)
        return url_path

    async def _validate_permissions(self, request, existing_user):
        url_path = self._get_cleaned_url_path(request)
        await self.check_permissions(url_path, request.method, existing_user)

    async def _validate_access_level(self, token_data):
        # Check if the user has the required access level
        if token_data['user_type'] not in self.access_levels:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=localization.EXCEPTION_FORBIDDEN_ACCESS)

    async def check_permissions(self, endpoint: str, method: str, user: dict[str, Any]) -> None:

        if not user.get('app_roles'):
            return

        pipeline: list[dict[str, Any]] = [
            # Match the api_permissions based on endpoint and method
            {'$match': {'endpoint': endpoint, 'method': method}},
            # Perform lookup to get permissions for the user's roles
            {
                '$lookup': {
                    'from': Collections.APP_ROLES_PERMISSIONS,
                    'pipeline': [{'$match': {'app_role_id': {'$in': user.get('app_roles')}}}, {'$project': {'permission_id': 1, '_id': 0}}],
                    'as': 'user_permissions',
                }
            },
            # Check if required permission_id exists in user_permissions
            {'$addFields': {'permission_exists': {'$in': ['$permission_id', '$user_permissions.permission_id']}}},
        ]

        permissions_available = await core_service.query_read(Collections.API_PERMISSIONS, aggregate=pipeline)

        if not all(permission.get('permission_exists') for permission in permissions_available):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_PERMISSION_DOESNT_EXIST)

    async def __call__(self, request: Request):
        """
        Callable method to verify the authorization token and check the
        user's access levels.

        Args:
            credentials (HTTPAuthorizationCredentials, optional): HTTP authorization
                credentials obtained from the HTTP Bearer token.

        Raises:
            HTTPException: If the token is invalid, user does not exist,
                account is not active, or access level is insufficient.

        Returns:
            dict: The verified token data.
        """
        token_data, token = await self._validate_token(request)

        # Check if the token type matches the expected token type
        if token_data['token_type'] != self.token_type.value:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_TOKEN_INVALID)

        # Get the user
        existing_user = await self._get_user(token_data, token)
        if token_data['user_type'] == enums.Role.SUPER_ADMIN:
            return await self._handle_super_admin(token_data, existing_user)

        await self._validate_permissions(request, existing_user)

        if token_data['token_type'] == TokenType.SIGN_UP:

            if existing_user['account_status'] != AccountStatus.SIGN_UP:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_ACCOUNT_INACTIVE)
        else:
            if token_data['token_type'] != enums.TokenType.RESET_PASSWORD.value:
                if existing_user['account_status'] == AccountStatus.INACTIVE:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_ACCOUNT_INACTIVE)

                if existing_user['account_status'] == AccountStatus.RESTRICTED:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_ACCOUNT_RESTRICTED)

                # Check if the user's account is active
                if existing_user['account_status'] != AccountStatus.ACTIVE:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=localization.EXCEPTION_ACCOUNT_INACTIVE)

        await self._validate_access_level(token_data)

        # Update the last active time for the user
        asyncio.create_task(update_last_active(token_data['user_id']))

        return token_data
