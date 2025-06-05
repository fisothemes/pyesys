import asyncio
from pyesys import create_event

event, listener = create_event(example=lambda x: None)

async def async_handler(x: int) -> None:
    print("Waiting...")
    await asyncio.sleep(1)
    print(f"Async got: {x}")

listener += async_handler

asyncio.run(event.emit_async(123))