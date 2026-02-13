"""Prompt templates for LLM ticket evaluation - Onsite Support Review."""

from tqrs.models.ticket import ServiceNowTicket

# JSON schema for structured output
RESPONSE_SCHEMA = {"type": "json_object"}


def _build_ticket_context(ticket: ServiceNowTicket) -> str:
    """Build ticket context string for prompts."""
    parts = [
        f"Ticket Number: {ticket.number}",
        f"Contact Type: {ticket.contact_type}",
        f"Category: {ticket.category}",
        f"Subcategory: {ticket.subcategory}",
        f"Business Service: {ticket.business_service or '(not set)'}",
        f"Configuration Item: {ticket.cmdb_ci or '(not set)'}",
        f"Opened For: {ticket.opened_for or '(not set)'}",
        f"Short Description: {ticket.short_description}",
        "",
        "=== DESCRIPTION ===",
        ticket.description or "(empty)",
        "",
        "=== WORK NOTES ===",
        ticket.work_notes or "(empty)",
        "",
        "=== CLOSE NOTES ===",
        ticket.close_notes or "(empty)",
    ]
    return "\n".join(parts)


class FieldCorrectnessPrompt:
    """Prompt for evaluating field correctness (criteria 1-4, 25pts total)."""

    SYSTEM_PROMPT = """You are an expert IT service desk quality reviewer for onsite support tickets. Your task is to evaluate whether the Category, Subcategory, Service, and Configuration Item fields are correctly set for the given incident.

SCORING RUBRIC:

1. CATEGORY (5 points):
   - 5 points: Category correctly matches the type of issue (e.g., Software, Hardware, Network, Inquiry/Help)
   - 0 points: Category does not match the incident

2. SUBCATEGORY (5 points):
   - 5 points: Subcategory correctly narrows the category (e.g., Operating System, Email, Printing)
   - 0 points: Subcategory does not match or is too generic

3. SERVICE (5 points):
   - 5 points: Correct business service selected for the incident
   - 2 points: Service is related but a better/more specific service was available
   - 0 points: Incorrect service selected or no service set

4. CONFIGURATION ITEM (10 points):
   - 10 points: Correct CI (device, application, system) identified
   - 5 points: CI is related but a more specific/appropriate CI was available
   - 0 points: Incorrect CI selected or no CI set

EVALUATION GUIDELINES:
- Assess based on the incident description and context
- Consider what the actual issue is about when evaluating field selections
- Service and CI should be specific to the affected system/application
- If no Service or CI is set, score 0 for that criterion

Respond with a JSON object containing your evaluation."""

    @classmethod
    def build_messages(cls, ticket: ServiceNowTicket) -> list[dict[str, str]]:
        user_content = f"""Evaluate the field correctness for this ticket:

{_build_ticket_context(ticket)}

Respond with this exact JSON structure:
{{
    "category_score": <5 or 0>,
    "category_reasoning": "explanation",
    "subcategory_score": <5 or 0>,
    "subcategory_reasoning": "explanation",
    "service_score": <5, 2, or 0>,
    "service_reasoning": "explanation",
    "ci_score": <10, 5, or 0>,
    "ci_reasoning": "explanation",
    "evidence": ["evidence1", "evidence2"],
    "coaching": "overall coaching recommendation"
}}"""
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class IncidentNotesPrompt:
    """Prompt for evaluating incident notes quality (20 pts)."""

    CRITERION_ID = "incident_notes"
    MAX_SCORE = 20

    SYSTEM_PROMPT = """You are an expert IT service desk quality reviewer for onsite support tickets. Your task is to evaluate the quality of incident documentation (description, work notes).

SCORING RUBRIC (20 points):
- 20 points (Meets Standards): All relevant information documented clearly in appropriate fields. Includes: contact information, working location, issue details, troubleshooting steps, error messages, affected systems.
- 10 points (Partially Meets Standards): Some information documented but with gaps, OR information is in the wrong fields (e.g., troubleshooting steps in description instead of work notes).
- 0 points (Does Not Meet Standards): No meaningful notes, or very limited documentation that doesn't describe the issue or actions taken.
- 20 points (N/A): Quick fix where all relevant information is captured in the resolution notes (e.g., simple password reset with proper documentation in close notes).

EVALUATION GUIDELINES:
- Check description for: contact info, working location, clear issue statement, relevant details
- Check work notes for: troubleshooting steps, actions taken, outcomes
- Information should be in the appropriate field (description for initial info, work notes for ongoing work)
- For simple requests (password reset, account unlock), N/A is appropriate if resolution notes cover it

Respond with a JSON object containing your evaluation."""

    @classmethod
    def build_messages(cls, ticket: ServiceNowTicket) -> list[dict[str, str]]:
        user_content = f"""Evaluate the incident notes quality for this ticket:

{_build_ticket_context(ticket)}

Respond with this exact JSON structure:
{{
    "criterion_id": "incident_notes",
    "score": <0, 10, or 20>,
    "max_score": 20,
    "location_documented": <true/false>,
    "contact_info_present": <true/false>,
    "relevant_details_present": <true/false>,
    "troubleshooting_documented": <true/false>,
    "appropriate_field_usage": <true/false>,
    "evidence": ["quote1", "quote2"],
    "reasoning": "explanation of score",
    "coaching": "specific coaching recommendation"
}}"""
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class IncidentHandlingPrompt:
    """Prompt for evaluating incident handling (15 pts)."""

    CRITERION_ID = "incident_handling"
    MAX_SCORE = 15

    SYSTEM_PROMPT = """You are an expert IT service desk quality reviewer for onsite support tickets. Your task is to evaluate whether the incident was handled correctly.

SCORING RUBRIC (15 points):
- 15 points (Correct Handling): Incident was resolved appropriately at the service desk level, OR routed to the correct resolver group when escalation was needed.
- 0 points (Incorrect Handling): First Contact Resolution (FCR) opportunity was missed (could have been resolved but was escalated), OR routed to the wrong team, OR resolved prematurely without proper confirmation.
- 15 points (N/A): Handling assessment is not applicable for this ticket type.

EVALUATION GUIDELINES:
- Consider whether the analyst exhausted appropriate troubleshooting before escalating
- Check if the routing group matches the type of issue
- Look for signs of premature resolution (closing without confirmation)
- Simple issues (password reset, account unlock) should be resolved at first contact
- Complex issues (hardware failure, network infrastructure) may legitimately need escalation

Respond with a JSON object containing your evaluation."""

    @classmethod
    def build_messages(cls, ticket: ServiceNowTicket) -> list[dict[str, str]]:
        user_content = f"""Evaluate the incident handling for this ticket:

{_build_ticket_context(ticket)}

Respond with this exact JSON structure:
{{
    "criterion_id": "incident_handling",
    "score": <0 or 15>,
    "max_score": 15,
    "routed_correctly": <true/false>,
    "resolved_appropriately": <true/false>,
    "fcr_opportunity_missed": <true/false>,
    "evidence": ["quote1", "quote2"],
    "reasoning": "explanation of score",
    "coaching": "specific coaching recommendation"
}}"""
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class ResolutionNotesPrompt:
    """Prompt for evaluating resolution notes quality (20 pts)."""

    CRITERION_ID = "resolution_notes"
    MAX_SCORE = 20

    SYSTEM_PROMPT = """You are an expert IT service desk quality reviewer for onsite support tickets. Your task is to evaluate the quality of resolution notes (close notes).

SCORING RUBRIC (20 points):
- 20 points (Meets Standards): Resolution notes include BOTH: (1) Summary of what was done to resolve the issue, AND (2) Confirmation that the colleague confirmed the issue is resolved.
- 10 points (Partially Meets Standards): Missing EITHER the resolution summary OR the user confirmation (but has one of them).
- 0 points (Does Not Meet Standards): Missing BOTH resolution summary AND user confirmation, or close notes are empty/meaningless.
- 20 points (N/A): Ticket is still Work In Progress (WIP), was routed to a different team for resolution, or was resolved via automated tool (e.g., AskLen).

EVALUATION GUIDELINES:
- Check close_notes for a clear summary of the resolution steps
- Look for explicit user confirmation phrases: "user confirmed", "colleague verified", "working now", "agreed to close"
- WIP tickets or tickets routed to other teams should get N/A (20 points)
- Resolution notes should be clear enough to reproduce the fix if the issue recurs

Respond with a JSON object containing your evaluation."""

    @classmethod
    def build_messages(cls, ticket: ServiceNowTicket) -> list[dict[str, str]]:
        user_content = f"""Evaluate the resolution notes quality for this ticket:

{_build_ticket_context(ticket)}

Respond with this exact JSON structure:
{{
    "criterion_id": "resolution_notes",
    "score": <0, 10, or 20>,
    "max_score": 20,
    "summary_present": <true/false>,
    "confirmation_present": <true/false>,
    "is_wip_or_routed": <true/false>,
    "evidence": ["quote1", "quote2"],
    "reasoning": "explanation of score",
    "coaching": "specific coaching recommendation"
}}"""
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
