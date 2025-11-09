"""Funnel analysis service for conversion tracking and optimization."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text, delete
from sqlalchemy.dialects.postgresql import insert
import json

from ...models.database.tables import (
    FunnelDefinition,
    FunnelAnalysisResult,
    FunnelStepPerformance,
    UserFunnelJourney,
)
from ...utils.datetime import calculate_start_date

logger = logging.getLogger(__name__)


class FunnelAnalysisService:
    """Service for conversion funnel tracking and analysis."""

    # Query timeout in seconds
    QUERY_TIMEOUT_SECONDS = 30

    # Caching configuration
    CACHE_TTL_SECONDS = {
        "24h": 300,  # 5 minutes
        "7d": 900,  # 15 minutes
        "30d": 1800,  # 30 minutes
        "90d": 3600,  # 1 hour
    }

    # Analysis thresholds
    MIN_USERS_FOR_ANALYSIS = 10
    ABANDONMENT_THRESHOLD_HOURS = 24  # Hours before marking journey as abandoned

    def __init__(self, db: AsyncSession):
        self.db = db

    # ===================================================================
    # FUNNEL DEFINITION MANAGEMENT
    # ===================================================================

    async def create_funnel_definition(
        self,
        workspace_id: str,
        name: str,
        steps: List[Dict[str, Any]],
        description: Optional[str] = None,
        timeframe: str = "30d",
        segment_by: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new funnel definition.

        Args:
            workspace_id: Workspace ID
            name: Funnel name
            steps: List of funnel steps with event names
            description: Optional description
            timeframe: Default timeframe for analysis
            segment_by: Optional segmentation field
            created_by: User ID who created the funnel

        Returns:
            Created funnel definition
        """
        try:
            uuid.UUID(workspace_id)
            if created_by:
                uuid.UUID(created_by)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID: {str(e)}")

        # Validate steps format
        if not steps or len(steps) < 2:
            raise ValueError("Funnel must have at least 2 steps")

        for i, step in enumerate(steps):
            if not all(k in step for k in ["stepId", "stepName", "event"]):
                raise ValueError(f"Step {i} missing required fields")

        # Create funnel definition
        funnel = FunnelDefinition(
            workspace_id=workspace_id,
            name=name,
            description=description,
            steps=steps,
            timeframe=timeframe,
            segment_by=segment_by,
            created_by=created_by,
            status="active",
        )

        self.db.add(funnel)
        await self.db.commit()
        await self.db.refresh(funnel)

        logger.info(f"Created funnel definition: {funnel.id} for workspace {workspace_id}")

        return {
            "funnelId": str(funnel.id),
            "name": funnel.name,
            "description": funnel.description,
            "steps": funnel.steps,
            "timeframe": funnel.timeframe,
            "segmentBy": funnel.segment_by,
            "status": funnel.status,
            "createdAt": funnel.created_at.isoformat(),
        }

    async def get_funnel_definition(
        self,
        funnel_id: str,
        workspace_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get funnel definition by ID."""
        try:
            uuid.UUID(funnel_id)
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID: {str(e)}")

        result = await self.db.execute(
            select(FunnelDefinition).where(
                and_(
                    FunnelDefinition.id == funnel_id,
                    FunnelDefinition.workspace_id == workspace_id,
                )
            )
        )
        funnel = result.scalar_one_or_none()

        if not funnel:
            return None

        return {
            "funnelId": str(funnel.id),
            "name": funnel.name,
            "description": funnel.description,
            "steps": funnel.steps,
            "timeframe": funnel.timeframe,
            "segmentBy": funnel.segment_by,
            "status": funnel.status,
            "createdAt": funnel.created_at.isoformat(),
            "updatedAt": funnel.updated_at.isoformat(),
        }

    async def list_funnel_definitions(
        self,
        workspace_id: str,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all funnel definitions for a workspace."""
        try:
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid workspace ID: {str(e)}")

        query = select(FunnelDefinition).where(
            FunnelDefinition.workspace_id == workspace_id
        )

        if status:
            query = query.where(FunnelDefinition.status == status)

        query = query.order_by(desc(FunnelDefinition.created_at))

        result = await self.db.execute(query)
        funnels = result.scalars().all()

        return [
            {
                "funnelId": str(f.id),
                "name": f.name,
                "description": f.description,
                "stepCount": len(f.steps),
                "timeframe": f.timeframe,
                "status": f.status,
                "createdAt": f.created_at.isoformat(),
            }
            for f in funnels
        ]

    async def update_funnel_definition(
        self,
        funnel_id: str,
        workspace_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update funnel definition."""
        try:
            uuid.UUID(funnel_id)
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID: {str(e)}")

        result = await self.db.execute(
            select(FunnelDefinition).where(
                and_(
                    FunnelDefinition.id == funnel_id,
                    FunnelDefinition.workspace_id == workspace_id,
                )
            )
        )
        funnel = result.scalar_one_or_none()

        if not funnel:
            raise ValueError(f"Funnel {funnel_id} not found")

        # Update allowed fields
        for key, value in updates.items():
            if hasattr(funnel, key) and key not in ["id", "workspace_id", "created_at"]:
                setattr(funnel, key, value)

        await self.db.commit()
        await self.db.refresh(funnel)

        return {
            "funnelId": str(funnel.id),
            "name": funnel.name,
            "description": funnel.description,
            "steps": funnel.steps,
            "status": funnel.status,
            "updatedAt": funnel.updated_at.isoformat(),
        }

    # ===================================================================
    # FUNNEL ANALYSIS
    # ===================================================================

    async def analyze_funnel(
        self,
        funnel_id: str,
        workspace_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        segment_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze conversion funnel.

        Args:
            funnel_id: Funnel definition ID
            workspace_id: Workspace ID
            start_date: Analysis start date (defaults to funnel timeframe)
            end_date: Analysis end date (defaults to now)
            segment_name: Optional segment filter

        Returns:
            Funnel analysis results
        """
        try:
            uuid.UUID(funnel_id)
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID: {str(e)}")

        # Get funnel definition
        funnel_def = await self.get_funnel_definition(funnel_id, workspace_id)
        if not funnel_def:
            raise ValueError(f"Funnel {funnel_id} not found")

        # Set time range
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = calculate_start_date(funnel_def["timeframe"])

        # Analyze each step
        steps = funnel_def["steps"]
        step_results = []
        previous_users = None

        for i, step in enumerate(steps):
            step_metrics = await self._analyze_funnel_step(
                workspace_id,
                step,
                i,
                start_date,
                end_date,
                previous_users,
                segment_name,
            )
            step_results.append(step_metrics)
            previous_users = step_metrics["uniqueUsers"]

        # Calculate overall metrics
        overall_metrics = self._calculate_overall_metrics(step_results)

        # Get segment analysis if requested
        segment_results = None
        if funnel_def["segmentBy"] and not segment_name:
            segment_results = await self._analyze_segments(
                funnel_id,
                workspace_id,
                funnel_def,
                start_date,
                end_date,
            )

        # Store analysis results
        analysis_result = await self._store_analysis_results(
            funnel_id,
            workspace_id,
            start_date,
            end_date,
            step_results,
            overall_metrics,
            segment_name,
            segment_results,
        )

        return {
            "funnelId": funnel_id,
            "funnelName": funnel_def["name"],
            "steps": step_results,
            "overall": overall_metrics,
            "segments": segment_results,
            "analysisStart": start_date.isoformat(),
            "analysisEnd": end_date.isoformat(),
            "calculatedAt": datetime.utcnow().isoformat(),
        }

    async def _analyze_funnel_step(
        self,
        workspace_id: str,
        step: Dict[str, Any],
        step_order: int,
        start_date: datetime,
        end_date: datetime,
        previous_step_users: Optional[int],
        segment_name: Optional[str],
    ) -> Dict[str, Any]:
        """Analyze individual funnel step."""

        # Query to get users who completed this step
        # NOTE: This is a simplified example - you'll need to adjust based on your events table structure
        try:
            query = text("""
                SELECT
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(*) as total_events,
                    AVG(EXTRACT(EPOCH FROM (created_at - LAG(created_at) OVER (PARTITION BY user_id ORDER BY created_at)))) as avg_time_from_previous
                FROM analytics.user_activity
                WHERE workspace_id = :workspace_id
                    AND event_name = :event_name
                    AND created_at >= :start_date
                    AND created_at <= :end_date
            """)

            result = await self.db.execute(
                query,
                {
                    "workspace_id": workspace_id,
                    "event_name": step["event"],
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )

            row = result.fetchone()

            unique_users = row.unique_users if row else 0
            total_events = row.total_events if row else 0
            avg_time_from_previous = row.avg_time_from_previous if row and row.avg_time_from_previous else None
        except Exception as e:
            logger.error(f"Error analyzing funnel step '{step['stepName']}': {str(e)}", exc_info=True)
            # Return zero metrics on error to allow analysis to continue
            unique_users = 0
            total_events = 0
            avg_time_from_previous = None

        # Calculate conversion and drop-off rates
        if step_order == 0:
            conversion_rate = 100.0
            drop_off_rate = 0.0
        elif previous_step_users and previous_step_users > 0:
            conversion_rate = round((unique_users / previous_step_users) * 100, 2)
            drop_off_rate = round(100 - conversion_rate, 2)
        else:
            conversion_rate = 0.0
            drop_off_rate = 100.0

        # Analyze drop-off reasons (placeholder - implement based on your data)
        drop_off_reasons = await self._analyze_drop_off_reasons(
            workspace_id,
            step,
            start_date,
            end_date,
        )

        return {
            "stepId": step["stepId"],
            "stepName": step["stepName"],
            "event": step["event"],
            "metrics": {
                "totalUsers": total_events,
                "uniqueUsers": unique_users,
                "conversionRate": conversion_rate,
                "avgTimeToComplete": avg_time_from_previous,
                "dropOffRate": drop_off_rate,
            },
            "dropOffReasons": drop_off_reasons,
        }

    async def _analyze_drop_off_reasons(
        self,
        workspace_id: str,
        step: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Analyze reasons for drop-off at this step."""
        # This is a placeholder - implement based on your error tracking and user behavior data
        # You might look at:
        # - Errors that occurred before dropping off
        # - Time spent on the step
        # - User segments that drop off more
        # - Device/browser issues

        return [
            {"reason": "Session timeout", "count": 0, "percentage": 0.0},
            {"reason": "Error encountered", "count": 0, "percentage": 0.0},
            {"reason": "Navigation away", "count": 0, "percentage": 0.0},
        ]

    def _calculate_overall_metrics(
        self,
        step_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate overall funnel metrics."""
        if not step_results:
            return {
                "totalConversion": 0.0,
                "avgTimeToComplete": None,
                "biggestDropOff": None,
                "improvementPotential": 0.0,
            }

        first_step_users = step_results[0]["metrics"]["uniqueUsers"]
        last_step_users = step_results[-1]["metrics"]["uniqueUsers"]

        total_conversion = 0.0
        if first_step_users > 0:
            total_conversion = round((last_step_users / first_step_users) * 100, 2)

        # Find biggest drop-off
        biggest_drop_off = None
        max_drop_off_rate = 0.0

        for step in step_results[1:]:  # Skip first step
            drop_off_rate = step["metrics"]["dropOffRate"]
            if drop_off_rate > max_drop_off_rate:
                max_drop_off_rate = drop_off_rate
                biggest_drop_off = step["stepName"]

        # Calculate average time to complete
        times = [
            s["metrics"]["avgTimeToComplete"]
            for s in step_results
            if s["metrics"]["avgTimeToComplete"] is not None
        ]
        avg_time_to_complete = sum(times) / len(times) if times else None

        # Calculate improvement potential (based on biggest drop-off)
        improvement_potential = round(max_drop_off_rate / 2, 2)  # Assume 50% recovery possible

        return {
            "totalConversion": total_conversion,
            "avgTimeToComplete": avg_time_to_complete,
            "biggestDropOff": biggest_drop_off,
            "biggestDropOffRate": max_drop_off_rate,
            "improvementPotential": improvement_potential,
        }

    async def _analyze_segments(
        self,
        funnel_id: str,
        workspace_id: str,
        funnel_def: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Analyze funnel performance across segments."""
        segment_by = funnel_def.get("segmentBy")
        if not segment_by:
            return []

        # This is a placeholder - implement based on your segmentation logic
        # You would:
        # 1. Get distinct segment values
        # 2. Run funnel analysis for each segment
        # 3. Compare segment performance to average

        return []

    async def _store_analysis_results(
        self,
        funnel_id: str,
        workspace_id: str,
        start_date: datetime,
        end_date: datetime,
        step_results: List[Dict[str, Any]],
        overall_metrics: Dict[str, Any],
        segment_name: Optional[str],
        segment_results: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Store analysis results in database."""

        first_step = step_results[0] if step_results else {}
        last_step = step_results[-1] if step_results else {}

        result = FunnelAnalysisResult(
            funnel_id=funnel_id,
            workspace_id=workspace_id,
            analysis_start=start_date,
            analysis_end=end_date,
            step_results=step_results,
            total_entered=first_step.get("metrics", {}).get("uniqueUsers", 0),
            total_completed=last_step.get("metrics", {}).get("uniqueUsers", 0),
            overall_conversion_rate=overall_metrics.get("totalConversion", 0.0),
            avg_time_to_complete=overall_metrics.get("avgTimeToComplete"),
            biggest_drop_off_step=overall_metrics.get("biggestDropOff"),
            biggest_drop_off_rate=overall_metrics.get("biggestDropOffRate", 0.0),
            segment_name=segment_name,
            segment_results=segment_results,
        )

        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)

        logger.info(f"Stored funnel analysis result: {result.id}")

        return str(result.id)

    # ===================================================================
    # USER JOURNEY TRACKING
    # ===================================================================

    async def track_user_journey(
        self,
        funnel_id: str,
        workspace_id: str,
        user_id: str,
        step_id: str,
        step_name: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Track user progress through funnel.

        Args:
            funnel_id: Funnel definition ID
            workspace_id: Workspace ID
            user_id: User ID
            step_id: Step ID completed
            step_name: Step name
            timestamp: Event timestamp (defaults to now)
        """
        if not timestamp:
            timestamp = datetime.utcnow()

        # Get or create user journey
        result = await self.db.execute(
            select(UserFunnelJourney).where(
                and_(
                    UserFunnelJourney.funnel_id == funnel_id,
                    UserFunnelJourney.user_id == user_id,
                    UserFunnelJourney.status.in_(["in_progress", "completed"]),
                )
            ).order_by(desc(UserFunnelJourney.started_at)).limit(1)
        )
        journey = result.scalar_one_or_none()

        if not journey:
            # Create new journey
            journey = UserFunnelJourney(
                funnel_id=funnel_id,
                workspace_id=workspace_id,
                user_id=user_id,
                started_at=timestamp,
                status="in_progress",
                journey_path=[],
                time_per_step={},
            )
            self.db.add(journey)

        # Update journey path
        journey_path = journey.journey_path or []
        journey_path.append({
            "stepId": step_id,
            "stepName": step_name,
            "timestamp": timestamp.isoformat(),
        })
        journey.journey_path = journey_path
        journey.last_step_reached = step_id

        await self.db.commit()

    async def get_user_journeys(
        self,
        funnel_id: str,
        workspace_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get user journeys through funnel."""
        try:
            uuid.UUID(funnel_id)
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID: {str(e)}")

        query = select(UserFunnelJourney).where(
            and_(
                UserFunnelJourney.funnel_id == funnel_id,
                UserFunnelJourney.workspace_id == workspace_id,
            )
        )

        if status:
            query = query.where(UserFunnelJourney.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Get paginated results
        query = query.order_by(desc(UserFunnelJourney.started_at))
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        journeys = result.scalars().all()

        return {
            "journeys": [
                {
                    "userId": str(j.user_id),
                    "startedAt": j.started_at.isoformat(),
                    "completedAt": j.completed_at.isoformat() if j.completed_at else None,
                    "status": j.status,
                    "lastStepReached": j.last_step_reached,
                    "journeyPath": j.journey_path,
                    "totalTimeSpent": j.total_time_spent,
                }
                for j in journeys
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # ===================================================================
    # UTILITIES
    # ===================================================================

    async def get_funnel_performance_summary(
        self,
        workspace_id: str,
        timeframe: str = "30d",
    ) -> Dict[str, Any]:
        """Get summary of all funnels performance."""
        try:
            uuid.UUID(workspace_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid workspace ID: {str(e)}")

        start_date = calculate_start_date(timeframe)
        end_date = datetime.utcnow()

        # Query to get funnel overview from materialized view
        query = text("""
            SELECT
                funnel_id,
                funnel_name,
                step_count,
                overall_conversion_rate,
                health_score,
                total_completions,
                total_abandonments,
                last_analyzed_at
            FROM analytics.mv_funnel_overview
            WHERE workspace_id = :workspace_id
            ORDER BY health_score DESC
        """)

        result = await self.db.execute(
            query,
            {"workspace_id": workspace_id},
        )

        rows = result.fetchall()

        return {
            "funnels": [
                {
                    "funnelId": str(row.funnel_id),
                    "funnelName": row.funnel_name,
                    "stepCount": row.step_count,
                    "conversionRate": float(row.overall_conversion_rate) if row.overall_conversion_rate else 0.0,
                    "healthScore": float(row.health_score) if row.health_score else 0.0,
                    "totalCompletions": row.total_completions,
                    "totalAbandonments": row.total_abandonments,
                    "lastAnalyzed": row.last_analyzed_at.isoformat() if row.last_analyzed_at else None,
                }
                for row in rows
            ],
            "timeframe": timeframe,
            "generatedAt": datetime.utcnow().isoformat(),
        }


# ===================================================================
# LEGACY FUNCTIONS FOR BACKWARD COMPATIBILITY
# ===================================================================

async def analyze_conversion_funnel(
    db: AsyncSession,
    funnel_steps: List[str],
    start_date: datetime,
    end_date: datetime,
) -> Dict:
    """Analyze conversion funnel for given steps (legacy function).

    Args:
        db: Database session
        funnel_steps: List of funnel step names
        start_date: Start date for analysis
        end_date: End date for analysis

    Returns:
        Funnel data with conversion rates between steps
    """
    logger.warning("Using legacy analyze_conversion_funnel function. Consider using FunnelAnalysisService instead.")

    service = FunnelAnalysisService(db)

    # Convert legacy format to new format
    steps = [
        {
            "stepId": f"step_{i}",
            "stepName": step,
            "event": step,
        }
        for i, step in enumerate(funnel_steps)
    ]

    # This would need a workspace_id in real usage
    # For now, returning basic structure
    return {
        "steps": steps,
        "conversion_rates": [],
        "drop_off_points": [],
    }


async def identify_drop_off_points(
    db: AsyncSession,
    funnel_steps: List[str],
    start_date: datetime,
    end_date: datetime,
) -> List[Dict]:
    """Identify where users are dropping off in the funnel (legacy function)."""
    logger.warning("Using legacy identify_drop_off_points function. Consider using FunnelAnalysisService instead.")

    # Legacy placeholder
    return []
