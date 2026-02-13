"""Tests for onsitereview rules engine."""

from datetime import datetime

import pytest

from onsitereview.models.ticket import ServiceNowTicket
from onsitereview.rules.evaluator import RulesEvaluator
from onsitereview.rules.opened_for import OpenedForValidator


def _make_ticket(**overrides) -> ServiceNowTicket:
    """Create a test ticket with defaults."""
    defaults = {
        "number": "INC0001",
        "sys_id": "abc123",
        "opened_at": datetime(2024, 1, 1),
        "caller_id": "user1",
        "opened_by": "agent1",
        "opened_for": "",
        "assigned_to": "agent1",
        "category": "Software",
        "subcategory": "Operating System",
        "contact_type": "phone",
        "priority": "3",
        "impact": "2",
        "urgency": "2",
        "short_description": "MARSH - Sydney - VDI - Cannot connect",
        "description": "User cannot connect to VDI",
        "state": "7",
        "incident_state": "7",
        "company": "comp1",
        "location": "loc1",
        "assignment_group": "grp1",
    }
    defaults.update(overrides)
    return ServiceNowTicket(**defaults)


class TestOpenedForValidator:
    """Tests for OpenedForValidator."""

    def setup_method(self):
        self.validator = OpenedForValidator()

    def test_passes_when_opened_for_populated(self):
        ticket = _make_ticket(opened_for="user_sys_id_123")
        result = self.validator.evaluate(ticket)
        assert result.passed is True
        assert result.score == 10
        assert result.max_score == 10
        assert result.criterion_id == "opened_for_correct"
        assert result.coaching is None

    def test_fails_when_opened_for_empty(self):
        ticket = _make_ticket(opened_for="")
        result = self.validator.evaluate(ticket)
        assert result.passed is False
        assert result.score == 0
        assert result.max_score == 10
        assert result.coaching is not None
        assert "Opened For" in result.coaching

    def test_fails_when_opened_for_whitespace(self):
        ticket = _make_ticket(opened_for="   ")
        result = self.validator.evaluate(ticket)
        assert result.passed is False
        assert result.score == 0


class TestRulesEvaluator:
    """Tests for RulesEvaluator orchestrator."""

    def setup_method(self):
        self.evaluator = RulesEvaluator()

    def test_returns_single_result(self):
        ticket = _make_ticket(opened_for="user123")
        results = self.evaluator.evaluate(ticket)
        assert len(results) == 1
        assert results[0].criterion_id == "opened_for_correct"

    def test_get_rule_scores(self):
        ticket = _make_ticket(opened_for="user123")
        scores = self.evaluator.get_rule_scores(ticket)
        assert "opened_for_correct" in scores
        assert scores["opened_for_correct"].score == 10
