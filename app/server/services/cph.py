from typing import Any

from app.server.models.generic import DictType
from app.server.static.collections import Collections
import app.server.database.core_data as core_service


class CphService:
    async def get_problems(self) -> list[DictType]:
        """
        Gets CPH problems from database
        Returns:
            List of CPH problems
        """
        problems = await core_service.read_many(Collections.CPH_PROBLEMS, data_filter={})
        return problems
