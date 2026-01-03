"""
Feedback Loop and Human-in-the-Loop (HITL) Module
Provides mechanisms for collecting feedback, learning from corrections,
and incorporating human oversight into automated processes.
"""
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
import threading
import logging
import json
import uuid

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback that can be provided."""
    APPROVAL = "approval"
    REJECTION = "rejection"
    CORRECTION = "correction"
    ESCALATION = "escalation"
    COMMENT = "comment"
    RATING = "rating"


class DecisionOutcome(Enum):
    """Possible outcomes for human-reviewed decisions."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    ESCALATED = "escalated"
    PENDING = "pending"
    TIMEOUT = "timeout"


@dataclass
class FeedbackEntry:
    """A single feedback entry."""
    id: str
    timestamp: datetime
    feedback_type: FeedbackType
    source: str  # user ID or system component
    target_id: str  # ID of the item receiving feedback
    target_type: str  # Type of item (decision, prediction, recommendation)
    original_value: Any
    feedback_value: Any
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "feedback_type": self.feedback_type.value,
            "source": self.source,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "original_value": self.original_value,
            "feedback_value": self.feedback_value,
            "context": self.context,
            "metadata": self.metadata
        }


@dataclass
class HumanReviewRequest:
    """A request for human review/decision."""
    id: str
    created_at: datetime
    decision_type: str
    description: str
    options: List[Dict[str, Any]]
    context: Dict[str, Any]
    timeout_seconds: int
    callback: Optional[Callable] = None
    outcome: DecisionOutcome = DecisionOutcome.PENDING
    decision: Optional[Any] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "decision_type": self.decision_type,
            "description": self.description,
            "options": self.options,
            "context": self.context,
            "timeout_seconds": self.timeout_seconds,
            "outcome": self.outcome.value,
            "decision": self.decision,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None
        }


