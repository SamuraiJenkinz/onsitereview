"""Tests for LLM evaluation module - Onsite Support Review."""

import json
from unittest.mock import MagicMock, patch

import pytest

from onsitereview.llm import (
    BatchLLMEvaluator,
    BatchProgress,
    LLMAPIError,
    LLMEvaluator,
    LLMRateLimitError,
    LLMValidationError,
    OpenAIClient,
    TokenUsage,
)
from onsitereview.llm.prompts import (
    FieldCorrectnessPrompt,
    IncidentHandlingPrompt,
    IncidentNotesPrompt,
    ResolutionNotesPrompt,
)
from onsitereview.llm.schemas import (
    FieldCorrectnessEvaluation,
    IncidentHandlingEvaluation,
    IncidentNotesEvaluation,
    ResolutionNotesEvaluation,
)
from onsitereview.models.ticket import ServiceNowTicket


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_ticket() -> ServiceNowTicket:
    """Create a sample ticket for testing."""
    from datetime import datetime

    return ServiceNowTicket(
        number="INC1234567",
        sys_id="abc123",
        opened_at=datetime(2025, 12, 10, 4, 26, 0),
        resolved_at=datetime(2025, 12, 10, 4, 41, 0),
        closed_at=datetime(2025, 12, 15, 5, 0, 0),
        caller_id="caller123",
        opened_by="agent123",
        opened_for="user456",
        assigned_to="agent123",
        resolved_by="agent123",
        closed_by="agent123",
        short_description="MMC-NCL Bangalore-VDI-error message",
        description=(
            "Validated by: Okta Push MFA & Full Name\n\n"
            "Contact Number: 1234567890\n"
            "Working remotely: Y\n\n"
            "Issue/Request: Colleague is getting error message while connecting to VDI\n\n"
            "TS:\n"
            "->VDI reset/restart\n"
            "->asked colleague to login after 5-10 mins\n"
            "->Colleague confirmed that they can login now\n"
            "Got confirmation to close the ticket"
        ),
        close_notes=(
            ">VDI reset/restart\n"
            "->asked colleague to login after 5-10 mins\n"
            "->Colleague confirmed that they can login now\n"
            "Got confirmation to close the ticket"
        ),
        category="software",
        subcategory="reset_restart",
        business_service="VDI Service",
        cmdb_ci="VDI Pool - Bangalore",
        contact_type="phone",
        state="7",
        incident_state="7",
        priority="5",
        impact="3",
        urgency="3",
        company="company123",
        location="location123",
        assignment_group="group123",
    )


@pytest.fixture
def mock_field_correctness_response() -> dict:
    """Mock response for field correctness evaluation."""
    return {
        "category_score": 5,
        "category_reasoning": "Software category correctly matches VDI issue.",
        "subcategory_score": 5,
        "subcategory_reasoning": "Reset/restart subcategory matches the resolution action.",
        "service_score": 5,
        "service_reasoning": "VDI Service correctly identified.",
        "ci_score": 10,
        "ci_reasoning": "VDI Pool - Bangalore correctly identified as the CI.",
        "evidence": ["VDI reset/restart", "error message while connecting to VDI"],
        "coaching": "",
    }


@pytest.fixture
def mock_incident_notes_response() -> dict:
    """Mock response for incident notes evaluation."""
    return {
        "criterion_id": "incident_notes",
        "score": 20,
        "max_score": 20,
        "location_documented": True,
        "contact_info_present": True,
        "relevant_details_present": True,
        "troubleshooting_documented": True,
        "appropriate_field_usage": True,
        "evidence": ["Contact Number: 1234567890", "Working remotely: Y"],
        "reasoning": "All relevant information documented clearly.",
        "coaching": "",
    }


@pytest.fixture
def mock_incident_handling_response() -> dict:
    """Mock response for incident handling evaluation."""
    return {
        "criterion_id": "incident_handling",
        "score": 15,
        "max_score": 15,
        "routed_correctly": True,
        "resolved_appropriately": True,
        "fcr_opportunity_missed": False,
        "evidence": ["VDI reset/restart resolved the issue"],
        "reasoning": "Incident resolved at first contact appropriately.",
        "coaching": "",
    }


@pytest.fixture
def mock_resolution_notes_response() -> dict:
    """Mock response for resolution notes evaluation."""
    return {
        "criterion_id": "resolution_notes",
        "score": 20,
        "max_score": 20,
        "summary_present": True,
        "confirmation_present": True,
        "is_wip_or_routed": False,
        "evidence": ["Colleague confirmed that they can login now", "Got confirmation to close"],
        "reasoning": "Resolution notes include both summary and user confirmation.",
        "coaching": "",
    }


