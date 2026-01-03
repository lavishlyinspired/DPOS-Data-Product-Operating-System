"""
DPOS LLM-Powered Agent Tools
Advanced tools that use LLM for reasoning, analysis, and recommendations.
"""
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from datetime import datetime, UTC

from src.core.llm import get_llm, get_llm_if_available, with_llm_fallback, LLMResponse
from src.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Input/Output Models
# =============================================================================

class RootCauseAnalysisInput(BaseModel):
    """Input for root cause analysis."""
    incident_id: str = Field(description="The incident ID to analyze")
    incident_type: str = Field(description="Type of incident (e.g., contract_violation)")
    description: str = Field(description="Incident description")
    affected_product: str = Field(description="Name of affected product")
    severity: str = Field(description="Incident severity level")
    violation_details: Optional[str] = Field(default=None, description="Details of the violation")
    historical_incidents: Optional[List[Dict]] = Field(default=None, description="Similar past incidents")


class SeverityAssessmentInput(BaseModel):
    """Input for severity reassessment."""
    incident_id: str = Field(description="The incident ID")
    current_severity: str = Field(description="Current severity level")
    downstream_count: int = Field(description="Number of downstream products affected")
    affected_users: int = Field(description="Number of users affected")
    has_fallback: bool = Field(description="Whether fallback is available")
    business_context: Optional[str] = Field(default=None, description="Business context")


class RemediationPlanInput(BaseModel):
    """Input for remediation planning."""
    incident_type: str = Field(description="Type of incident")
    root_cause: str = Field(description="Root cause analysis result")
    severity: str = Field(description="Incident severity")
    affected_systems: List[str] = Field(description="List of affected systems/products")
    available_resources: Optional[List[str]] = Field(default=None, description="Available resources")


class IncidentNarrativeInput(BaseModel):
    """Input for incident narrative generation."""
    incident: Dict = Field(description="Incident details")
    impact_analysis: Dict = Field(description="Impact analysis results")
    actions_taken: List[str] = Field(description="Actions taken so far")


# =============================================================================
# Root Cause Analysis Tool
# =============================================================================

ROOT_CAUSE_PROMPT = """You are a data quality expert analyzing an incident. Based on the following information, provide a root cause analysis.

Incident Details:
- ID: {incident_id}
- Type: {incident_type}
- Description: {description}
- Affected Product: {affected_product}
- Severity: {severity}
{violation_details}
{historical_context}

Analyze and provide:
1. Most likely root cause (one sentence)
2. Contributing factors (2-3 bullet points)
3. Confidence level (high/medium/low)
4. Evidence supporting this conclusion

Format your response as:
ROOT_CAUSE: <one sentence summary>
FACTORS:
- <factor 1>
- <factor 2>
- <factor 3>
CONFIDENCE: <high/medium/low>
EVIDENCE: <brief evidence summary>
"""


def _fallback_root_cause_analysis(input_data: RootCauseAnalysisInput) -> Dict[str, Any]:
    """Fallback root cause analysis using rules."""
    root_cause = "unknown"
    confidence = "low"
    factors = []

    if "null" in input_data.description.lower():
        root_cause = "Data quality issue: unexpected null values in required fields"
        factors.append("Upstream data source may have schema changes")
        confidence = "medium"
    elif "pattern" in input_data.description.lower():
        root_cause = "Data format violation: values don't match expected patterns"
        factors.append("Data transformation or ETL issue")
        confidence = "medium"
    elif "timeout" in input_data.description.lower():
        root_cause = "Infrastructure issue: service timeout or connectivity problem"
        factors.append("Network or database performance degradation")
        confidence = "medium"
    else:
        root_cause = f"Data issue detected in {input_data.affected_product}"
        factors.append("Requires manual investigation")

    return {
        "root_cause": root_cause,
        "factors": factors,
        "confidence": confidence,
        "evidence": f"Based on incident type: {input_data.incident_type}",
        "method": "rule_based"
    }


