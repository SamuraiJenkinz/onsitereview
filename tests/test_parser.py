"""Tests for ServiceNow JSON parser."""

from datetime import datetime
from pathlib import Path

import pytest

from tqrs.models import ServiceNowTicket
from tqrs.parser import ServiceNowParser


class TestServiceNowParser:
    """Tests for ServiceNowParser class."""

    def test_parse_file_returns_tickets(
        self, parser: ServiceNowParser, sample_tickets_path: Path
    ):
        """Parser should return list of tickets from file."""
        tickets = parser.parse_file(sample_tickets_path)
        assert isinstance(tickets, list)
        assert len(tickets) == 3
        assert all(isinstance(t, ServiceNowTicket) for t in tickets)

    def test_parse_file_not_found(self, parser: ServiceNowParser):
        """Parser should raise error for missing file."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file(Path("/nonexistent/file.json"))

    def test_parse_json_missing_records_key(self, parser: ServiceNowParser):
        """Parser should raise error if records key is missing."""
        with pytest.raises(ValueError, match="must contain 'records' key"):
            parser.parse_json({"data": []})


class TestTicketParsing:
    """Tests for individual ticket parsing."""

    def test_ticket_numbers(self, sample_tickets: list[ServiceNowTicket]):
        """All ticket numbers should be parsed correctly."""
        numbers = {t.number for t in sample_tickets}
        assert numbers == {"INC8924218", "INC8924339", "INC8923651"}

    def test_ticket_sys_ids(self, sample_tickets: list[ServiceNowTicket]):
        """All tickets should have sys_id populated."""
        for ticket in sample_tickets:
            assert ticket.sys_id
            assert len(ticket.sys_id) == 32  # ServiceNow sys_id length

    def test_opened_at_parsing(self, sample_tickets: list[ServiceNowTicket]):
        """Opened timestamps should be parsed correctly."""
        for ticket in sample_tickets:
            assert ticket.opened_at is not None
            assert isinstance(ticket.opened_at, datetime)
            assert ticket.opened_at.year == 2025
            assert ticket.opened_at.month == 12
            assert ticket.opened_at.day == 10

    def test_resolved_at_parsing(self, sample_tickets: list[ServiceNowTicket]):
        """Resolved timestamps should be parsed correctly."""
        for ticket in sample_tickets:
            assert ticket.resolved_at is not None
            assert isinstance(ticket.resolved_at, datetime)

    def test_closed_at_parsing(self, sample_tickets: list[ServiceNowTicket]):
        """Closed timestamps should be parsed correctly."""
        for ticket in sample_tickets:
            assert ticket.closed_at is not None
            assert ticket.closed_at >= ticket.resolved_at

    def test_resolution_time_calculated(self, sample_tickets: list[ServiceNowTicket]):
        """Resolution time should be computed from timestamps."""
        for ticket in sample_tickets:
            assert ticket.resolution_time_minutes is not None
            assert ticket.resolution_time_minutes > 0

    def test_resolution_time_accuracy(self, sample_tickets: list[ServiceNowTicket]):
        """Resolution time should match expected values."""
        # INC8924218: opened 04:26:00, resolved 04:41:00 = 15 minutes
        inc1 = next(t for t in sample_tickets if t.number == "INC8924218")
        assert inc1.resolution_time_minutes == 15

        # INC8924339: opened 04:57:00, resolved 04:59:00 = 2 minutes
        inc2 = next(t for t in sample_tickets if t.number == "INC8924339")
        assert inc2.resolution_time_minutes == 2


class TestBooleanParsing:
    """Tests for boolean field parsing."""

    def test_lob_flags_parsed(self, sample_tickets: list[ServiceNowTicket]):
        """LoB boolean flags should parse correctly."""
        for ticket in sample_tickets:
            # All sample tickets have all LoB flags as false
            assert ticket.u_marsh is False
            assert ticket.u_mercer is False
            assert ticket.u_guy_carpenter is False
            assert ticket.u_oliver_wyman_group is False
            assert ticket.u_mmc_corporate is False

    def test_parse_bool_true(self, parser: ServiceNowParser):
        """Parser should convert 'true' string to True."""
        assert parser._parse_bool("true") is True
        assert parser._parse_bool("TRUE") is True
        assert parser._parse_bool("True") is True

    def test_parse_bool_false(self, parser: ServiceNowParser):
        """Parser should convert 'false' string to False."""
        assert parser._parse_bool("false") is False
        assert parser._parse_bool("FALSE") is False
        assert parser._parse_bool("False") is False

    def test_parse_bool_already_bool(self, parser: ServiceNowParser):
        """Parser should pass through actual booleans."""
        assert parser._parse_bool(True) is True
        assert parser._parse_bool(False) is False


class TestLineOfBusinessExtraction:
    """Tests for LoB extraction logic."""

    def test_lob_from_short_description(self, sample_tickets: list[ServiceNowTicket]):
        """LoB should be extracted from short description prefix."""
        # INC8924218: "MMC-NCL Bangalore-VDI-error message"
        inc1 = next(t for t in sample_tickets if t.number == "INC8924218")
        assert inc1.line_of_business == "MMC Corporate"

        # INC8924339: "Marsh-Mumbai-LAN-Need password reset"
        inc2 = next(t for t in sample_tickets if t.number == "INC8924339")
        assert inc2.line_of_business == "Marsh"

        # INC8923651: "MMC - Wollongong - AD - Password reset"
        inc3 = next(t for t in sample_tickets if t.number == "INC8923651")
        assert inc3.line_of_business == "MMC Corporate"

    def test_get_line_of_business_method(self, sample_tickets: list[ServiceNowTicket]):
        """Ticket method should return correct LoB."""
        for ticket in sample_tickets:
            lob = ticket.get_line_of_business()
            assert lob in ["Marsh", "Mercer", "Guy Carpenter", "Oliver Wyman", "MMC Corporate"]


class TestTicketClassification:
    """Tests for ticket classification fields."""

    def test_categories_parsed(self, sample_tickets: list[ServiceNowTicket]):
        """Categories should be parsed correctly."""
        categories = {t.category for t in sample_tickets}
        assert "software" in categories
        assert "inquiry" in categories

    def test_subcategories_parsed(self, sample_tickets: list[ServiceNowTicket]):
        """Subcategories should be parsed correctly."""
        subcategories = {t.subcategory for t in sample_tickets}
        assert "reset_restart" in subcategories
        assert "password reset" in subcategories

    def test_contact_type_all_phone(self, sample_tickets: list[ServiceNowTicket]):
        """All sample tickets should have phone contact type."""
        for ticket in sample_tickets:
            assert ticket.contact_type == "phone"

    def test_priority_parsed(self, sample_tickets: list[ServiceNowTicket]):
        """Priority should be parsed correctly."""
        priorities = {t.priority for t in sample_tickets}
        assert priorities.issubset({"4", "5"})


class TestTicketContent:
    """Tests for ticket content fields."""

    def test_short_description_populated(self, sample_tickets: list[ServiceNowTicket]):
        """Short descriptions should be populated."""
        for ticket in sample_tickets:
            assert ticket.short_description
            assert len(ticket.short_description) > 10

    def test_description_populated(self, sample_tickets: list[ServiceNowTicket]):
        """Full descriptions should be populated."""
        for ticket in sample_tickets:
            assert ticket.description
            assert len(ticket.description) > 50

    def test_close_notes_populated(self, sample_tickets: list[ServiceNowTicket]):
        """Close notes should be populated."""
        for ticket in sample_tickets:
            assert ticket.close_notes
            assert len(ticket.close_notes) > 10

    def test_close_code_populated(self, sample_tickets: list[ServiceNowTicket]):
        """Close code should be 'Solved (Permanently)' for all samples."""
        for ticket in sample_tickets:
            assert ticket.close_code == "Solved (Permanently)"


class TestTicketStatus:
    """Tests for ticket status properties."""

    def test_is_closed(self, sample_tickets: list[ServiceNowTicket]):
        """All sample tickets should be closed."""
        for ticket in sample_tickets:
            assert ticket.is_closed is True
            assert ticket.state == "7"
            assert ticket.incident_state == "7"

    def test_is_resolved(self, sample_tickets: list[ServiceNowTicket]):
        """All sample tickets should be resolved."""
        for ticket in sample_tickets:
            assert ticket.is_resolved is True

    def test_has_validation(self, sample_tickets: list[ServiceNowTicket]):
        """Sample tickets should have validation documented."""
        for ticket in sample_tickets:
            # All samples mention validation in description
            assert ticket.has_validation is True


class TestDatetimeParsing:
    """Tests for datetime parsing edge cases."""

    def test_parse_valid_datetime(self, parser: ServiceNowParser):
        """Parser should handle valid datetime strings."""
        result = parser._parse_datetime("2025-12-10 04:26:00")
        assert result == datetime(2025, 12, 10, 4, 26, 0)

    def test_parse_empty_datetime(self, parser: ServiceNowParser):
        """Parser should return None for empty string."""
        assert parser._parse_datetime("") is None
        assert parser._parse_datetime("   ") is None

    def test_parse_invalid_datetime(self, parser: ServiceNowParser):
        """Parser should return None for invalid format."""
        assert parser._parse_datetime("not-a-date") is None
        assert parser._parse_datetime("2025/12/10") is None


class TestIntegerParsing:
    """Tests for integer parsing."""

    def test_parse_string_int(self, parser: ServiceNowParser):
        """Parser should convert string numbers to int."""
        assert parser._parse_int("5") == 5
        assert parser._parse_int("0") == 0
        assert parser._parse_int("100") == 100

    def test_parse_empty_string(self, parser: ServiceNowParser):
        """Parser should return 0 for empty string."""
        assert parser._parse_int("") == 0

    def test_parse_actual_int(self, parser: ServiceNowParser):
        """Parser should pass through actual integers."""
        assert parser._parse_int(42) == 42

    def test_reassignment_count(self, sample_tickets: list[ServiceNowTicket]):
        """Reassignment count should be parsed as int."""
        for ticket in sample_tickets:
            assert isinstance(ticket.reassignment_count, int)
            assert ticket.reassignment_count == 1  # All samples have 1

    def test_reopen_count(self, sample_tickets: list[ServiceNowTicket]):
        """Reopen count should be parsed as int."""
        for ticket in sample_tickets:
            assert isinstance(ticket.reopen_count, int)
            assert ticket.reopen_count == 0  # All samples have 0
