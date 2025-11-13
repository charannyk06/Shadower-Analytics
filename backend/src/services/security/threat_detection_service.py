"""Threat detection service for security analytics."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.schemas.security import (
    ThreatDetectionResult,
    BehavioralAnomaly,
    SecurityEvent,
)

logger = logging.getLogger(__name__)


class ThreatDetectionEngine:
    """Engine for detecting threats and anomalies in agent behavior."""

    def __init__(self, db: AsyncSession):
        """Initialize threat detection engine."""
        self.db = db
        self.anomaly_threshold = 0.7
        self.alert_threshold = 0.8

    async def detect_threats(
        self, agent_id: str, window_minutes: int = 60
    ) -> ThreatDetectionResult:
        """
        Detect threats for an agent within a time window.

        Args:
            agent_id: Agent identifier
            window_minutes: Time window for analysis in minutes

        Returns:
            ThreatDetectionResult with detected threats and recommendations
        """
        logger.info(f"Starting threat detection for agent {agent_id}")

        # Get recent events
        events = await self._get_recent_events(agent_id, window_minutes)

        if not events:
            return ThreatDetectionResult(
                agent_id=agent_id,
                threat_level=0.0,
                behavioral_anomalies=[],
                pattern_matches=[],
                statistical_outliers=[],
                risk_score=0.0,
                recommended_actions=[],
                timestamp=datetime.utcnow(),
            )

        # Run threat detection algorithms
        behavioral_anomalies = await self._detect_behavioral_anomalies(events)
        pattern_matches = await self._match_threat_patterns(events)
        statistical_outliers = await self._find_statistical_outliers(events)

        # Calculate overall threat level
        threat_level = self._calculate_threat_level(
            behavioral_anomalies, pattern_matches, statistical_outliers
        )

        # Calculate risk score
        risk_score = self._calculate_risk_score(
            behavioral_anomalies, pattern_matches, statistical_outliers
        )

        # Generate recommendations
        recommended_actions = self._generate_recommendations(
            threat_level, behavioral_anomalies, pattern_matches
        )

        # Generate alert if necessary
        if threat_level > self.alert_threshold:
            await self._generate_security_alert(
                agent_id, threat_level, behavioral_anomalies, pattern_matches
            )

        return ThreatDetectionResult(
            agent_id=agent_id,
            threat_level=threat_level,
            behavioral_anomalies=behavioral_anomalies,
            pattern_matches=pattern_matches,
            statistical_outliers=statistical_outliers,
            risk_score=risk_score,
            recommended_actions=recommended_actions,
            timestamp=datetime.utcnow(),
        )

    async def _get_recent_events(
        self, agent_id: str, window_minutes: int
    ) -> List[Dict[str, Any]]:
        """Get recent security events for an agent."""
        query = text("""
            SELECT
                id,
                agent_id,
                workspace_id,
                event_type,
                severity,
                event_data,
                threat_score,
                threat_category,
                created_at,
                session_id,
                source_ip,
                user_agent
            FROM analytics.security_events
            WHERE agent_id = :agent_id
                AND created_at > NOW() - INTERVAL ':window_minutes minutes'
            ORDER BY created_at DESC
        """)

        result = await self.db.execute(
            query, {"agent_id": agent_id, "window_minutes": window_minutes}
        )
        rows = result.fetchall()

        events = []
        for row in rows:
            events.append({
                "id": str(row.id),
                "agent_id": str(row.agent_id),
                "workspace_id": str(row.workspace_id),
                "event_type": row.event_type,
                "severity": row.severity,
                "event_data": row.event_data,
                "threat_score": row.threat_score,
                "threat_category": row.threat_category,
                "created_at": row.created_at,
                "session_id": str(row.session_id) if row.session_id else None,
                "source_ip": str(row.source_ip) if row.source_ip else None,
                "user_agent": row.user_agent,
            })

        return events

    async def _detect_behavioral_anomalies(
        self, events: List[Dict[str, Any]]
    ) -> List[BehavioralAnomaly]:
        """Detect behavioral anomalies in event patterns."""
        if not events:
            return []

        anomalies = []
        agent_id = events[0]["agent_id"]

        # Get behavior baseline
        baseline = await self._get_behavior_baseline(agent_id)

        if not baseline:
            logger.warning(f"No baseline found for agent {agent_id}")
            return []

        # Analyze each event for anomalies
        for event in events:
            features = self._extract_behavioral_features(event)
            deviation = self._calculate_deviation(features, baseline)

            if deviation > self.anomaly_threshold:
                anomaly_type = self._classify_anomaly(features, baseline)
                features_affected = self._identify_anomalous_features(
                    features, baseline
                )

                anomalies.append(
                    BehavioralAnomaly(
                        event_id=event["id"],
                        anomaly_type=anomaly_type,
                        deviation_score=deviation,
                        features_affected=features_affected,
                    )
                )

        return anomalies

    async def _get_behavior_baseline(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get behavior baseline for an agent."""
        query = text("""
            SELECT
                baseline_data,
                statistical_model,
                anomaly_threshold
            FROM analytics.security_baselines
            WHERE agent_id = :agent_id
                AND baseline_type = 'behavioral'
                AND active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = await self.db.execute(query, {"agent_id": agent_id})
        row = result.fetchone()

        if row:
            return {
                "baseline_data": row.baseline_data,
                "statistical_model": row.statistical_model,
                "anomaly_threshold": row.anomaly_threshold,
            }

        return None

    def _extract_behavioral_features(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Extract behavioral features from an event."""
        return {
            "event_type": event.get("event_type"),
            "severity": event.get("severity"),
            "hour_of_day": event.get("created_at").hour if event.get("created_at") else 0,
            "day_of_week": event.get("created_at").weekday() if event.get("created_at") else 0,
            "has_threat_score": event.get("threat_score") is not None,
            "threat_score": event.get("threat_score", 0),
            "source_ip": event.get("source_ip"),
            "user_agent": event.get("user_agent"),
        }

    def _calculate_deviation(
        self, features: Dict[str, Any], baseline: Dict[str, Any]
    ) -> float:
        """Calculate deviation from baseline."""
        baseline_data = baseline.get("baseline_data", {})

        if not baseline_data:
            return 0.0

        # Calculate deviation score based on feature differences
        deviations = []

        # Event type frequency deviation
        event_type = features.get("event_type")
        if event_type:
            baseline_freq = baseline_data.get("event_type_freq", {}).get(event_type, 0)
            if baseline_freq > 0:
                # Calculate how unusual this event type is
                deviations.append(1.0 - baseline_freq)

        # Severity deviation
        severity = features.get("severity")
        if severity in ["critical", "high"]:
            deviations.append(0.8)

        # Time-based deviation
        hour = features.get("hour_of_day", 0)
        baseline_hours = baseline_data.get("active_hours", [])
        if baseline_hours and hour not in baseline_hours:
            deviations.append(0.7)

        # Threat score deviation
        threat_score = features.get("threat_score", 0)
        baseline_threat = baseline_data.get("avg_threat_score", 0)
        if threat_score > baseline_threat * 2:
            deviations.append(0.9)

        return np.mean(deviations) if deviations else 0.0

    def _classify_anomaly(
        self, features: Dict[str, Any], baseline: Dict[str, Any]
    ) -> str:
        """Classify the type of anomaly."""
        event_type = features.get("event_type")
        severity = features.get("severity")
        hour = features.get("hour_of_day", 0)

        if severity in ["critical", "high"]:
            return "high_severity_event"
        elif hour < 6 or hour > 22:
            return "unusual_timing"
        elif event_type == "injection":
            return "injection_attempt"
        elif event_type == "authorization":
            return "privilege_escalation"
        else:
            return "general_anomaly"

    def _identify_anomalous_features(
        self, features: Dict[str, Any], baseline: Dict[str, Any]
    ) -> List[str]:
        """Identify which features are anomalous."""
        anomalous = []

        if features.get("severity") in ["critical", "high"]:
            anomalous.append("severity")

        if features.get("threat_score", 0) > 70:
            anomalous.append("threat_score")

        hour = features.get("hour_of_day", 0)
        if hour < 6 or hour > 22:
            anomalous.append("timing")

        return anomalous

    async def _match_threat_patterns(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Match events against known threat patterns."""
        if not events:
            return []

        # Get event sequence
        event_sequence = [e.get("event_type") for e in events]

        # Query attack patterns
        query = text("""
            SELECT
                id,
                pattern_name,
                attack_type,
                threat_level,
                typical_sequence,
                min_match_score
            FROM analytics.attack_patterns
            WHERE enabled = TRUE
        """)

        result = await self.db.execute(query)
        patterns = result.fetchall()

        matches = []
        for pattern in patterns:
            match_score = self._calculate_pattern_match_score(
                event_sequence, pattern.typical_sequence
            )

            if match_score >= pattern.min_match_score:
                matches.append({
                    "pattern_id": str(pattern.id),
                    "pattern_name": pattern.pattern_name,
                    "attack_type": pattern.attack_type,
                    "threat_level": pattern.threat_level,
                    "match_score": match_score,
                })

        return matches

    def _calculate_pattern_match_score(
        self, event_sequence: List[str], pattern_sequence: List[str]
    ) -> float:
        """Calculate similarity score between event sequence and pattern."""
        if not event_sequence or not pattern_sequence:
            return 0.0

        # Simple sequence matching
        matches = sum(1 for e in event_sequence if e in pattern_sequence)
        max_length = max(len(event_sequence), len(pattern_sequence))

        return matches / max_length if max_length > 0 else 0.0

    async def _find_statistical_outliers(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find statistical outliers in event data."""
        outliers = []

        if len(events) < 3:
            return outliers

        # Extract numerical features
        threat_scores = [
            e.get("threat_score", 0) for e in events if e.get("threat_score") is not None
        ]

        if threat_scores:
            mean_score = np.mean(threat_scores)
            std_score = np.std(threat_scores)

            for event in events:
                score = event.get("threat_score", 0)
                if score and abs(score - mean_score) > 2 * std_score:
                    outliers.append({
                        "event_id": event["id"],
                        "metric": "threat_score",
                        "value": score,
                        "mean": mean_score,
                        "std_dev": std_score,
                        "z_score": (score - mean_score) / std_score if std_score > 0 else 0,
                    })

        return outliers

    def _calculate_threat_level(
        self,
        behavioral_anomalies: List[BehavioralAnomaly],
        pattern_matches: List[Dict[str, Any]],
        statistical_outliers: List[Dict[str, Any]],
    ) -> float:
        """Calculate overall threat level."""
        scores = []

        # Behavioral anomaly contribution
        if behavioral_anomalies:
            avg_deviation = np.mean([a.deviation_score for a in behavioral_anomalies])
            scores.append(avg_deviation * 100)

        # Pattern match contribution
        if pattern_matches:
            max_match_score = max(m.get("match_score", 0) for m in pattern_matches)
            scores.append(max_match_score * 100)

        # Outlier contribution
        if statistical_outliers:
            max_z_score = max(abs(o.get("z_score", 0)) for o in statistical_outliers)
            outlier_score = min(max_z_score / 3 * 100, 100)
            scores.append(outlier_score)

        return min(np.mean(scores) if scores else 0.0, 100.0)

    def _calculate_risk_score(
        self,
        behavioral_anomalies: List[BehavioralAnomaly],
        pattern_matches: List[Dict[str, Any]],
        statistical_outliers: List[Dict[str, Any]],
    ) -> float:
        """Calculate overall risk score."""
        risk_factors = []

        # High severity anomalies
        high_severity_anomalies = sum(
            1 for a in behavioral_anomalies
            if "high_severity" in a.anomaly_type or "escalation" in a.anomaly_type
        )
        if high_severity_anomalies > 0:
            risk_factors.append(min(high_severity_anomalies * 20, 80))

        # Critical pattern matches
        critical_patterns = sum(
            1 for m in pattern_matches if m.get("threat_level") == "critical"
        )
        if critical_patterns > 0:
            risk_factors.append(90)

        # Multiple anomalies
        if len(behavioral_anomalies) > 5:
            risk_factors.append(70)

        return min(max(risk_factors) if risk_factors else 0.0, 100.0)

    def _generate_recommendations(
        self,
        threat_level: float,
        behavioral_anomalies: List[BehavioralAnomaly],
        pattern_matches: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate security recommendations."""
        recommendations = []

        if threat_level > 80:
            recommendations.append("Immediate investigation required - critical threat level detected")
            recommendations.append("Consider temporarily restricting agent permissions")

        if any("injection" in a.anomaly_type for a in behavioral_anomalies):
            recommendations.append("Review and sanitize all user inputs")
            recommendations.append("Implement input validation and parameterized queries")

        if any("escalation" in a.anomaly_type for a in behavioral_anomalies):
            recommendations.append("Audit agent permission levels")
            recommendations.append("Implement principle of least privilege")

        if pattern_matches:
            recommendations.append("Review detected attack patterns and update security policies")
            recommendations.append("Enable additional monitoring for matched attack vectors")

        if threat_level > 60 and len(behavioral_anomalies) > 3:
            recommendations.append("Increase monitoring frequency for this agent")
            recommendations.append("Review recent configuration changes")

        return recommendations

    async def _generate_security_alert(
        self,
        agent_id: str,
        threat_level: float,
        behavioral_anomalies: List[BehavioralAnomaly],
        pattern_matches: List[Dict[str, Any]],
    ):
        """Generate security alert for high threat levels."""
        logger.warning(
            f"Security alert for agent {agent_id}: "
            f"threat_level={threat_level}, "
            f"anomalies={len(behavioral_anomalies)}, "
            f"patterns={len(pattern_matches)}"
        )

        # Insert security incident
        query = text("""
            INSERT INTO analytics.security_incidents (
                incident_number,
                agent_id,
                workspace_id,
                incident_type,
                severity,
                status,
                description,
                detected_at
            )
            SELECT
                'INC-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0'),
                :agent_id,
                workspace_id,
                'automated_threat_detection',
                CASE
                    WHEN :threat_level > 90 THEN 'critical'
                    WHEN :threat_level > 70 THEN 'high'
                    WHEN :threat_level > 40 THEN 'medium'
                    ELSE 'low'
                END,
                'detected',
                :description,
                NOW()
            FROM analytics.security_events
            WHERE agent_id = :agent_id
            LIMIT 1
        """)

        description = (
            f"Automated threat detection triggered for agent {agent_id}. "
            f"Threat level: {threat_level:.2f}. "
            f"Behavioral anomalies: {len(behavioral_anomalies)}. "
            f"Pattern matches: {len(pattern_matches)}."
        )

        await self.db.execute(
            query,
            {
                "agent_id": agent_id,
                "threat_level": threat_level,
                "description": description,
            },
        )
        await self.db.commit()