# ============================================================================
# Token Usage Tests
# ============================================================================


class TestTokenUsage:
    """Tests for TokenUsage tracking."""

    def test_initial_state(self):
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.request_count == 0

    def test_add_usage(self):
        usage = TokenUsage()
        usage.add({
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        })
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.request_count == 1

    def test_cumulative_usage(self):
        usage = TokenUsage()
        usage.add({"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
        usage.add({"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300})
        assert usage.prompt_tokens == 300
        assert usage.completion_tokens == 150
        assert usage.total_tokens == 450
        assert usage.request_count == 2

    def test_estimated_cost(self):
        usage = TokenUsage()
        usage.add({
            "prompt_tokens": 1_000_000,
            "completion_tokens": 1_000_000,
            "total_tokens": 2_000_000,
        })
        assert usage.estimated_cost == pytest.approx(12.50, rel=0.01)


# ============================================================================
# OpenAI Client Tests
# ============================================================================


class TestOpenAIClient:
    """Tests for OpenAI client."""

    def test_init(self):
        client = OpenAIClient(api_key="test-key")
        assert client.config.api_key == "test-key"
        assert client.config.model == "gpt-4o"
        assert client.config.temperature == 0.1
        assert client.config.max_retries == 3

    def test_init_with_custom_config(self):
        client = OpenAIClient(
            api_key="test-key",
            base_url="https://custom.api.com",
            model="gpt-4-turbo",
            temperature=0.2,
            max_retries=5,
        )
        assert client.config.base_url == "https://custom.api.com"
        assert client.config.model == "gpt-4-turbo"
        assert client.config.temperature == 0.2
        assert client.config.max_retries == 5

    @patch("onsitereview.llm.client.OpenAI")
    def test_complete_success(self, mock_openai_class):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "success"}'
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")
        result = client.complete([{"role": "user", "content": "test"}])

        assert result == {"result": "success"}
        assert client.token_usage.total_tokens == 150

    @patch("onsitereview.llm.client.OpenAI")
    def test_complete_invalid_json(self, mock_openai_class):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json"
        mock_response.usage = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")

        with pytest.raises(LLMValidationError):
            client.complete([{"role": "user", "content": "test"}])

    @patch("onsitereview.llm.client.OpenAI")
    def test_complete_empty_response(self, mock_openai_class):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.usage = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")

        with pytest.raises(LLMValidationError):
            client.complete([{"role": "user", "content": "test"}])

    def test_reset_usage(self):
        client = OpenAIClient(api_key="test-key")
        client.token_usage.add({"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
        old_usage = client.reset_usage()
        assert old_usage.total_tokens == 150
        assert client.token_usage.total_tokens == 0


# ============================================================================
# Schema Tests
# ============================================================================


class TestSchemas:
    """Tests for evaluation schemas."""

    def test_field_correctness_evaluation(self, mock_field_correctness_response):
        eval_result = FieldCorrectnessEvaluation.model_validate(mock_field_correctness_response)
        assert eval_result.category_score == 5
        assert eval_result.subcategory_score == 5
        assert eval_result.service_score == 5
        assert eval_result.ci_score == 10

    def test_incident_notes_evaluation(self, mock_incident_notes_response):
        eval_result = IncidentNotesEvaluation.model_validate(mock_incident_notes_response)
        assert eval_result.criterion_id == "incident_notes"
        assert eval_result.score == 20
        assert eval_result.max_score == 20
        assert eval_result.location_documented is True
        assert eval_result.contact_info_present is True

    def test_incident_handling_evaluation(self, mock_incident_handling_response):
        eval_result = IncidentHandlingEvaluation.model_validate(mock_incident_handling_response)
        assert eval_result.criterion_id == "incident_handling"
        assert eval_result.score == 15
        assert eval_result.routed_correctly is True
        assert eval_result.fcr_opportunity_missed is False

    def test_resolution_notes_evaluation(self, mock_resolution_notes_response):
        eval_result = ResolutionNotesEvaluation.model_validate(mock_resolution_notes_response)
        assert eval_result.criterion_id == "resolution_notes"
        assert eval_result.score == 20
        assert eval_result.summary_present is True
        assert eval_result.confirmation_present is True

    def test_score_validation_bounds(self):
        with pytest.raises(Exception):
            IncidentNotesEvaluation(
                criterion_id="test",
                score=-1,
                max_score=20,
                location_documented=True,
                contact_info_present=True,
                relevant_details_present=True,
                troubleshooting_documented=True,
                appropriate_field_usage=True,
                reasoning="test",
            )


# ============================================================================
# Prompt Tests
# ============================================================================


class TestPrompts:
    """Tests for prompt templates."""

    def test_field_correctness_prompt_messages(self, sample_ticket):
        messages = FieldCorrectnessPrompt.build_messages(sample_ticket)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "INC1234567" in messages[1]["content"]
        assert "category_score" in messages[1]["content"]

    def test_incident_notes_prompt_messages(self, sample_ticket):
        messages = IncidentNotesPrompt.build_messages(sample_ticket)
        assert len(messages) == 2
        assert "incident" in messages[0]["content"].lower()
        assert "notes" in messages[0]["content"].lower()

    def test_incident_handling_prompt_messages(self, sample_ticket):
        messages = IncidentHandlingPrompt.build_messages(sample_ticket)
        assert len(messages) == 2
        assert "handling" in messages[0]["content"].lower()

    def test_resolution_notes_prompt_messages(self, sample_ticket):
        messages = ResolutionNotesPrompt.build_messages(sample_ticket)
        assert len(messages) == 2
        assert "resolution" in messages[0]["content"].lower()

    def test_prompt_includes_all_ticket_fields(self, sample_ticket):
        messages = FieldCorrectnessPrompt.build_messages(sample_ticket)
        content = messages[1]["content"]
        assert sample_ticket.number in content
        assert sample_ticket.category in content
        assert sample_ticket.contact_type in content
        assert "Okta Push" in content


# ============================================================================
# LLM Evaluator Tests
# ============================================================================


class TestLLMEvaluator:
    """Tests for LLM Evaluator."""

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_field_correctness(
        self, mock_complete, sample_ticket, mock_field_correctness_response
    ):
        mock_complete.return_value = mock_field_correctness_response

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)
        results = evaluator.evaluate_field_correctness(sample_ticket)

        assert len(results) == 4
        assert results[0].criterion_id == "correct_category"
        assert results[0].score == 5
        assert results[1].criterion_id == "correct_subcategory"
        assert results[1].score == 5
        assert results[2].criterion_id == "correct_service"
        assert results[2].score == 5
        assert results[3].criterion_id == "correct_ci"
        assert results[3].score == 10

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_incident_notes(
        self, mock_complete, sample_ticket, mock_incident_notes_response
    ):
        mock_complete.return_value = mock_incident_notes_response

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)
        result = evaluator.evaluate_incident_notes(sample_ticket)

        assert result.criterion_id == "incident_notes"
        assert result.score == 20
        assert result.passed is True

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_incident_handling(
        self, mock_complete, sample_ticket, mock_incident_handling_response
    ):
        mock_complete.return_value = mock_incident_handling_response

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)
        result = evaluator.evaluate_incident_handling(sample_ticket)

        assert result.criterion_id == "incident_handling"
        assert result.score == 15
        assert result.passed is True

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_resolution_notes(
        self, mock_complete, sample_ticket, mock_resolution_notes_response
    ):
        mock_complete.return_value = mock_resolution_notes_response

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)
        result = evaluator.evaluate_resolution_notes(sample_ticket)

        assert result.criterion_id == "resolution_notes"
        assert result.score == 20
        assert result.passed is True

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_ticket_returns_7_results(
        self,
        mock_complete,
        sample_ticket,
        mock_field_correctness_response,
        mock_incident_notes_response,
        mock_incident_handling_response,
        mock_resolution_notes_response,
    ):
        """Test full ticket evaluation returns 7 RuleResults from 4 LLM calls."""
        mock_complete.side_effect = [
            mock_field_correctness_response,
            mock_incident_notes_response,
            mock_incident_handling_response,
            mock_resolution_notes_response,
        ]

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)
        results = evaluator.evaluate_ticket(sample_ticket)

        assert len(results) == 7
        criterion_ids = [r.criterion_id for r in results]
        assert "correct_category" in criterion_ids
        assert "correct_subcategory" in criterion_ids
        assert "correct_service" in criterion_ids
        assert "correct_ci" in criterion_ids
        assert "incident_notes" in criterion_ids
        assert "incident_handling" in criterion_ids
        assert "resolution_notes" in criterion_ids

        # Verify total max score is 80 (LLM portion of 90)
        total_max = sum(r.max_score for r in results)
        assert total_max == 80  # 5+5+5+10+20+15+20

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_handles_api_error(self, mock_complete, sample_ticket):
        """Test graceful handling of API errors."""
        mock_complete.side_effect = LLMAPIError("API Error")

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)
        results = evaluator.evaluate_ticket(sample_ticket)

        # Should return 7 error results (4 for fields + 1+1+1)
        assert len(results) == 7
        assert all(r.score == 0 for r in results)
        assert all("error" in r.reasoning.lower() for r in results)


