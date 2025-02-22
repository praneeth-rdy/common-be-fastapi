from typing import Any

from fastapi import APIRouter, Depends
# from app.server.routes import route_dependencies
from app.server.services.cph import CphService
# from app.server.static import enums

router = APIRouter()

@router.get('/problems', description='Get CPH problems', responses={200: {'description': 'Success'}})
async def get_problems() -> dict[str, Any]:
    """
    Gets CPH problems
    Returns:
        Dict containing the problems data and status
    """
    data = await CphService().get_problems()
    return {'data': data, 'status': 'SUCCESS'}

