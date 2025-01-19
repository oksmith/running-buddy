import asyncio
import logging
from typing import Dict

logging.basicConfig(level=logging.DEBUG)

# Store pending confirmations
CONFIRMATION_REQUESTS: Dict[str, asyncio.Event] = {}
CONFIRMATION_RESPONSES: Dict[str, bool] = {}


async def get_user_confirmation_async(confirmation_id: str) -> bool:
    """
    Wait asynchronously for user confirmation from the UI.
    """
    logging.info(f"Creating confirmation request for ID: {confirmation_id}")
    event = asyncio.Event()
    CONFIRMATION_REQUESTS[confirmation_id] = event
    await event.wait()  # Wait for the user to confirm or cancel
    result = CONFIRMATION_RESPONSES.pop(confirmation_id, False)
    logging.info(f"Confirmation result for ID {confirmation_id}: {result}")
    return result