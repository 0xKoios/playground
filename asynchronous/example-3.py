import asyncio
from loguru import logger
import time

async def wash(basket):
    logger.info(f"Washing Machine ({basket}): Put the coin")
    logger.info(f"Washing Machine ({basket}): Start washing...")
    await asyncio.sleep(5)
    logger.success(f"Washing Machine ({basket}): Finished washing")
    return f"{basket} is completed!"

async def main():
    coro = wash("Basket A")
    logger.info(coro)
    logger.info(type(coro))
    task = asyncio.create_task(coro)
    logger.info(f"Task: {task}")
    logger.info(f"Task Type: {type(task)}")
    result = await task
    logger.info(result)

if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    end = time.time()
    logger.info(f"Total time: {end - start}")