# ============================================================================
# Batch Evaluator Tests
# ============================================================================


class TestBatchLLMEvaluator:
    """Tests for batch LLM evaluator."""

    def test_batch_progress(self):
        progress = BatchProgress(total=10, completed=5, failed=1)
        assert progress.percentage == 50.0
        assert progress.elapsed_seconds >= 0

    @patch.object(LLMEvaluator, "evaluate_ticket")
    def test_evaluate_batch(self, mock_evaluate, sample_ticket):
        mock_evaluate.return_value = [
            MagicMock(criterion_id="test", score=10, passed=True)
        ]

        client = OpenAIClient(api_key="test-key")
        batch_evaluator = BatchLLMEvaluator(client, concurrency=2)

        tickets = [sample_ticket, sample_ticket]
        result = batch_evaluator.evaluate_batch(tickets)

        assert result.total_tickets == 2
        assert result.successful == 2
        assert result.failed == 0
        assert result.success_rate == 100.0

    @patch.object(LLMEvaluator, "evaluate_ticket")
    def test_evaluate_batch_with_failures(self, mock_evaluate, sample_ticket):
        mock_evaluate.side_effect = [
            [MagicMock(criterion_id="test", score=10, passed=True)],
            LLMAPIError("API Error"),
        ]

        client = OpenAIClient(api_key="test-key")
        batch_evaluator = BatchLLMEvaluator(client)

        tickets = [sample_ticket, sample_ticket]
        result = batch_evaluator.evaluate_batch(tickets)

        assert result.total_tickets == 2
        assert result.successful == 1
        assert result.failed == 1
        assert result.success_rate == 50.0

    @patch.object(LLMEvaluator, "evaluate_ticket")
    def test_evaluate_batch_with_progress_callback(self, mock_evaluate, sample_ticket):
        mock_evaluate.return_value = [MagicMock()]

        client = OpenAIClient(api_key="test-key")
        batch_evaluator = BatchLLMEvaluator(client)

        progress_updates = []

        def callback(progress: BatchProgress):
            progress_updates.append(progress.percentage)

        tickets = [sample_ticket, sample_ticket, sample_ticket]
        batch_evaluator.evaluate_batch(tickets, progress_callback=callback)

        assert len(progress_updates) > 0

    @patch.object(LLMEvaluator, "evaluate_ticket")
    def test_evaluate_single(self, mock_evaluate, sample_ticket):
        mock_evaluate.return_value = [MagicMock()]

        client = OpenAIClient(api_key="test-key")
        batch_evaluator = BatchLLMEvaluator(client)

        result = batch_evaluator.evaluate_single(sample_ticket)

        assert result.success is True
        assert result.ticket_number == "INC1234567"


