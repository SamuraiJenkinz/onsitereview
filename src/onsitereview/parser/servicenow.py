"""ServiceNow JSON parser for onsitereview."""

import json
import logging
from datetime import datetime
from pathlib import Path

from onsitereview.models.ticket import ServiceNowTicket

logger = logging.getLogger(__name__)

# ServiceNow datetime format
SERVICENOW_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class ServiceNowParser:
    """Parse ServiceNow JSON exports into ticket models."""

    def parse_file(self, path: Path) -> list[ServiceNowTicket]:
        """Parse JSON file containing ServiceNow records.

        Args:
            path: Path to JSON file

        Returns:
            List of parsed ServiceNowTicket objects

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is invalid JSON
            ValueError: If JSON structure is invalid
        """
        logger.info(f"Parsing ServiceNow JSON file: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return self.parse_json(data)

    def parse_json(self, data: dict) -> list[ServiceNowTicket]:
        """Parse JSON dict containing ServiceNow records.

        Args:
            data: Dictionary with 'records' key containing ticket list

        Returns:
            List of parsed ServiceNowTicket objects

        Raises:
            ValueError: If data doesn't contain 'records' key
        """
        if "records" not in data:
            raise ValueError("JSON data must contain 'records' key")

        records = data["records"]
        logger.info(f"Found {len(records)} records in JSON data")

        tickets = []
        for i, raw in enumerate(records):
            # Skip failed records
            if raw.get("__status") != "success":
                logger.warning(f"Skipping record {i}: status is {raw.get('__status')}")
                continue

            try:
                ticket = self._parse_ticket(raw)
                tickets.append(ticket)
            except Exception as e:
                logger.error(f"Failed to parse record {i} ({raw.get('number', 'unknown')}): {e}")
                raise

        logger.info(f"Successfully parsed {len(tickets)} tickets")
        return tickets

    def _parse_ticket(self, raw: dict) -> ServiceNowTicket:
        """Parse single ticket record into model.

        Args:
            raw: Raw ticket dictionary from JSON

        Returns:
            Parsed ServiceNowTicket
        """
        # Parse timestamps
        opened_at = self._parse_datetime(raw.get("opened_at", ""))
        resolved_at = self._parse_datetime(raw.get("resolved_at", ""))
        closed_at = self._parse_datetime(raw.get("closed_at", ""))

        # Compute resolution time
        resolution_time = None
        if opened_at and resolved_at:
            resolution_time = self._compute_resolution_time(opened_at, resolved_at)

        # Extract line of business
        line_of_business = self._extract_line_of_business(raw)

        ticket = ServiceNowTicket(
            # Identifiers
            number=raw.get("number", ""),
            sys_id=raw.get("sys_id", ""),
            # Timestamps
            opened_at=opened_at,
            resolved_at=resolved_at,
            closed_at=closed_at,
            # People
            caller_id=raw.get("caller_id", ""),
            opened_by=raw.get("opened_by", ""),
            opened_for=raw.get("opened_for", ""),
            assigned_to=raw.get("assigned_to", ""),
            resolved_by=raw.get("resolved_by", "") or None,
            closed_by=raw.get("closed_by", "") or None,
            # Classification
            category=raw.get("category", ""),
            subcategory=raw.get("subcategory", ""),
            contact_type=raw.get("contact_type", ""),
            priority=raw.get("priority", ""),
            impact=raw.get("impact", ""),
            urgency=raw.get("urgency", ""),
            # Content
            short_description=raw.get("short_description", ""),
            description=raw.get("description", ""),
            work_notes=raw.get("work_notes", ""),
            close_notes=raw.get("close_notes", ""),
            close_code=raw.get("close_code", ""),
            # Status
            state=raw.get("state", ""),
            incident_state=raw.get("incident_state", ""),
            # Business context
            company=raw.get("company", ""),
            location=raw.get("location", ""),
            assignment_group=raw.get("assignment_group", ""),
            business_service=raw.get("business_service", "") or None,
            cmdb_ci=raw.get("cmdb_ci", "") or None,
            # LoB flags
            u_marsh=self._parse_bool(raw.get("u_marsh", "false")),
            u_mercer=self._parse_bool(raw.get("u_mercer", "false")),
            u_guy_carpenter=self._parse_bool(raw.get("u_guy_carpenter", "false")),
            u_oliver_wyman_group=self._parse_bool(raw.get("u_oliver_wyman_group", "false")),
            u_mmc_corporate=self._parse_bool(raw.get("u_mmc_corporate", "false")),
            # Metadata
            reassignment_count=self._parse_int(raw.get("reassignment_count", "0")),
            reopen_count=self._parse_int(raw.get("reopen_count", "0")),
            # Computed
            line_of_business=line_of_business,
            resolution_time_minutes=resolution_time,
        )

        return ticket

    def _parse_bool(self, value: str | bool) -> bool:
        """Convert ServiceNow boolean string to Python bool.

        Args:
            value: String "true"/"false" or already a bool

        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        return str(value).lower() == "true"

    def _parse_int(self, value: str | int) -> int:
        """Convert string to int, defaulting to 0.

        Args:
            value: String number or int

        Returns:
            Integer value
        """
        if isinstance(value, int):
            return value
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0

    def _parse_datetime(self, value: str) -> datetime | None:
        """Parse ServiceNow datetime format.

        Args:
            value: Datetime string in format 'YYYY-MM-DD HH:MM:SS'

        Returns:
            Parsed datetime or None if empty/invalid
        """
        if not value or not value.strip():
            return None

        try:
            return datetime.strptime(value.strip(), SERVICENOW_DATETIME_FORMAT)
        except ValueError:
            logger.warning(f"Failed to parse datetime: {value}")
            return None

    def _extract_line_of_business(self, raw: dict) -> str | None:
        """Determine Line of Business from flags or short description.

        Args:
            raw: Raw ticket dictionary

        Returns:
            LoB name or None if not determinable
        """
        # Check LoB boolean flags first
        if self._parse_bool(raw.get("u_marsh", "false")):
            return "Marsh"
        if self._parse_bool(raw.get("u_mercer", "false")):
            return "Mercer"
        if self._parse_bool(raw.get("u_guy_carpenter", "false")):
            return "Guy Carpenter"
        if self._parse_bool(raw.get("u_oliver_wyman_group", "false")):
            return "Oliver Wyman"
        if self._parse_bool(raw.get("u_mmc_corporate", "false")):
            return "MMC Corporate"

        # Try to extract from short_description prefix
        # Format can be "LoB - Location - App - Brief" or "LoB-Location-App-Brief"
        short_desc = raw.get("short_description", "")

        lob_map = {
            "MARSH": "Marsh",
            "MERCER": "Mercer",
            "GC": "Guy Carpenter",
            "GUY CARPENTER": "Guy Carpenter",
            "OW": "Oliver Wyman",
            "OLIVER WYMAN": "Oliver Wyman",
            "MMC": "MMC Corporate",
            "MMC-NCL": "MMC Corporate",
        }

        # Try " - " separator first (standard format)
        if " - " in short_desc:
            prefix = short_desc.split(" - ")[0].strip().upper()
            if prefix in lob_map:
                return lob_map[prefix]

        # Try "-" separator (alternative format like "Marsh-Mumbai-LAN-...")
        if "-" in short_desc:
            prefix = short_desc.split("-")[0].strip().upper()
            if prefix in lob_map:
                return lob_map[prefix]
            # Also check first two parts for "MMC-NCL" style
            parts = short_desc.split("-")
            if len(parts) >= 2:
                compound = f"{parts[0].strip()}-{parts[1].strip()}".upper()
                if compound in lob_map:
                    return lob_map[compound]

        return None

    def _compute_resolution_time(
        self, opened: datetime, resolved: datetime
    ) -> int:
        """Calculate resolution time in minutes.

        Args:
            opened: When ticket was opened
            resolved: When ticket was resolved

        Returns:
            Resolution time in minutes
        """
        delta = resolved - opened
        return int(delta.total_seconds() / 60)


def parse_servicenow_file(path: Path) -> list[ServiceNowTicket]:
    """Convenience function to parse a ServiceNow JSON file.

    Args:
        path: Path to JSON file

    Returns:
        List of parsed tickets
    """
    parser = ServiceNowParser()
    return parser.parse_file(path)