@tool
def analyze_root_cause(
    incident_id: str,
    incident_type: str,
    description: str,
    affected_product: str,
    severity: str,
    violation_details: str = "",
    historical_incidents: List[Dict] = None
) -> Dict[str, Any]:
    """
    Analyze the root cause of an incident using LLM reasoning.

    Returns a structured analysis with root cause, contributing factors,
    confidence level, and supporting evidence.
    """
    input_data = RootCauseAnalysisInput(
        incident_id=incident_id,
        incident_type=incident_type,
        description=description,
        affected_product=affected_product,
        severity=severity,
        violation_details=violation_details,
        historical_incidents=historical_incidents or []
    )

    llm = get_llm_if_available()
    if not llm:
        logger.info("LLM not available, using rule-based root cause analysis")
        return _fallback_root_cause_analysis(input_data)

    try:
        # Prepare context
        violation_ctx = f"Violation Details: {violation_details}" if violation_details else ""
        historical_ctx = ""
        if historical_incidents:
            historical_ctx = "Historical Similar Incidents:\n" + "\n".join(
                f"- {inc.get('id')}: {inc.get('description', 'N/A')}"
                for inc in historical_incidents[:3]
            )

        prompt = ROOT_CAUSE_PROMPT.format(
            incident_id=incident_id,
            incident_type=incident_type,
            description=description,
            affected_product=affected_product,
            severity=severity,
            violation_details=violation_ctx,
            historical_context=historical_ctx
        )

        response = llm.invoke(prompt)
        result = _parse_root_cause_response(response.content)
        result["method"] = "llm"
        result["model"] = response.model

        logger.info(f"Root cause analysis completed for {incident_id}", extra={"confidence": result.get("confidence")})
        return result

    except Exception as e:
        logger.warning(f"LLM root cause analysis failed: {e}, using fallback")
        return _fallback_root_cause_analysis(input_data)


def _parse_root_cause_response(content: str) -> Dict[str, Any]:
    """Parse LLM response into structured format."""
    result = {
        "root_cause": "",
        "factors": [],
        "confidence": "medium",
        "evidence": ""
    }

    lines = content.strip().split("\n")
    current_section = None

    for line in lines:
        line = line.strip()
        if line.startswith("ROOT_CAUSE:"):
            result["root_cause"] = line.replace("ROOT_CAUSE:", "").strip()
        elif line.startswith("FACTORS:"):
            current_section = "factors"
        elif line.startswith("CONFIDENCE:"):
            result["confidence"] = line.replace("CONFIDENCE:", "").strip().lower()
        elif line.startswith("EVIDENCE:"):
            result["evidence"] = line.replace("EVIDENCE:", "").strip()
        elif line.startswith("-") and current_section == "factors":
            result["factors"].append(line[1:].strip())

    # If parsing failed, use the whole response
    if not result["root_cause"]:
        result["root_cause"] = content[:200]

    return result


# =============================================================================
# Severity Reassessment Tool
# =============================================================================

SEVERITY_PROMPT = """You are assessing the severity of a data incident. Consider all factors to determine the appropriate severity level.

Current Assessment:
- Incident ID: {incident_id}
- Current Severity: {current_severity}
- Downstream Products Affected: {downstream_count}
- Users Affected: {affected_users}
- Fallback Available: {has_fallback}
{business_context}

Severity Levels:
- critical: Immediate business impact, customer-facing, no fallback
- high: Significant impact, multiple downstream dependencies, urgent attention needed
- medium: Moderate impact, workarounds available, attention needed within hours
- low: Minor impact, minimal downstream effects, can be addressed in normal workflow

Provide your assessment:
SEVERITY: <critical/high/medium/low>
REASONING: <one paragraph explaining why>
URGENCY: <immediate/hours/day/week>
ESCALATION: <yes/no> - should this be escalated to leadership?
"""


def _fallback_severity_assessment(input_data: SeverityAssessmentInput) -> Dict[str, Any]:
    """Fallback severity assessment using rules."""
    # Simple rule-based assessment
    if input_data.downstream_count > 10 or input_data.affected_users > 100:
        severity = "critical"
        urgency = "immediate"
    elif input_data.downstream_count > 5 or input_data.affected_users > 50:
        severity = "high"
        urgency = "hours"
    elif input_data.downstream_count > 2 or input_data.affected_users > 10:
        severity = "medium"
        urgency = "day"
    else:
        severity = "low"
        urgency = "week"

    # Adjust if fallback available
    if input_data.has_fallback and severity in ["critical", "high"]:
        severity = "high" if severity == "critical" else "medium"

    return {
        "original_severity": input_data.current_severity,
        "assessed_severity": severity,
        "changed": severity != input_data.current_severity,
        "urgency": urgency,
        "escalation_needed": severity in ["critical", "high"],
        "reasoning": f"Based on {input_data.downstream_count} downstream products and {input_data.affected_users} affected users",
        "method": "rule_based"
    }


