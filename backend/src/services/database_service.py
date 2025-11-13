"""Advanced database service layer with connection pooling and query execution."""

from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import text
import asyncpg
from contextlib import asynccontextmanager
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """Advanced database service with connection pooling and raw query support."""

    def __init__(self):
        self.engine = None
        self.async_session_maker = None
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connections and pools."""
        logger.info("Initializing database service...")

        # Convert postgresql:// to postgresql+asyncpg://
        database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            database_url,
            echo=settings.APP_ENV == "development",
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=True,  # Verify connections before using
            poolclass=AsyncAdaptedQueuePool,
        )

        # Create session factory
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        # Extract connection parameters for asyncpg
        db_url = settings.DATABASE_URL

        # Create asyncpg connection pool for raw queries
        try:
            self.pool = await asyncpg.create_pool(
                db_url,
                min_size=10,
                max_size=20,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                timeout=30,
                command_timeout=60,
            )
            logger.info(f"Database connection pool created: min=10, max=20")
        except Exception as e:
            logger.error(f"Failed to create asyncpg pool: {e}")
            raise

        logger.info("Database service initialized successfully")

    @asynccontextmanager
    async def get_session(self):
        """Get database session with automatic commit/rollback.

        Yields:
            AsyncSession: Database session

        Example:
            async with db_service.get_session() as session:
                result = await session.execute(query)
                # Automatically commits on success, rolls back on error
        """
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        fetch_all: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute raw SQL query and return results.

        Args:
            query: SQL query string
            params: Query parameters
            fetch_all: If True, fetch all results. If False, fetch one.

        Returns:
            List of dictionaries with query results

        Example:
            results = await db_service.execute_query(
                "SELECT * FROM users WHERE workspace_id = $1",
                params={"workspace_id": "ws_123"}
            )
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")

        try:
            async with self.pool.acquire() as connection:
                if params:
                    # Convert dict params to list if using positional parameters
                    if "$" in query:
                        param_values = list(params.values())
                        rows = await connection.fetch(query, *param_values)
                    else:
                        # Named parameters
                        rows = await connection.fetch(query, **params)
                else:
                    rows = await connection.fetch(query)

                # Convert asyncpg.Record to dict
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Query execution error: {e}\nQuery: {query}\nParams: {params}")
            raise

    async def execute_query_one(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute query and return single result.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single result dictionary or None

        Example:
            user = await db_service.execute_query_one(
                "SELECT * FROM users WHERE id = $1",
                params={"id": "user_123"}
            )
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")

        try:
            async with self.pool.acquire() as connection:
                if params:
                    if "$" in query:
                        param_values = list(params.values())
                        row = await connection.fetchrow(query, *param_values)
                    else:
                        row = await connection.fetchrow(query, **params)
                else:
                    row = await connection.fetchrow(query)

                return dict(row) if row else None

        except Exception as e:
            logger.error(f"Query execution error: {e}\nQuery: {query}\nParams: {params}")
            raise

    async def execute_batch(
        self,
        queries: List[Tuple[str, Dict[str, Any]]]
    ) -> List[Any]:
        """Execute multiple queries in a transaction.

        Args:
            queries: List of (query, params) tuples

        Returns:
            List of results from each query

        Example:
            results = await db_service.execute_batch([
                ("INSERT INTO users (id, name) VALUES ($1, $2)", {"id": "1", "name": "John"}),
                ("INSERT INTO users (id, name) VALUES ($1, $2)", {"id": "2", "name": "Jane"}),
            ])
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")

        try:
            async with self.pool.acquire() as connection:
                async with connection.transaction():
                    results = []
                    for query, params in queries:
                        if params:
                            if "$" in query:
                                param_values = list(params.values())
                                result = await connection.fetch(query, *param_values)
                            else:
                                result = await connection.fetch(query, **params)
                        else:
                            result = await connection.fetch(query)

                        results.append([dict(row) for row in result] if result else [])

                    return results

        except Exception as e:
            logger.error(f"Batch execution error: {e}")
            raise

    async def execute_many(
        self,
        query: str,
        params_list: List[Dict[str, Any]]
    ) -> int:
        """Execute the same query multiple times with different parameters.

        Useful for bulk inserts or updates.

        Args:
            query: SQL query string
            params_list: List of parameter dictionaries

        Returns:
            Number of affected rows

        Example:
            count = await db_service.execute_many(
                "INSERT INTO logs (user_id, action) VALUES ($1, $2)",
                [
                    {"user_id": "1", "action": "login"},
                    {"user_id": "2", "action": "logout"},
                ]
            )
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")

        try:
            async with self.pool.acquire() as connection:
                async with connection.transaction():
                    # Convert list of dicts to list of tuples
                    if "$" in query:
                        param_tuples = [tuple(params.values()) for params in params_list]
                        result = await connection.executemany(query, param_tuples)
                    else:
                        # Named parameters - less efficient but supported
                        count = 0
                        for params in params_list:
                            await connection.execute(query, **params)
                            count += 1
                        return count

                    # Parse result (format: "INSERT 0 N" or "UPDATE N")
                    if isinstance(result, str):
                        return int(result.split()[-1])
                    return len(params_list)

        except Exception as e:
            logger.error(f"Execute many error: {e}\nQuery: {query}")
            raise

    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        if not self.pool:
            return {"status": "not_initialized"}

        return {
            "status": "active",
            "size": self.pool.get_size(),
            "free_size": self.pool.get_idle_size(),
            "min_size": self.pool.get_min_size(),
            "max_size": self.pool.get_max_size(),
        }

    async def close(self):
        """Close all database connections."""
        logger.info("Closing database connections...")

        try:
            if self.pool:
                await self.pool.close()
                logger.info("AsyncPG pool closed")

            if self.engine:
                await self.engine.dispose()
                logger.info("SQLAlchemy engine disposed")

        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
            raise

        logger.info("Database service closed successfully")

    async def health_check(self) -> bool:
        """Check database health.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as connection:
                result = await connection.fetchval("SELECT 1")
                return result == 1

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Singleton instance
db_service = DatabaseService()


async def get_db_service() -> DatabaseService:
    """Get database service instance.

    Returns:
        DatabaseService: Singleton database service instance
    """
    if not db_service.pool:
        await db_service.initialize()
    return db_service
