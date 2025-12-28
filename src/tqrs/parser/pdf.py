"""PDF parser for ServiceNow incident reports.

Extracts ticket data from ServiceNow PDF exports.
"""

import re
from datetime import datetime
from io import BytesIO

import pdfplumber

from tqrs.models.ticket import ServiceNowTicket


class PDFParser:
    """Parse ServiceNow incident PDFs into ticket objects."""

    # Field patterns for extraction (label: regex pattern)
    # These patterns match up to common field terminators (next label or newline)
    FIELD_PATTERNS = {
        "number": r"Number:\s*(INC\d+)",
        "opened_for": r"Opened for:\s*([^\n]+?)(?=\s*(?:Location:|Contact type:|$))",
        "location": r"Location:\s*([^\n]+?)(?=\s*(?:Category:|State:|$))",
        "category": r"Category:\s*([^\n]+?)(?=\s*(?:Subcategory:|On hold|$))",
        "subcategory": r"Subcategory:\s*([^\n]+?)(?=\s*(?:Service:|Impact:|$))",
        "contact_type": r"Contact type:\s*(\w+(?:[-\s]\w+)?)",
        "priority": r"Priority:\s*(\d+[^\n]*?)(?=\s*(?:Assignment|$))",
        "state": r"State:\s*(\w+)",
        "assigned_to": r"Assigned to:\s*([^\n]+?)(?=\s*(?:Short|$))",
        "assignment_group": r"Assignment group:\s*([^\n]+?)(?=\s*(?:Assigned to:|$))",
        "configuration_item": r"Configuration item:\s*([^\n]+?)(?=\s*(?:MMC|Universal|$))",
        "business_service": r"(?<![:\w])Service:\s*([^\n]+?)(?=\s*(?:Service offering:|$))",
        "opened_at": r"Opened:\s*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AP]M)?)",
        "resolved_at": r"Resolved:\s*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AP]M)?)",
        "closed_at": r"Closed:\s*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AP]M)?)",
        "close_code": r"Resolution code:\s*([^\n]+?)(?=\s*(?:Resolved by:|$))",
        "impact": r"Impact:\s*(\d+[^\n]*?)(?=\s*(?:Urgency:|$))",
        "urgency": r"Urgency:\s*(\d+[^\n]*?)(?=\s*(?:Priority:|$))",
    }

    # Multi-line field patterns (these need special handling)
    MULTILINE_FIELDS = {
        "short_description": r"Short description:\s*\n(.+?)(?=\nDescription:|$)",
        "description": r"Description:\s*\n([\s\S]+?)(?=\nUpdated:|Notes|Work notes:|Additional comments:|$)",
        "close_notes": r"Resolution notes:\s*\n([\s\S]+?)(?=\nMajor Incident|Related|Variables|$)",
        "work_notes": r"Work notes:\s*\n([\s\S]+?)(?=\nVariables|Related|Resolution|$)",
        "additional_comments": r"Additional comments:\s*\n([\s\S]+?)(?=\nWork notes:|Variables|Related|$)",
    }

    def parse_file(self, file_path: str) -> ServiceNowTicket | None:
        """Parse a PDF file into a ServiceNowTicket.

        Args:
            file_path: Path to the PDF file.

        Returns:
            ServiceNowTicket object or None if parsing fails.
        """
        with pdfplumber.open(file_path) as pdf:
            text = self._extract_text(pdf)
        return self._parse_text(text)

    def parse_bytes(self, pdf_bytes: BytesIO) -> ServiceNowTicket | None:
        """Parse PDF bytes into a ServiceNowTicket.

        Args:
            pdf_bytes: BytesIO object containing PDF data.

        Returns:
            ServiceNowTicket object or None if parsing fails.
        """
        with pdfplumber.open(pdf_bytes) as pdf:
            text = self._extract_text(pdf)
        return self._parse_text(text)

    def _extract_text(self, pdf: pdfplumber.PDF) -> str:
        """Extract all text from PDF pages."""
        text_parts = []
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)

    def _parse_text(self, text: str) -> ServiceNowTicket | None:
        """Parse extracted text into a ServiceNowTicket."""
        if not text:
            return None

        # Extract fields
        fields = {}

        # Single-line fields
        for field_name, pattern in self.FIELD_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields[field_name] = match.group(1).strip()

        # Multi-line fields
        for field_name, pattern in self.MULTILINE_FIELDS.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                # Clean up the value
                value = self._clean_multiline_text(value)
                fields[field_name] = value

        # Validate we have minimum required fields
        if not fields.get("number"):
            return None

        # Build the ticket
        return self._build_ticket(fields)

    def _clean_multiline_text(self, text: str) -> str:
        """Clean up multi-line text extracted from PDF."""
        # Remove page headers/footers that might be mixed in
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            # Skip lines that look like headers/footers
            if re.match(r"^(Run By|Page \d|Incident Details)", line, re.IGNORECASE):
                continue
            # Skip timestamp lines at start of comments
            if re.match(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}", line):
                # Keep these - they're part of work notes
                pass
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    def _extract_priority_number(self, priority_str: str) -> str:
        """Extract priority number from string like '5 - Minimal'."""
        match = re.match(r"(\d+)", priority_str)
        return match.group(1) if match else "3"

    def _extract_impact_urgency(self, value_str: str) -> str:
        """Extract impact/urgency number from string like '3 - Low'."""
        match = re.match(r"(\d+)", value_str)
        return match.group(1) if match else "3"

    def _extract_state_value(self, state_str: str) -> str:
        """Convert state string to numeric value."""
        state_map = {
            "new": "1",
            "in progress": "2",
            "on hold": "3",
            "resolved": "6",
            "closed": "7",
        }
        state_lower = state_str.lower().strip()
        return state_map.get(state_lower, "7")  # Default to closed

    def _build_ticket(self, fields: dict) -> ServiceNowTicket:
        """Build ServiceNowTicket from extracted fields."""
        # Extract priority number
        priority_str = fields.get("priority", "3")
        priority = self._extract_priority_number(priority_str)

        # Extract impact and urgency
        impact = self._extract_impact_urgency(fields.get("impact", "3"))
        urgency = self._extract_impact_urgency(fields.get("urgency", "3"))

        # Normalize contact type
        contact_type = fields.get("contact_type", "").lower().strip()
        if contact_type not in ("phone", "email", "chat", "self-service", "walk-in"):
            contact_type = "email"  # Default

        # Get state values
        state_str = fields.get("state", "Closed")
        state = self._extract_state_value(state_str)

        # Parse dates
        opened_at = self._parse_date(fields.get("opened_at", ""))
        resolved_at = self._parse_date(fields.get("resolved_at", ""))
        closed_at = self._parse_date(fields.get("closed_at", ""))

        # Default opened_at to now if not found
        if opened_at is None:
            opened_at = datetime.now()

        return ServiceNowTicket(
            # Identifiers
            number=fields.get("number", ""),
            sys_id=f"pdf-{fields.get('number', 'unknown')}",
            # Timestamps
            opened_at=opened_at,
            resolved_at=resolved_at,
            closed_at=closed_at,
            # People
            caller_id=fields.get("opened_for", "unknown"),
            opened_by=fields.get("opened_for", "unknown"),
            assigned_to=fields.get("assigned_to", ""),
            resolved_by=fields.get("assigned_to", ""),
            # Classification
            category=fields.get("category", ""),
            subcategory=fields.get("subcategory", ""),
            contact_type=contact_type,
            priority=priority,
            impact=impact,
            urgency=urgency,
            # Content
            short_description=fields.get("short_description", ""),
            description=fields.get("description", ""),
            work_notes=fields.get("work_notes", ""),
            close_notes=fields.get("close_notes", ""),
            close_code=fields.get("close_code", ""),
            # Status
            state=state,
            incident_state=state,
            # Business context
            company="pdf-import",
            location=fields.get("location", ""),
            assignment_group=fields.get("assignment_group", ""),
            business_service=fields.get("business_service", ""),
            cmdb_ci=fields.get("configuration_item", ""),
            # LoB flags default to false for PDF imports
            u_marsh=False,
            u_mercer=False,
            u_guy_carpenter=False,
            u_oliver_wyman_group=False,
            u_mmc_corporate=False,
        )

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date string from PDF into datetime object."""
        if not date_str:
            return None

        # Try various date formats
        formats = [
            "%m/%d/%Y %I:%M %p",      # 12/16/2025 11:45 PM
            "%m/%d/%Y %I:%M:%S %p",   # 12/16/2025 11:45:00 PM
            "%m/%d/%Y %H:%M",         # 12/16/2025 23:45
            "%m/%d/%Y %H:%M:%S",      # 12/16/2025 23:45:00
            "%Y-%m-%d %H:%M:%S",      # 2025-12-16 23:45:00
            "%m/%d/%Y",               # 12/16/2025
        ]

        # Clean the string
        date_str = date_str.strip()

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try to extract just the date/time part if there's extra text
        match = re.search(r"(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AP]M)?)", date_str, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            for fmt in formats:
                try:
                    return datetime.strptime(extracted, fmt)
                except ValueError:
                    continue

        return None