class FeedbackCollector:
    """
    Collects and stores feedback for learning and improvement.
    Supports various feedback types and aggregation for analysis.
    """

    def __init__(self, storage_backend=None):
        self._entries: List[FeedbackEntry] = []
        self._storage = storage_backend
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []

    def record(
        self,
        feedback_type: FeedbackType,
        source: str,
        target_id: str,
        target_type: str,
        original_value: Any,
        feedback_value: Any,
        context: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> FeedbackEntry:
        """Record a new feedback entry."""
        entry = FeedbackEntry(
            id=uuid.uuid4().hex,
            timestamp=datetime.now(UTC),
            feedback_type=feedback_type,
            source=source,
            target_id=target_id,
            target_type=target_type,
            original_value=original_value,
            feedback_value=feedback_value,
            context=context or {},
            metadata=metadata or {}
        )

        with self._lock:
            self._entries.append(entry)

        # Persist if storage available
        if self._storage:
            try:
                self._storage.save(entry)
            except Exception as e:
                logger.warning(f"Failed to persist feedback: {e}")

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception as e:
                logger.warning(f"Feedback listener error: {e}")

        logger.info(f"Recorded {feedback_type.value} feedback for {target_type}:{target_id}")
        return entry

    def get_feedback(
        self,
        target_id: Optional[str] = None,
        target_type: Optional[str] = None,
        feedback_type: Optional[FeedbackType] = None,
        limit: int = 100
    ) -> List[FeedbackEntry]:
        """Query feedback entries with optional filters."""
        with self._lock:
            results = self._entries.copy()

        if target_id:
            results = [e for e in results if e.target_id == target_id]
        if target_type:
            results = [e for e in results if e.target_type == target_type]
        if feedback_type:
            results = [e for e in results if e.feedback_type == feedback_type]

        return results[-limit:]

    def get_correction_rate(self, target_type: str) -> float:
        """Calculate the correction rate for a target type."""
        entries = self.get_feedback(target_type=target_type, limit=1000)
        if not entries:
            return 0.0

        corrections = sum(
            1 for e in entries
            if e.feedback_type in [FeedbackType.CORRECTION, FeedbackType.REJECTION]
        )
        return corrections / len(entries)

    def get_aggregated_stats(self, target_type: str) -> Dict[str, Any]:
        """Get aggregated statistics for feedback on a target type."""
        entries = self.get_feedback(target_type=target_type, limit=1000)

        if not entries:
            return {"total": 0}

        type_counts = {}
        for entry in entries:
            ft = entry.feedback_type.value
            type_counts[ft] = type_counts.get(ft, 0) + 1

        ratings = [
            e.feedback_value for e in entries
            if e.feedback_type == FeedbackType.RATING and isinstance(e.feedback_value, (int, float))
        ]

        return {
            "total": len(entries),
            "by_type": type_counts,
            "correction_rate": self.get_correction_rate(target_type),
            "avg_rating": sum(ratings) / len(ratings) if ratings else None,
            "sources": len(set(e.source for e in entries))
        }

    def add_listener(self, callback: Callable[[FeedbackEntry], None]):
        """Add a listener for new feedback entries."""
        self._listeners.append(callback)

    def export_for_training(
        self,
        target_type: str,
        feedback_types: Optional[List[FeedbackType]] = None
    ) -> List[Dict]:
        """Export feedback data in a format suitable for model training."""
        entries = self.get_feedback(target_type=target_type, limit=10000)

        if feedback_types:
            entries = [e for e in entries if e.feedback_type in feedback_types]

        training_data = []
        for entry in entries:
            if entry.feedback_type == FeedbackType.CORRECTION:
                training_data.append({
                    "input": entry.original_value,
                    "corrected_output": entry.feedback_value,
                    "context": entry.context
                })
            elif entry.feedback_type == FeedbackType.RATING:
                training_data.append({
                    "input": entry.original_value,
                    "quality_score": entry.feedback_value,
                    "context": entry.context
                })

        return training_data


class HumanInTheLoop:
    """
    Manages human oversight for automated decisions.
    Supports approval workflows, escalation, and timeout handling.
    """

    def __init__(self):
        self._pending_reviews: Dict[str, HumanReviewRequest] = {}
        self._completed_reviews: List[HumanReviewRequest] = []
        self._lock = threading.Lock()
        self._notification_handlers: List[Callable] = []
        self._auto_approve_rules: List[Callable] = []

    def request_review(
        self,
        decision_type: str,
        description: str,
        options: List[Dict[str, Any]],
        context: Optional[Dict] = None,
        timeout_seconds: int = 3600,
        callback: Optional[Callable] = None,
        auto_approve_threshold: Optional[float] = None
    ) -> HumanReviewRequest:
        """
        Create a request for human review.

        Args:
            decision_type: Type of decision (e.g., "severity_override", "remediation_approval")
            description: Human-readable description of what needs to be decided
            options: Available options/choices
            context: Additional context for the decision
            timeout_seconds: How long to wait for a decision
            callback: Function to call when decision is made
            auto_approve_threshold: If confidence > threshold, auto-approve

        Returns:
            HumanReviewRequest object
        """
        # Check auto-approve rules
        if auto_approve_threshold and context:
            confidence = context.get("confidence", 0)
            if confidence >= auto_approve_threshold:
                logger.info(
                    f"Auto-approving {decision_type} with confidence {confidence}"
                )
                request = HumanReviewRequest(
                    id=uuid.uuid4().hex,
                    created_at=datetime.now(UTC),
                    decision_type=decision_type,
                    description=description,
                    options=options,
                    context=context or {},
                    timeout_seconds=timeout_seconds,
                    callback=callback,
                    outcome=DecisionOutcome.APPROVED,
                    decision=options[0] if options else None,
                    decided_by="auto_approve",
                    decided_at=datetime.now(UTC)
                )
                self._completed_reviews.append(request)
                return request

        request = HumanReviewRequest(
            id=uuid.uuid4().hex,
            created_at=datetime.now(UTC),
            decision_type=decision_type,
            description=description,
            options=options,
            context=context or {},
            timeout_seconds=timeout_seconds,
            callback=callback
        )

        with self._lock:
            self._pending_reviews[request.id] = request

        # Notify handlers
        for handler in self._notification_handlers:
            try:
                handler(request)
            except Exception as e:
                logger.warning(f"Notification handler error: {e}")

        logger.info(f"Created review request {request.id} for {decision_type}")
        return request

    def submit_decision(
        self,
        request_id: str,
        decision: Any,
        decided_by: str,
        outcome: DecisionOutcome = DecisionOutcome.APPROVED
    ) -> bool:
        """Submit a human decision for a pending review."""
        with self._lock:
            if request_id not in self._pending_reviews:
                logger.warning(f"Review request {request_id} not found")
                return False

            request = self._pending_reviews.pop(request_id)

        request.outcome = outcome
        request.decision = decision
        request.decided_by = decided_by
        request.decided_at = datetime.now(UTC)

        self._completed_reviews.append(request)

        # Execute callback if provided
        if request.callback:
            try:
                request.callback(request)
            except Exception as e:
                logger.error(f"Decision callback error: {e}")

        logger.info(
            f"Decision submitted for {request_id}: {outcome.value} by {decided_by}"
        )
        return True

    def get_pending_reviews(
        self,
        decision_type: Optional[str] = None
    ) -> List[HumanReviewRequest]:
        """Get all pending review requests."""
        with self._lock:
            reviews = list(self._pending_reviews.values())

        if decision_type:
            reviews = [r for r in reviews if r.decision_type == decision_type]

        return reviews

    def get_review(self, request_id: str) -> Optional[HumanReviewRequest]:
        """Get a specific review request."""
        with self._lock:
            if request_id in self._pending_reviews:
                return self._pending_reviews[request_id]

        for review in self._completed_reviews:
            if review.id == request_id:
                return review

        return None

    def add_notification_handler(self, handler: Callable[[HumanReviewRequest], None]):
        """Add a handler for new review requests."""
        self._notification_handlers.append(handler)

    def check_timeouts(self) -> List[HumanReviewRequest]:
        """Check for timed-out reviews and handle them."""
        now = datetime.now(UTC)
        timed_out = []

        with self._lock:
            for request_id, request in list(self._pending_reviews.items()):
                elapsed = (now - request.created_at).total_seconds()
                if elapsed > request.timeout_seconds:
                    request.outcome = DecisionOutcome.TIMEOUT
                    request.decided_at = now
                    timed_out.append(request)
                    del self._pending_reviews[request_id]
                    self._completed_reviews.append(request)

        for request in timed_out:
            logger.warning(f"Review request {request.id} timed out")
            if request.callback:
                try:
                    request.callback(request)
                except Exception as e:
                    logger.error(f"Timeout callback error: {e}")

        return timed_out

    def get_decision_stats(self) -> Dict[str, Any]:
        """Get statistics on decisions made."""
        all_reviews = self._completed_reviews

        if not all_reviews:
            return {"total": 0}

        outcome_counts = {}
        for review in all_reviews:
            outcome = review.outcome.value
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        decision_times = []
        for review in all_reviews:
            if review.decided_at and review.outcome != DecisionOutcome.TIMEOUT:
                elapsed = (review.decided_at - review.created_at).total_seconds()
                decision_times.append(elapsed)

        return {
            "total": len(all_reviews),
            "pending": len(self._pending_reviews),
            "by_outcome": outcome_counts,
            "avg_decision_time_seconds": (
                sum(decision_times) / len(decision_times) if decision_times else None
            ),
            "decision_makers": len(set(
                r.decided_by for r in all_reviews if r.decided_by
            ))
        }


class TemporalReasoning:
    """
    Provides temporal reasoning capabilities for understanding
    time-based patterns, trends, and predictions.
    """

    def __init__(self):
        self._event_history: List[Dict] = []
        self._pattern_cache: Dict[str, Dict] = {}

    def record_event(
        self,
        event_type: str,
        timestamp: datetime,
        data: Dict[str, Any],
        metadata: Optional[Dict] = None
    ):
        """Record a time-stamped event."""
        self._event_history.append({
            "id": uuid.uuid4().hex,
            "type": event_type,
            "timestamp": timestamp,
            "data": data,
            "metadata": metadata or {}
        })

        # Keep last 10000 events
        if len(self._event_history) > 10000:
            self._event_history = self._event_history[-10000:]

    def get_events_in_range(
        self,
        start: datetime,
        end: datetime,
        event_type: Optional[str] = None
    ) -> List[Dict]:
        """Get events within a time range."""
        events = [
            e for e in self._event_history
            if start <= e["timestamp"] <= end
        ]

        if event_type:
            events = [e for e in events if e["type"] == event_type]

        return events

    def detect_frequency_change(
        self,
        event_type: str,
        window_size_hours: int = 24
    ) -> Dict[str, Any]:
        """Detect if event frequency has changed recently."""
        now = datetime.now(UTC)
        from datetime import timedelta

        # Recent window
        recent_start = now - timedelta(hours=window_size_hours)
        recent_events = self.get_events_in_range(recent_start, now, event_type)

        # Previous window
        prev_start = recent_start - timedelta(hours=window_size_hours)
        prev_events = self.get_events_in_range(prev_start, recent_start, event_type)

        recent_count = len(recent_events)
        prev_count = len(prev_events) or 1  # Avoid division by zero

        change_ratio = recent_count / prev_count

        return {
            "event_type": event_type,
            "window_hours": window_size_hours,
            "recent_count": recent_count,
            "previous_count": prev_count,
            "change_ratio": change_ratio,
            "trend": (
                "increasing" if change_ratio > 1.2
                else "decreasing" if change_ratio < 0.8
                else "stable"
            )
        }

    def find_correlated_events(
        self,
        event_type: str,
        correlation_window_seconds: int = 300
    ) -> Dict[str, float]:
        """Find events that frequently occur near a given event type."""
        from collections import defaultdict
        from datetime import timedelta

        target_events = [
            e for e in self._event_history if e["type"] == event_type
        ]

        correlations = defaultdict(int)
        total = 0

        for target in target_events:
            window_start = target["timestamp"] - timedelta(seconds=correlation_window_seconds)
            window_end = target["timestamp"] + timedelta(seconds=correlation_window_seconds)

            nearby = self.get_events_in_range(window_start, window_end)
            for event in nearby:
                if event["type"] != event_type:
                    correlations[event["type"]] += 1
            total += 1

        # Normalize to correlation scores
        if total > 0:
            return {k: v / total for k, v in correlations.items()}
        return {}

    def predict_next_occurrence(
        self,
        event_type: str
    ) -> Optional[Dict[str, Any]]:
        """Predict when an event type is likely to occur next."""
        from datetime import timedelta

        events = [
            e for e in self._event_history if e["type"] == event_type
        ]

        if len(events) < 3:
            return None

        # Calculate intervals
        sorted_events = sorted(events, key=lambda x: x["timestamp"])
        intervals = []
        for i in range(1, len(sorted_events)):
            diff = (sorted_events[i]["timestamp"] - sorted_events[i-1]["timestamp"]).total_seconds()
            intervals.append(diff)

        avg_interval = sum(intervals) / len(intervals)
        last_event = sorted_events[-1]["timestamp"]
        predicted_time = last_event + timedelta(seconds=avg_interval)

        return {
            "event_type": event_type,
            "predicted_time": predicted_time,
            "avg_interval_seconds": avg_interval,
            "confidence": min(0.9, len(events) / 20),  # More data = higher confidence
            "based_on_events": len(events)
        }


# Global instances
_feedback_collector: Optional[FeedbackCollector] = None
_hitl_manager: Optional[HumanInTheLoop] = None
_temporal_reasoning: Optional[TemporalReasoning] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get the global feedback collector instance."""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector


def get_hitl_manager() -> HumanInTheLoop:
    """Get the global HITL manager instance."""
    global _hitl_manager
    if _hitl_manager is None:
        _hitl_manager = HumanInTheLoop()
    return _hitl_manager


def get_temporal_reasoning() -> TemporalReasoning:
    """Get the global temporal reasoning instance."""
    global _temporal_reasoning
    if _temporal_reasoning is None:
        _temporal_reasoning = TemporalReasoning()
    return _temporal_reasoning
