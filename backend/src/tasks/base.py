"""Base classes for Celery tasks."""

import asyncio
from celery import Task


class AsyncDatabaseTask(Task):
    """Base task class that provides async database session handling.

    This class provides a run_async method that properly manages event loops
    and ensures cleanup to prevent resource leaks.

    Usage:
        @celery_app.task(bind=True, base=AsyncDatabaseTask)
        def my_task(self, arg1, arg2):
            async def async_work():
                async with async_session_maker() as db:
                    # Do async database work
                    return result

            return self.run_async(async_work)
    """

    def run_async(self, async_func, *args, **kwargs):
        """Run an async function synchronously with proper cleanup.

        Args:
            async_func: Async function or coroutine to run
            *args: Positional arguments to pass to async_func
            **kwargs: Keyword arguments to pass to async_func

        Returns:
            The result of async_func

        Note:
            This method uses asyncio.run() which creates a new event loop,
            runs the coroutine, and properly cleans up the loop afterwards.
            A fallback is provided for edge cases where asyncio.run() isn't available.
        """
        # Use asyncio.run() for proper event loop management and cleanup
        # This creates a new loop, runs the coroutine, and cleans up
        try:
            return asyncio.run(async_func(*args, **kwargs))
        except RuntimeError:
            # Fallback for edge cases where asyncio.run() isn't available
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_func(*args, **kwargs))
            finally:
                try:
                    loop.close()
                finally:
                    asyncio.set_event_loop(None)
