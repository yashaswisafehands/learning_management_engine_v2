import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from neo4j.exceptions import ServiceUnavailable

executor = ThreadPoolExecutor()


async def run_sync(func, *args, **kwargs):
    """
    Run a synchronous function in a thread pool with retry logic for Neo4j.

    This executor is designed to provide a consistent, resilient way to run
    blocking, synchronous (e.g., repository) code from asynchronous FastAPI services.

    Features:
    - Kwargs Support: Uses `functools.partial` to pass keyword arguments to the
      target function, a feature not directly supported by `run_in_executor`.
    - Retry on Failure: Automatically retries operations up to 3 times if a
      `neo4j.exceptions.ServiceUnavailable` error occurs, which can happen with
      transient network issues or "defunct connection" problems.
    - Exponential Backoff: Waits with a small, increasing delay between retries
      (0.2s, 0.4s, etc.) to give the database time to recover.
    """
    loop = asyncio.get_event_loop()
    attempts = 0
    delay = 0.2  # Initial delay in seconds

    while True:
        try:
            if kwargs:
                # Wrap func with args and kwargs for executor
                wrapped_func = partial(func, *args, **kwargs)
                return await loop.run_in_executor(executor, wrapped_func)
            else:
                # Run with only positional args
                return await loop.run_in_executor(executor, func, *args)
        except ServiceUnavailable as e:
            attempts += 1
            if attempts >= 3:
                # Re-raise the exception after the final attempt
                raise e
            # Wait before retrying
            await asyncio.sleep(delay)
            # Increase delay for the next potential retry
            delay = min(delay * 2, 1.0)  # Cap delay at 1 second
