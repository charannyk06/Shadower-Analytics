"""Base task classes for Celery tasks."""

import asyncio
from celery import Task


class AsyncDatabaseTask(Task):
    """Base task class that provides async database session handling."""

    def run_async(self, async_func, *args, **kwargs):
        """Run an async function synchronously.

        Uses asyncio.run() for better compatibility with Python 3.10+.
        """
        return asyncio.run(async_func(*args, **kwargs))
