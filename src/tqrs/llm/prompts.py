"""Prompt templates for LLM ticket evaluation."""

from typing import Any

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


class DescriptionPrompt:
    """Prompt for evaluating description quality (20 pts)."""

    CRITERION_ID = "accurate_description"
    MAX_SCORE = 20

    SYSTEM_PROMPT = """You are an expert IT service desk quality reviewer. Your task is to evaluate the quality of incident descriptions in ServiceNow tickets.

SCORING RUBRIC (20 points maximum):
- 20 points: Description clearly states the issue and documents ALL required items
- 15 points: 1 item incorrect/inaccurate/missing
- 10 points: 2 items incorrect/inaccurate/missing
- 5 points: 3 items incorrect/inaccurate/missing
- 0 points: 4+ items incorrect/inaccurate/missing

REQUIRED ITEMS TO CHECK:
1. Contact information and working location (office/working remotely)
2. All information relevant to the issue (error messages, screenshots mentioned, approvals, file paths, mailboxes, etc.)
3. Usernames documented where issues relate to account access
4. Domain\\Username documented for Active Directory/Domain password resets
5. Clear statement of what the issue/request is

EVALUATION GUIDELINES:
- The description should be in the incident description field
- Look for validation documentation (OKTA, employee ID, name verification)
- Check if the issue is clearly and concisely stated
- Verify relevant technical details are included

Respond with a JSON object containing your evaluation."""

    @classmethod
    def build_messages(cls, ticket: ServiceNowTicket) -> list[dict[str, str]]:
        """Build messages for description evaluation."""
        user_content = f"""Evaluate the description quality for this ticket:

{_build_ticket_context(ticket)}

Respond with this exact JSON structure:
{{
    "criterion_id": "accurate_description",
    "score": <0-20>,
    "max_score": 20,
    "completeness_score": <0-10>,
    "clarity_score": <0-10>,
    "issue_stated": <true/false>,
    "context_provided": <true/false>,
    "user_impact_noted": <true/false>,
    "evidence": ["quote1", "quote2"],
    "reasoning": "explanation of score",
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "coaching": "specific coaching recommendation"
}}"""
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class TroubleshootingPrompt:
    """Prompt for evaluating troubleshooting quality (20 pts)."""

    CRITERION_ID = "troubleshooting_quality"
    MAX_SCORE = 20

    SYSTEM_PROMPT = """You are an expert IT service desk quality reviewer. Your task is to evaluate the quality of troubleshooting documentation in ServiceNow tickets.

SCORING RUBRIC (20 points maximum):
- 20 points: Sufficient troubleshooting conducted AND documented clearly
- 15 points: Sufficient troubleshooting conducted but not sufficiently documented
- 10 points: Some troubleshooting conducted and documented
- 5 points: Limited low-level troubleshooting conducted
- 0 points: No troubleshooting conducted or no documentation of troubleshooting
- N/A: No troubleshooting was required (simple requests like password resets)

EVALUATION GUIDELINES:
- Troubleshooting steps should be clearly documented in description, work notes, or close notes
- Steps should be relevant to the reported issue
- Steps should follow a logical progression
- Outcomes of each step should be documented where applicable
- Look for actions like: restart, reset, clear cache, check settings, verify access, etc.

For simple requests (password reset, account unlock), if documented properly, award full points or N/A.

Respond with a JSON object containing your evaluation."""

    @classmethod
    def build_messages(cls, ticket: ServiceNowTicket) -> list[dict[str, str]]:
        """Build messages for troubleshooting evaluation."""
        user_content = f"""Evaluate the troubleshooting quality for this ticket:

{_build_ticket_context(ticket)}

Respond with this exact JSON structure:
{{
    "criterion_id": "troubleshooting_quality",
    "score": <0-20 or "N/A">,
    "max_score": 20,
    "steps_documented": <true/false>,
    "logical_progression": <true/false>,
    "appropriate_actions": <true/false>,
    "outcome_documented": <true/false>,
    "steps_count": <number>,
    "evidence": ["quote1", "quote2"],
    "reasoning": "explanation of score",
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "coaching": "specific coaching recommendation"
}}

If no troubleshooting was required, use "N/A" for score."""
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class ResolutionPrompt:
    """Prompt for evaluating resolution notes quality (15 pts)."""

    CRITERION_ID = "resolution_notes"
    MAX_SCORE = 15

    SYSTEM_PROMPT = """You are an expert IT service desk quality reviewer. Your task is to evaluate the quality of resolution notes in ServiceNow tickets.

SCORING RUBRIC (15 points maximum):
- 15 points: Resolution notes include ALL THREE required elements
- 10 points: Missing ONE of the required elements
- 5 points: Missing TWO of the required elements
- 0 points: No clear information on resolution OR missing confirmation
- N/A: Ticket not resolved or was routed to another team

REQUIRED ELEMENTS:
1. Summary of what was done to resolve the issue
2. Confirmation that the issue is resolved
3. Confirmation that the colleague agreed the incident can be closed

EVALUATION GUIDELINES:
- Check close_notes and work_notes for resolution documentation
- Look for explicit user confirmation (e.g., "user confirmed", "colleague verified", "working now")
- Resolution steps should be clear enough to reproduce if issue recurs
- Look for closure agreement phrases like "agreed to close", "confirmed to close"

Respond with a JSON object containing your evaluation."""

    @classmethod
    def build_messages(cls, ticket: ServiceNowTicket) -> list[dict[str, str]]:
        """Build messages for resolution evaluation."""
        user_content = f"""Evaluate the resolution notes quality for this ticket:

{_build_ticket_context(ticket)}

Respond with this exact JSON structure:
{{
    "criterion_id": "resolution_notes",
    "score": <0-15 or "N/A">,
    "max_score": 15,
    "outcome_clear": <true/false>,
    "steps_documented": <true/false>,
    "confirmation_obtained": <true/false>,
    "resolution_complete": <true/false>,
    "evidence": ["quote1", "quote2"],
    "reasoning": "explanation of score",
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "coaching": "specific coaching recommendation"
}}

If ticket was routed and not resolved, use "N/A" for score."""
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class CustomerServicePrompt:
    """Prompt for evaluating customer service quality (20 pts)."""

    CRITERION_ID = "customer_service_quality"
    MAX_SCORE = 20

    SYSTEM_PROMPT = """You are an expert IT service desk quality reviewer. Your task is to evaluate the customer service quality demonstrated in ServiceNow tickets.

SCORING RUBRIC (20 points maximum):
- 20 points: HIGH level - Friendly, polite, understands issue, responds appropriately, assists quickly and effectively, shows eagerness to help
- 15 points: GOOD level - Polite, friendly, understands issue, responds appropriately but not particularly quickly
- 10 points: ADEQUATE level - Understands issue, troubleshoots effectively, but doesn't communicate enough with colleague
- 5 points: POOR level - Not particularly friendly/helpful, may not understand issue, doesn't help effectively
- 0 points: UNACCEPTABLE - Unprofessional, rude, unhelpful, does not assist with issue

EVALUATION GUIDELINES:
- Look for professional and friendly tone in all communications
- Check for empathy towards the colleague's situation
- Verify clear communication of what is being done and why
- Look for appropriate greeting and closing messages
- Check for proper expectation setting (e.g., "this may take a few minutes")
- Look for offer of workarounds when immediate resolution isn't possible

Note: For phone tickets, evaluate based on documented interactions. For chat tickets, more direct communication is expected.

Respond with a JSON object containing your evaluation."""

    @classmethod
    def build_messages(cls, ticket: ServiceNowTicket) -> list[dict[str, str]]:
        """Build messages for customer service evaluation."""
        user_content = f"""Evaluate the customer service quality for this ticket:

{_build_ticket_context(ticket)}

Respond with this exact JSON structure:
{{
    "criterion_id": "customer_service_quality",
    "score": <0-20>,
    "max_score": 20,
    "professional_tone": <true/false>,
    "empathy_shown": <true/false>,
    "clear_communication": <true/false>,
    "proper_greeting": <true/false>,
    "proper_closing": <true/false>,
    "expectations_set": <true/false>,
    "evidence": ["quote1", "quote2"],
    "reasoning": "explanation of score",
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "coaching": "specific coaching recommendation"
}}"""
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class SpellingGrammarPrompt:
    """Prompt for evaluating spelling and grammar (2 pts)."""

    CRITERION_ID = "spelling_grammar"
    MAX_SCORE = 2

    SYSTEM_PROMPT = """You are an expert IT service desk quality reviewer. Your task is to evaluate spelling, grammar, and punctuation in ServiceNow tickets.

SCORING RUBRIC (2 points maximum):
- 2 points: Perfect or near-perfect spelling, grammar, and punctuation
- 1 point: 1-4 spelling, grammar, or punctuation mistakes
- 0 points: 5 or more mistakes

EVALUATION GUIDELINES:
- Focus on the description, work notes, and close notes fields
- Common acceptable abbreviations in IT context: VDI, LAN, MFA, OKTA, AD, etc.
- Technical terms and application names are not spelling errors
- Consider readability and professionalism
- Minor typos count as errors
- Ignore formatting issues (line breaks, bullets, etc.)

Respond with a JSON object containing your evaluation."""

    @classmethod
    def build_messages(cls, ticket: ServiceNowTicket) -> list[dict[str, str]]:
        """Build messages for spelling/grammar evaluation."""
        user_content = f"""Evaluate the spelling and grammar for this ticket:

{_build_ticket_context(ticket)}

Respond with this exact JSON structure:
{{
    "criterion_id": "spelling_grammar",
    "score": <0-2>,
    "max_score": 2,
    "error_count": <number>,
    "errors_found": ["error1", "error2"],
    "severity": "<none|minor|moderate|significant>",
    "evidence": [],
    "reasoning": "explanation of score",
    "strengths": ["strength1"],
    "improvements": ["improvement1"],
    "coaching": "specific coaching recommendation"
}}"""
        return [
            {"role": "system", "content": cls.SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


class PromptTemplates:
    """Collection of all prompt templates."""

    def __init__(self) -> None:
        self.description = DescriptionPrompt()
        self.troubleshooting = TroubleshootingPrompt()
        self.resolution = ResolutionPrompt()
        self.customer_service = CustomerServicePrompt()
        self.spelling_grammar = SpellingGrammarPrompt()

    def get_all_prompts(self) -> dict[str, Any]:
        """Get all prompt templates."""
        return {
            "description": self.description,
            "troubleshooting": self.troubleshooting,
            "resolution": self.resolution,
            "customer_service": self.customer_service,
            "spelling_grammar": self.spelling_grammar,
        }
