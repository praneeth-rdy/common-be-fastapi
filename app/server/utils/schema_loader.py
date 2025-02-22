import json
import os
import pathlib

import aiofiles

current_path = os.path.dirname(__file__)


def get_schema_path():
    return os.path.join(current_path, '..', '..')


async def load_async(path):
    """Asynchronously read file

    Args:
        path (str): file path

    Returns:
        dict[str, Any]: json data
    """
    filepath = f'{get_schema_path()}/response_schemas/{path}'
    async with aiofiles.open(filepath, mode='r') as file:
        contents = await file.read()
    return json.loads(contents)


def load(path):
    """Synchronously read file

    Args:
        path (str): file path

    Returns:
        dict[str, Any]: json data
    """
    filepath = f'{get_schema_path()}/response_schemas/{path}'
    contents = pathlib.Path(filepath).read_text(encoding='utf-8')
    return json.loads(contents)
