from typing import Any

from fastapi import Header
from user_agents import parse


async def get_user_agent(user_agent: str = Header(None)) -> dict[str, Any]:
    """
    Asynchronously parses a user agent string to extract information
    about the user's operating system, device, and browser.

    Args:
        user_agent: A string that represents the user agent. Defaults to Header(None).
    Returns:
        dict: A dictionary containing information about the user's operating system, device, and browser.
    """
    agent_details = parse(user_agent)
    return {'os': agent_details.os.family, 'device': f'{agent_details.device.brand}:{agent_details.device.model}', 'browser': f'{agent_details.browser.family}:{agent_details.browser.version_string}'}
