from typing import Any

from fastapi import Depends

from app.server.services import validations
from app.server.static import enums
from app.server.utils.token_util import JWTAuthUser


async def check_client_or_super_admin(token: dict[str, Any] = Depends(JWTAuthUser(access_levels=[enums.Role.CLIENT, enums.Role.SUPER_ADMIN]))):
    if token['user_type'] == enums.Role.CLIENT.value:
        existing_client = await validations.check_client(token['user_id'])
        return {'entity': existing_client, 'role': enums.Role.CLIENT}

    existing_super_admin = await validations.check_super_admin(token['user_id'])
    return {'entity': existing_super_admin, 'role': enums.Role.SUPER_ADMIN}


async def check_client(token: dict[str, Any] = Depends(JWTAuthUser(access_levels=[enums.Role.CLIENT]))):
    existing_client = await validations.check_client(token['user_id'])
    return existing_client


async def check_talent(token: dict[str, Any] = Depends(JWTAuthUser(access_levels=[enums.Role.TALENT]))):
    existing_talent = await validations.check_talent(token['user_id'])
    return existing_talent


async def check_entity(token: dict[str, Any] = Depends(JWTAuthUser(access_levels=[enums.Role.CLIENT, enums.Role.TALENT]))):
    if token['user_type'] == enums.Role.CLIENT.value:
        existing_client = await validations.check_client(token['user_id'])
        return {'entity': existing_client, 'role': enums.Role.CLIENT}

    existing_talent = await validations.check_talent(token['user_id'])
    return {'entity': existing_talent, 'role': enums.Role.TALENT}