@tool
def reassess_severity(
    incident_id: str,
    current_severity: str,
    downstream_count: int,
    affected_users: int,
    has_fallback: bool,
    business_context: str = ""
) -> Dict[str, Any]:
    """
    Reassess incident severity using LLM analysis of impact factors.

    Returns updated severity recommendation with reasoning.
    """
    input_data = SeverityAssessmentInput(
        incident_id=incident_id,
        current_severity=current_severity,
        downstream_count=downstream_count,
        affected_users=affected_users,
        has_fallback=has_fallback,
        business_context=business_context
    )

    llm = get_llm_if_available()
    if not llm:
        return _fallback_severity_assessment(input_data)

    try:
        business_ctx = f"Business Context: {business_context}" if business_context else ""

        prompt = SEVERITY_PROMPT.format(
            incident_id=incident_id,
            current_severity=current_severity,
            downstream_count=downstream_count,
            affected_users=affected_users,
            has_fallback=has_fallback,
            business_context=business_ctx
        )

        response = llm.invoke(prompt)
        result = _parse_severity_response(response.content, current_severity)
        result["method"] = "llm"

        return result

    except Exception as e:
        logger.warning(f"LLM severity assessment failed: {e}")
        return _fallback_severity_assessment(input_data)


def _parse_severity_response(content: str, original: str) -> Dict[str, Any]:
    """Parse severity assessment response."""
    result = {
        "original_severity": original,
        "assessed_severity": original,
        "changed": False,
        "urgency": "day",
        "escalation_needed": False,
        "reasoning": ""
    }

    for line in content.strip().split("\n"):
        line = line.strip()
        if line.startswith("SEVERITY:"):
            severity = line.replace("SEVERITY:", "").strip().lower()
            if severity in ["critical", "high", "medium", "low"]:
                result["assessed_severity"] = severity
                result["changed"] = severity != original
        elif line.startswith("REASONING:"):
            result["reasoning"] = line.replace("REASONING:", "").strip()
        elif line.startswith("URGENCY:"):
            result["urgency"] = line.replace("URGENCY:", "").strip().lower()
        elif line.startswith("ESCALATION:"):
            result["escalation_needed"] = "yes" in line.lower()

    return result


# =============================================================================
# Remediation Planning Tool
# =============================================================================

REMEDIATION_PROMPT = """You are a data platform expert creating a remediation plan for an incident.

Incident Information:
- Type: {incident_type}
- Root Cause: {root_cause}
- Severity: {severity}
- Affected Systems: {affected_systems}
{resources}

Create a prioritized remediation plan with clear, actionable steps.

Format:
IMMEDIATE_ACTIONS:
1. <first immediate action>
2. <second immediate action>

SHORT_TERM_FIXES:
1. <fix to apply within hours>
2. <another short-term fix>

PREVENTIVE_MEASURES:
1. <measure to prevent recurrence>
2. <another preventive measure>

ESTIMATED_RESOLUTION: <time estimate>
REQUIRED_EXPERTISE: <skills/teams needed>
"""


def _fallback_remediation_plan(input_data: RemediationPlanInput) -> Dict[str, Any]:
    """Fallback remediation planning."""
    immediate = ["Notify affected stakeholders", "Begin impact assessment"]
    short_term = ["Investigate root cause", "Prepare fix"]
    preventive = ["Review monitoring", "Update documentation"]

    if input_data.severity == "critical":
        immediate.insert(0, "URGENT: Activate incident response team")
        immediate.append("Consider activating fallback systems")

    return {
        "immediate_actions": immediate,
        "short_term_fixes": short_term,
        "preventive_measures": preventive,
        "estimated_resolution": "2-4 hours" if input_data.severity in ["critical", "high"] else "1-2 days",
        "required_expertise": ["Data Engineering", "Platform Team"],
        "method": "rule_based"
    }


@tool
def create_remediation_plan(
    incident_type: str,
    root_cause: str,
    severity: str,
    affected_systems: List[str],
    available_resources: List[str] = None
) -> Dict[str, Any]:
    """
    Create a detailed remediation plan using LLM reasoning.

    Returns prioritized actions for immediate, short-term, and preventive measures.
    """
    input_data = RemediationPlanInput(
        incident_type=incident_type,
        root_cause=root_cause,
        severity=severity,
        affected_systems=affected_systems,
        available_resources=available_resources
    )

    llm = get_llm_if_available()
    if not llm:
        return _fallback_remediation_plan(input_data)

    try:
        resources_ctx = f"Available Resources: {', '.join(available_resources)}" if available_resources else ""

        prompt = REMEDIATION_PROMPT.format(
            incident_type=incident_type,
            root_cause=root_cause,
            severity=severity,
            affected_systems=", ".join(affected_systems),
            resources=resources_ctx
        )

        response = llm.invoke(prompt)
        result = _parse_remediation_response(response.content)
        result["method"] = "llm"

        return result

    except Exception as e:
        logger.warning(f"LLM remediation planning failed: {e}")
        return _fallback_remediation_plan(input_data)