# ============================================================================
# Integration-style Tests (with full mock chain)
# ============================================================================


class TestIntegration:
    """Integration-style tests with full mock chain."""

    @patch("onsitereview.llm.client.OpenAI")
    def test_full_evaluation_flow(
        self,
        mock_openai_class,
        sample_ticket,
        mock_field_correctness_response,
        mock_incident_notes_response,
        mock_incident_handling_response,
        mock_resolution_notes_response,
    ):
        """Test complete evaluation flow with 4 LLM calls -> 7 results."""
        responses = [
            json.dumps(mock_field_correctness_response),
            json.dumps(mock_incident_notes_response),
            json.dumps(mock_incident_handling_response),
            json.dumps(mock_resolution_notes_response),
        ]
        response_iter = iter(responses)

        def make_response(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.content = next(response_iter)
            mock_resp.usage = MagicMock()
            mock_resp.usage.prompt_tokens = 100
            mock_resp.usage.completion_tokens = 50
            mock_resp.usage.total_tokens = 150
            return mock_resp

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = make_response
        mock_openai_class.return_value = mock_client

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)
        results = evaluator.evaluate_ticket(sample_ticket)

        # 4 LLM calls -> 7 results
        assert len(results) == 7
        assert results[0].criterion_id == "correct_category"
        assert results[0].score == 5
        assert results[4].criterion_id == "incident_notes"
        assert results[4].score == 20
        assert results[5].criterion_id == "incident_handling"
        assert results[5].score == 15
        assert results[6].criterion_id == "resolution_notes"
        assert results[6].score == 20

        # 4 API calls * 150 tokens each
        assert client.token_usage.total_tokens == 600
