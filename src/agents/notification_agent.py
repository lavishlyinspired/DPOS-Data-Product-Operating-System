"""
Stakeholder Notification Agent
Intelligent agent for creating context-aware notifications for different stakeholders.
Uses LLM to tailor messaging based on audience and urgency.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime, UTC
from enum import Enum
import operator
import logging
import json

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

# Try to import LLM components
try:
    from src.core.llm import UnifiedLLM, LLMConfig
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class StakeholderType(Enum):
    """Types of stakeholders for notifications."""
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    BUSINESS = "business"
    OPERATIONS = "operations"
    CUSTOMER = "customer"
    COMPLIANCE = "compliance"


class NotificationChannel(Enum):
    """Available notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    DASHBOARD = "dashboard"
    PAGERDUTY = "pagerduty"


class NotificationState(TypedDict):
    """State for notification workflow."""
    event: Dict  # The event triggering notification
    stakeholders: List[Dict]  # Stakeholders to notify
    notification_plan: Dict[str, List[Dict]]  # Notifications per stakeholder type
    generated_messages: List[Dict]
    delivery_status: Dict[str, str]
    escalation_needed: bool
    escalation_chain: List[str]
    messages: Annotated[List[str], operator.add]


class StakeholderNotificationAgent:
    """
    Agent that creates intelligent, context-aware notifications for stakeholders.
    Tailors messaging based on:
    - Stakeholder role and technical level
    - Event severity and urgency
    - Communication channel constraints
    - Historical preferences
    """

    def __init__(self, graph_manager=None):
        self.graph_manager = graph_manager
        self._llm = None

        if LLM_AVAILABLE:
            try:
                config = LLMConfig()
                self._llm = UnifiedLLM(config)
                logger.info("StakeholderNotificationAgent initialized with LLM support")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")

        # Default stakeholder preferences
        self.stakeholder_preferences = {
            StakeholderType.EXECUTIVE: {
                "channels": [NotificationChannel.EMAIL, NotificationChannel.SLACK],
                "detail_level": "high-level",
                "focus": ["business impact", "timeline", "action needed"],
                "max_length": 200
            },
            StakeholderType.TECHNICAL: {
                "channels": [NotificationChannel.SLACK, NotificationChannel.PAGERDUTY],
                "detail_level": "detailed",
                "focus": ["root cause", "affected systems", "technical steps"],
                "max_length": 500
            },
            StakeholderType.BUSINESS: {
                "channels": [NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
                "detail_level": "moderate",
                "focus": ["process impact", "workarounds", "resolution timeline"],
                "max_length": 300
            },
            StakeholderType.OPERATIONS: {
                "channels": [NotificationChannel.SLACK, NotificationChannel.SMS],
                "detail_level": "action-focused",
                "focus": ["immediate actions", "monitoring", "escalation"],
                "max_length": 250
            },
            StakeholderType.CUSTOMER: {
                "channels": [NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
                "detail_level": "simple",
                "focus": ["what happened", "what we're doing", "when it will be fixed"],
                "max_length": 150
            },
            StakeholderType.COMPLIANCE: {
                "channels": [NotificationChannel.EMAIL],
                "detail_level": "comprehensive",
                "focus": ["regulatory impact", "data affected", "remediation plan"],
                "max_length": 400
            }
        }

        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the notification workflow."""
        workflow = StateGraph(NotificationState)

        workflow.add_node("identify_stakeholders", self._identify_stakeholders)
        workflow.add_node("plan_notifications", self._plan_notifications)
        workflow.add_node("generate_messages", self._generate_messages)
        workflow.add_node("check_escalation", self._check_escalation)

        workflow.set_entry_point("identify_stakeholders")
        workflow.add_edge("identify_stakeholders", "plan_notifications")
        workflow.add_edge("plan_notifications", "generate_messages")
        workflow.add_edge("generate_messages", "check_escalation")
        workflow.add_edge("check_escalation", END)

        return workflow.compile()

    def notify(
        self,
        event_type: str,
        severity: str,
        affected_product: str,
        description: str,
        impact_summary: Optional[str] = None,
        resolution_eta: Optional[str] = None
    ) -> NotificationState:
        """
        Create and plan notifications for an event.

        Args:
            event_type: Type of event (incident, change, alert)
            severity: Event severity (critical, high, medium, low)
            affected_product: Primary affected product
            description: Event description
            impact_summary: Summary of impact
            resolution_eta: Estimated resolution time

        Returns:
            Notification state with generated messages
        """
        initial_state: NotificationState = {
            "event": {
                "type": event_type,
                "severity": severity,
                "product": affected_product,
                "description": description,
                "impact_summary": impact_summary,
                "resolution_eta": resolution_eta,
                "timestamp": datetime.now(UTC).isoformat()
            },
            "stakeholders": [],
            "notification_plan": {},
            "generated_messages": [],
            "delivery_status": {},
            "escalation_needed": False,
            "escalation_chain": [],
            "messages": [f"Starting notification process for {event_type} on {affected_product}"]
        }

        return self.workflow.invoke(initial_state)

    def _identify_stakeholders(self, state: NotificationState) -> NotificationState:
        """Identify stakeholders who need to be notified."""
        event = state["event"]
        severity = event["severity"]
        stakeholders = []

        # Severity-based stakeholder mapping
        severity_stakeholders = {
            "critical": [
                StakeholderType.EXECUTIVE,
                StakeholderType.TECHNICAL,
                StakeholderType.OPERATIONS,
                StakeholderType.COMPLIANCE
            ],
            "high": [
                StakeholderType.TECHNICAL,
                StakeholderType.OPERATIONS,
                StakeholderType.BUSINESS
            ],
            "medium": [
                StakeholderType.TECHNICAL,
                StakeholderType.BUSINESS
            ],
            "low": [
                StakeholderType.TECHNICAL
            ]
        }

        stakeholder_types = severity_stakeholders.get(severity, [StakeholderType.TECHNICAL])

        for st_type in stakeholder_types:
            prefs = self.stakeholder_preferences.get(st_type, {})
            stakeholders.append({
                "type": st_type.value,
                "channels": [c.value for c in prefs.get("channels", [])],
                "detail_level": prefs.get("detail_level", "moderate"),
                "focus_areas": prefs.get("focus", []),
                "max_length": prefs.get("max_length", 300)
            })

        # Check if customer notification needed (for customer-facing issues)
        if event.get("impact_summary") and "customer" in event.get("impact_summary", "").lower():
            if StakeholderType.CUSTOMER.value not in [s["type"] for s in stakeholders]:
                prefs = self.stakeholder_preferences[StakeholderType.CUSTOMER]
                stakeholders.append({
                    "type": StakeholderType.CUSTOMER.value,
                    "channels": [c.value for c in prefs["channels"]],
                    "detail_level": prefs["detail_level"],
                    "focus_areas": prefs["focus"],
                    "max_length": prefs["max_length"]
                })

        state["stakeholders"] = stakeholders
        state["messages"].append(
            f"Identified {len(stakeholders)} stakeholder groups: "
            f"{', '.join(s['type'] for s in stakeholders)}"
        )

        return state

    def _plan_notifications(self, state: NotificationState) -> NotificationState:
        """Plan notifications for each stakeholder type."""
        notification_plan = {}
        event = state["event"]

        for stakeholder in state["stakeholders"]:
            st_type = stakeholder["type"]
            notifications = []

            for channel in stakeholder["channels"]:
                notification = {
                    "channel": channel,
                    "priority": self._get_priority(event["severity"], channel),
                    "stakeholder_type": st_type,
                    "detail_level": stakeholder["detail_level"],
                    "focus_areas": stakeholder["focus_areas"],
                    "max_length": stakeholder["max_length"]
                }
                notifications.append(notification)

            notification_plan[st_type] = notifications

        state["notification_plan"] = notification_plan
        total_notifications = sum(len(n) for n in notification_plan.values())
        state["messages"].append(
            f"Planned {total_notifications} notifications across "
            f"{len(notification_plan)} stakeholder groups"
        )

        return state

    def _get_priority(self, severity: str, channel: str) -> str:
        """Determine notification priority based on severity and channel."""
        if severity == "critical":
            return "immediate"
        elif severity == "high":
            return "urgent" if channel in ["pagerduty", "sms"] else "high"
        elif severity == "medium":
            return "normal"
        else:
            return "low"

    def _generate_messages(self, state: NotificationState) -> NotificationState:
        """Generate tailored messages for each notification."""
        generated_messages = []
        event = state["event"]

        for st_type, notifications in state["notification_plan"].items():
            for notification in notifications:
                message = self._generate_message_for_stakeholder(
                    event,
                    notification
                )
                generated_messages.append({
                    "stakeholder_type": st_type,
                    "channel": notification["channel"],
                    "priority": notification["priority"],
                    "subject": message.get("subject", ""),
                    "body": message.get("body", ""),
                    "action_items": message.get("action_items", [])
                })

        state["generated_messages"] = generated_messages
        state["messages"].append(f"Generated {len(generated_messages)} notification messages")

        return state

    def _generate_message_for_stakeholder(
        self,
        event: Dict,
        notification: Dict
    ) -> Dict:
        """Generate a message tailored to the stakeholder type and channel."""
        if self._llm:
            prompt = f"""Generate a notification message for this event:

EVENT:
- Type: {event['type']}
- Severity: {event['severity']}
- Product: {event['product']}
- Description: {event['description']}
- Impact: {event.get('impact_summary', 'Under assessment')}
- Resolution ETA: {event.get('resolution_eta', 'TBD')}

NOTIFICATION REQUIREMENTS:
- Stakeholder Type: {notification['stakeholder_type']}
- Channel: {notification['channel']}
- Detail Level: {notification['detail_level']}
- Focus Areas: {', '.join(notification['focus_areas'])}
- Max Length: {notification['max_length']} words

Generate a message appropriate for this stakeholder and channel.
For email, include a subject line.
Include clear action items if applicable.

Return a JSON object:
{{
    "subject": "subject line (for email)",
    "body": "message body",
    "action_items": ["list of actions if any"]
}}
"""

            try:
                response = self._llm.invoke(
                    prompt,
                    system_prompt="You are an expert communications specialist creating stakeholder notifications."
                )

                if response.success and response.content:
                    json_match = response.content[
                        response.content.find("{"):response.content.rfind("}")+1
                    ]
                    return json.loads(json_match)

            except Exception as e:
                logger.warning(f"LLM message generation failed: {e}")

        # Fallback message generation
        return self._generate_fallback_message(event, notification)

    def _generate_fallback_message(self, event: Dict, notification: Dict) -> Dict:
        """Generate a fallback message without LLM."""
        st_type = notification["stakeholder_type"]
        severity = event["severity"]
        product = event["product"]

        subjects = {
            "executive": f"[{severity.upper()}] Business Impact Alert: {product}",
            "technical": f"[{severity.upper()}] Technical Incident: {product}",
            "business": f"[{severity.upper()}] Process Disruption: {product}",
            "operations": f"[ACTION REQUIRED] {severity.upper()}: {product}",
            "customer": f"Service Update: {product}",
            "compliance": f"[{severity.upper()}] Compliance Notice: {product}"
        }

        bodies = {
            "executive": (
                f"An incident affecting {product} requires attention. "
                f"Severity: {severity}. "
                f"Impact: {event.get('impact_summary', 'Under assessment')}. "
                f"Resolution ETA: {event.get('resolution_eta', 'Being determined')}."
            ),
            "technical": (
                f"Incident detected on {product}.\n"
                f"Severity: {severity}\n"
                f"Description: {event['description']}\n"
                f"Status: Active investigation"
            ),
            "business": (
                f"We're experiencing an issue with {product}. "
                f"Our team is actively working on resolution. "
                f"Expected resolution: {event.get('resolution_eta', 'TBD')}."
            ),
            "operations": (
                f"ALERT: {product} - {severity}\n"
                f"{event['description']}\n"
                f"Monitor dashboards and standby for updates."
            ),
            "customer": (
                f"We're aware of an issue affecting some services. "
                f"Our team is working to resolve this as quickly as possible. "
                f"We'll provide updates as they become available."
            ),
            "compliance": (
                f"This notice documents an incident affecting {product}. "
                f"Severity: {severity}. "
                f"Description: {event['description']}. "
                f"Remediation actions are in progress."
            )
        }

        action_items = {
            "executive": ["Review impact assessment when available"],
            "technical": ["Join incident channel", "Review affected systems", "Prepare rollback if needed"],
            "business": ["Communicate with affected teams", "Document workarounds"],
            "operations": ["Monitor system health", "Report any additional issues"],
            "customer": [],
            "compliance": ["Log this notification", "Prepare incident documentation"]
        }

        return {
            "subject": subjects.get(st_type, f"[{severity.upper()}] Alert: {product}"),
            "body": bodies.get(st_type, event["description"]),
            "action_items": action_items.get(st_type, [])
        }

    def _check_escalation(self, state: NotificationState) -> NotificationState:
        """Check if escalation is needed based on severity and timing."""
        event = state["event"]
        severity = event["severity"]

        escalation_needed = severity in ["critical", "high"]
        escalation_chain = []

        if escalation_needed:
            if severity == "critical":
                escalation_chain = [
                    "On-call engineer (immediate)",
                    "Team lead (5 min)",
                    "Engineering manager (15 min)",
                    "VP Engineering (30 min)",
                    "CTO (1 hour if unresolved)"
                ]
            else:
                escalation_chain = [
                    "On-call engineer (immediate)",
                    "Team lead (15 min)",
                    "Engineering manager (30 min)"
                ]

        state["escalation_needed"] = escalation_needed
        state["escalation_chain"] = escalation_chain

        if escalation_needed:
            state["messages"].append(
                f"Escalation enabled with {len(escalation_chain)} escalation levels"
            )
        else:
            state["messages"].append("No escalation needed for this severity level")

        return state


# Factory function
def create_notification_agent(graph_manager=None) -> StakeholderNotificationAgent:
    """Create a stakeholder notification agent instance."""
    return StakeholderNotificationAgent(graph_manager)