def _parse_remediation_response(content: str) -> Dict[str, Any]:
    """Parse remediation plan response."""
    result = {
        "immediate_actions": [],
        "short_term_fixes": [],
        "preventive_measures": [],
        "estimated_resolution": "",
        "required_expertise": []
    }

    current_section = None
    for line in content.strip().split("\n"):
        line = line.strip()
        if "IMMEDIATE_ACTIONS" in line:
            current_section = "immediate_actions"
        elif "SHORT_TERM" in line:
            current_section = "short_term_fixes"
        elif "PREVENTIVE" in line:
            current_section = "preventive_measures"
        elif line.startswith("ESTIMATED_RESOLUTION:"):
            result["estimated_resolution"] = line.replace("ESTIMATED_RESOLUTION:", "").strip()
        elif line.startswith("REQUIRED_EXPERTISE:"):
            expertise = line.replace("REQUIRED_EXPERTISE:", "").strip()
            result["required_expertise"] = [e.strip() for e in expertise.split(",")]
        elif line and line[0].isdigit() and current_section:
            # Remove numbering and add to appropriate list
            action = line.split(".", 1)[-1].strip() if "." in line else line
            result[current_section].append(action)

    return result


# =============================================================================
# Incident Narrative Generator Tool
# =============================================================================

NARRATIVE_PROMPT = """Generate a clear, professional incident narrative for stakeholder communication.

Incident Details:
{incident_details}

Impact Analysis:
{impact_details}

Actions Taken:
{actions}

Generate a narrative that includes:
1. Executive Summary (2-3 sentences)
2. Timeline of Events
3. Business Impact
4. Current Status
5. Next Steps

Keep the tone professional and factual.
"""


@tool
def generate_incident_narrative(
    incident: Dict,
    impact_analysis: Dict,
    actions_taken: List[str]
) -> Dict[str, str]:
    """
    Generate a human-readable incident narrative for stakeholder communication.

    Returns formatted narrative suitable for email/Slack notifications.
    """
    llm = get_llm_if_available()

    # Prepare incident details
    incident_text = f"""
    - ID: {incident.get('id', 'N/A')}
    - Type: {incident.get('type', 'N/A')}
    - Severity: {incident.get('severity', 'N/A')}
    - Product: {incident.get('product_name', 'N/A')}
    - Description: {incident.get('description', 'N/A')}
    - Status: {incident.get('status', 'N/A')}
    """

    impact_text = f"""
    - Downstream Products: {impact_analysis.get('downstream_count', 0)}
    - Affected Users: {impact_analysis.get('affected_users', 0)}
    - Risk Score: {impact_analysis.get('risk_score', 'N/A')}
    """

    actions_text = "\n".join(f"- {action}" for action in actions_taken)

    if llm:
        try:
            prompt = NARRATIVE_PROMPT.format(
                incident_details=incident_text,
                impact_details=impact_text,
                actions=actions_text
            )
            response = llm.invoke(prompt)
            return {
                "narrative": response.content,
                "method": "llm"
            }
        except Exception as e:
            logger.warning(f"LLM narrative generation failed: {e}")

    # Fallback template
    narrative = f"""
**Incident Report: {incident.get('id', 'N/A')}**

**Summary:** A {incident.get('severity', 'N/A')} severity incident has been detected in {incident.get('product_name', 'the system')}.

**Details:**
{incident.get('description', 'No description available.')}

**Impact:**
- {impact_analysis.get('downstream_count', 0)} downstream products affected
- {impact_analysis.get('affected_users', 0)} users potentially impacted

**Actions Taken:**
{actions_text or '- Investigation in progress'}

**Status:** {incident.get('status', 'Under Investigation')}

**Next Steps:** The team is actively working on resolution. Updates will be provided as available.
"""

    return {
        "narrative": narrative.strip(),
        "method": "template"
    }


# =============================================================================
# Export all tools
# =============================================================================

def get_llm_tools():
    """Get all LLM-powered tools for agent use."""
    return [
        analyze_root_cause,
        reassess_severity,
        create_remediation_plan,
        generate_incident_narrative
    ]
