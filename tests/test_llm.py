"""Tests for LLM evaluation module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from tqrs.llm import (
    BatchLLMEvaluator,
    BatchProgress,
    LLMAPIError,
    LLMEvaluator,
    LLMRateLimitError,
    LLMValidationError,
    OpenAIClient,
    TokenUsage,
)
from tqrs.llm.prompts import (
    CustomerServicePrompt,
    DescriptionPrompt,
    ResolutionPrompt,
    SpellingGrammarPrompt,
    TroubleshootingPrompt,
)
from tqrs.llm.schemas import (
    CustomerServiceEvaluation,
    DescriptionEvaluation,
    LLMEvaluationResponse,
    ResolutionEvaluation,
    SpellingGrammarEvaluation,
    TroubleshootingEvaluation,
)
from tqrs.models.evaluation import TemplateType
from tqrs.models.ticket import ServiceNowTicket


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
def mock_description_response() -> dict:
    """Mock response for description evaluation."""
    return {
        "criterion_id": "accurate_description",
        "score": 20,
        "max_score": 20,
        "completeness_score": 10,
        "clarity_score": 10,
        "issue_stated": True,
        "context_provided": True,
        "user_impact_noted": True,
        "evidence": ["Validated by: Okta Push MFA", "Issue/Request: Colleague is getting error"],
        "reasoning": "Excellent description with all required elements.",
        "strengths": ["Clear issue statement", "Validation documented"],
        "improvements": [],
        "coaching": "",
    }


@pytest.fixture
def mock_troubleshooting_response() -> dict:
    """Mock response for troubleshooting evaluation."""
    return {
        "criterion_id": "troubleshooting_quality",
        "score": 20,
        "max_score": 20,
        "steps_documented": True,
        "logical_progression": True,
        "appropriate_actions": True,
        "outcome_documented": True,
        "steps_count": 3,
        "evidence": ["VDI reset/restart", "asked colleague to login after 5-10 mins"],
        "reasoning": "Troubleshooting steps clearly documented with outcomes.",
        "strengths": ["Clear step documentation", "Logical progression"],
        "improvements": [],
        "coaching": "",
    }


@pytest.fixture
def mock_resolution_response() -> dict:
    """Mock response for resolution evaluation."""
    return {
        "criterion_id": "resolution_notes",
        "score": 15,
        "max_score": 15,
        "outcome_clear": True,
        "steps_documented": True,
        "confirmation_obtained": True,
        "resolution_complete": True,
        "evidence": ["Colleague confirmed that they can login now", "Got confirmation to close"],
        "reasoning": "Resolution notes complete with all required elements.",
        "strengths": ["User confirmation obtained", "Clear resolution steps"],
        "improvements": [],
        "coaching": "",
    }


@pytest.fixture
def mock_customer_service_response() -> dict:
    """Mock response for customer service evaluation."""
    return {
        "criterion_id": "customer_service_quality",
        "score": 20,
        "max_score": 20,
        "professional_tone": True,
        "empathy_shown": True,
        "clear_communication": True,
        "proper_greeting": True,
        "proper_closing": True,
        "expectations_set": True,
        "evidence": ["Got confirmation to close the ticket"],
        "reasoning": "High level of customer service demonstrated.",
        "strengths": ["Professional interaction", "Clear communication"],
        "improvements": [],
        "coaching": "",
    }


@pytest.fixture
def mock_spelling_response() -> dict:
    """Mock response for spelling/grammar evaluation."""
    return {
        "criterion_id": "spelling_grammar",
        "score": 2,
        "max_score": 2,
        "error_count": 0,
        "errors_found": [],
        "severity": "none",
        "evidence": [],
        "reasoning": "No spelling or grammar errors found.",
        "strengths": ["Error-free writing"],
        "improvements": [],
        "coaching": "",
    }


# ============================================================================
# Token Usage Tests
# ============================================================================


class TestTokenUsage:
    """Tests for TokenUsage tracking."""

    def test_initial_state(self):
        """Test initial token usage is zero."""
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.request_count == 0

    def test_add_usage(self):
        """Test adding token usage."""
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
        """Test cumulative token usage tracking."""
        usage = TokenUsage()
        usage.add({"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})
        usage.add({"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300})

        assert usage.prompt_tokens == 300
        assert usage.completion_tokens == 150
        assert usage.total_tokens == 450
        assert usage.request_count == 2

    def test_estimated_cost(self):
        """Test cost estimation."""
        usage = TokenUsage()
        usage.add({
            "prompt_tokens": 1_000_000,  # $2.50
            "completion_tokens": 1_000_000,  # $10.00
            "total_tokens": 2_000_000,
        })

        assert usage.estimated_cost == pytest.approx(12.50, rel=0.01)


# ============================================================================
# OpenAI Client Tests
# ============================================================================


class TestOpenAIClient:
    """Tests for OpenAI client."""

    def test_init(self):
        """Test client initialization."""
        client = OpenAIClient(api_key="test-key")

        assert client.config.api_key == "test-key"
        assert client.config.model == "gpt-4o"
        assert client.config.temperature == 0.1
        assert client.config.max_retries == 3

    def test_init_with_custom_config(self):
        """Test client with custom configuration."""
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

    @patch("tqrs.llm.client.OpenAI")
    def test_complete_success(self, mock_openai_class):
        """Test successful completion request."""
        # Mock response
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

    @patch("tqrs.llm.client.OpenAI")
    def test_complete_invalid_json(self, mock_openai_class):
        """Test handling of invalid JSON response."""
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

    @patch("tqrs.llm.client.OpenAI")
    def test_complete_empty_response(self, mock_openai_class):
        """Test handling of empty response."""
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
        """Test resetting token usage."""
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

    def test_description_evaluation(self, mock_description_response):
        """Test DescriptionEvaluation model."""
        eval_result = DescriptionEvaluation.model_validate(mock_description_response)

        assert eval_result.criterion_id == "accurate_description"
        assert eval_result.score == 20
        assert eval_result.max_score == 20
        assert eval_result.completeness_score == 10
        assert eval_result.clarity_score == 10
        assert eval_result.issue_stated is True

    def test_troubleshooting_evaluation(self, mock_troubleshooting_response):
        """Test TroubleshootingEvaluation model."""
        eval_result = TroubleshootingEvaluation.model_validate(mock_troubleshooting_response)

        assert eval_result.criterion_id == "troubleshooting_quality"
        assert eval_result.score == 20
        assert eval_result.steps_documented is True
        assert eval_result.steps_count == 3

    def test_resolution_evaluation(self, mock_resolution_response):
        """Test ResolutionEvaluation model."""
        eval_result = ResolutionEvaluation.model_validate(mock_resolution_response)

        assert eval_result.criterion_id == "resolution_notes"
        assert eval_result.score == 15
        assert eval_result.confirmation_obtained is True

    def test_customer_service_evaluation(self, mock_customer_service_response):
        """Test CustomerServiceEvaluation model."""
        eval_result = CustomerServiceEvaluation.model_validate(mock_customer_service_response)

        assert eval_result.criterion_id == "customer_service_quality"
        assert eval_result.score == 20
        assert eval_result.professional_tone is True

    def test_spelling_evaluation(self, mock_spelling_response):
        """Test SpellingGrammarEvaluation model."""
        eval_result = SpellingGrammarEvaluation.model_validate(mock_spelling_response)

        assert eval_result.criterion_id == "spelling_grammar"
        assert eval_result.score == 2
        assert eval_result.error_count == 0
        assert eval_result.severity == "none"

    def test_llm_evaluation_response(
        self, mock_description_response, mock_spelling_response
    ):
        """Test LLMEvaluationResponse model."""
        desc_eval = DescriptionEvaluation.model_validate(mock_description_response)
        spell_eval = SpellingGrammarEvaluation.model_validate(mock_spelling_response)

        response = LLMEvaluationResponse(
            ticket_number="INC1234567",
            template_type="incident_logging",
            description_eval=desc_eval,
            spelling_grammar_eval=spell_eval,
            overall_assessment="Excellent ticket quality.",
            total_llm_score=22,
            max_llm_score=22,
        )

        assert response.llm_percentage == 100.0
        assert len(response.get_all_coaching()) == 0

    def test_score_validation(self):
        """Test score validation bounds."""
        with pytest.raises(Exception):
            DescriptionEvaluation(
                criterion_id="test",
                score=-1,  # Invalid: below 0
                max_score=20,
                completeness_score=10,
                clarity_score=10,
                issue_stated=True,
                context_provided=True,
                user_impact_noted=True,
                reasoning="test",
            )


# ============================================================================
# Prompt Tests
# ============================================================================


class TestPrompts:
    """Tests for prompt templates."""

    def test_description_prompt_messages(self, sample_ticket):
        """Test description prompt message construction."""
        messages = DescriptionPrompt.build_messages(sample_ticket)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "INC1234567" in messages[1]["content"]
        assert "accurate_description" in messages[1]["content"]

    def test_troubleshooting_prompt_messages(self, sample_ticket):
        """Test troubleshooting prompt message construction."""
        messages = TroubleshootingPrompt.build_messages(sample_ticket)

        assert len(messages) == 2
        assert "troubleshooting" in messages[0]["content"].lower()
        assert "VDI reset/restart" in messages[1]["content"]

    def test_resolution_prompt_messages(self, sample_ticket):
        """Test resolution prompt message construction."""
        messages = ResolutionPrompt.build_messages(sample_ticket)

        assert len(messages) == 2
        assert "resolution" in messages[0]["content"].lower()

    def test_customer_service_prompt_messages(self, sample_ticket):
        """Test customer service prompt message construction."""
        messages = CustomerServicePrompt.build_messages(sample_ticket)

        assert len(messages) == 2
        assert "customer service" in messages[0]["content"].lower()

    def test_spelling_prompt_messages(self, sample_ticket):
        """Test spelling/grammar prompt message construction."""
        messages = SpellingGrammarPrompt.build_messages(sample_ticket)

        assert len(messages) == 2
        assert "spelling" in messages[0]["content"].lower()

    def test_prompt_includes_all_ticket_fields(self, sample_ticket):
        """Test that prompts include key ticket fields."""
        messages = DescriptionPrompt.build_messages(sample_ticket)
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
    def test_evaluate_description(
        self, mock_complete, sample_ticket, mock_description_response
    ):
        """Test description evaluation."""
        mock_complete.return_value = mock_description_response

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)

        result = evaluator.evaluate_description(sample_ticket)

        assert result.criterion_id == "accurate_description"
        assert result.score == 20
        assert result.max_score == 20
        assert result.passed is True

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_troubleshooting(
        self, mock_complete, sample_ticket, mock_troubleshooting_response
    ):
        """Test troubleshooting evaluation."""
        mock_complete.return_value = mock_troubleshooting_response

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)

        result = evaluator.evaluate_troubleshooting(sample_ticket)

        assert result.criterion_id == "troubleshooting_quality"
        assert result.score == 20
        assert result.passed is True

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_resolution(
        self, mock_complete, sample_ticket, mock_resolution_response
    ):
        """Test resolution evaluation."""
        mock_complete.return_value = mock_resolution_response

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)

        result = evaluator.evaluate_resolution(sample_ticket)

        assert result.criterion_id == "resolution_notes"
        assert result.score == 15
        assert result.passed is True

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_customer_service(
        self, mock_complete, sample_ticket, mock_customer_service_response
    ):
        """Test customer service evaluation."""
        mock_complete.return_value = mock_customer_service_response

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)

        result = evaluator.evaluate_customer_service(sample_ticket)

        assert result.criterion_id == "customer_service_quality"
        assert result.score == 20
        assert result.passed is True

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_spelling_grammar(
        self, mock_complete, sample_ticket, mock_spelling_response
    ):
        """Test spelling/grammar evaluation."""
        mock_complete.return_value = mock_spelling_response

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)

        result = evaluator.evaluate_spelling_grammar(sample_ticket)

        assert result.criterion_id == "spelling_grammar"
        assert result.score == 2
        assert result.passed is True

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_ticket_incident_logging(
        self, mock_complete, sample_ticket, mock_description_response, mock_spelling_response
    ):
        """Test full ticket evaluation for Incident Logging template."""
        # Return appropriate response based on call
        mock_complete.side_effect = [
            mock_description_response,
            mock_spelling_response,
        ]

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)

        results = evaluator.evaluate_ticket(sample_ticket, TemplateType.INCIDENT_LOGGING)

        assert len(results) == 2
        assert results[0].criterion_id == "accurate_description"
        assert results[1].criterion_id == "spelling_grammar"

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_ticket_incident_handling(
        self,
        mock_complete,
        sample_ticket,
        mock_description_response,
        mock_troubleshooting_response,
        mock_resolution_response,
        mock_spelling_response,
    ):
        """Test full ticket evaluation for Incident Handling template."""
        mock_complete.side_effect = [
            mock_description_response,
            mock_troubleshooting_response,
            mock_resolution_response,
            mock_spelling_response,
        ]

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)

        results = evaluator.evaluate_ticket(sample_ticket, TemplateType.INCIDENT_HANDLING)

        assert len(results) == 4
        criterion_ids = [r.criterion_id for r in results]
        assert "accurate_description" in criterion_ids
        assert "troubleshooting_quality" in criterion_ids
        assert "resolution_notes" in criterion_ids
        assert "spelling_grammar" in criterion_ids

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_ticket_customer_service(
        self,
        mock_complete,
        sample_ticket,
        mock_description_response,
        mock_troubleshooting_response,
        mock_customer_service_response,
        mock_spelling_response,
    ):
        """Test full ticket evaluation for Customer Service template."""
        mock_complete.side_effect = [
            mock_description_response,
            mock_troubleshooting_response,
            mock_customer_service_response,
            mock_spelling_response,
        ]

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)

        results = evaluator.evaluate_ticket(sample_ticket, TemplateType.CUSTOMER_SERVICE)

        assert len(results) == 4
        criterion_ids = [r.criterion_id for r in results]
        assert "customer_service_quality" in criterion_ids

    @patch.object(OpenAIClient, "complete")
    def test_evaluate_handles_api_error(self, mock_complete, sample_ticket):
        """Test graceful handling of API errors."""
        mock_complete.side_effect = LLMAPIError("API Error")

        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)

        results = evaluator.evaluate_ticket(sample_ticket, TemplateType.INCIDENT_LOGGING)

        # Should return error results instead of raising
        assert len(results) == 2
        assert results[0].score == 0
        assert "error" in results[0].reasoning.lower()


# ============================================================================
# Batch Evaluator Tests
# ============================================================================


class TestBatchLLMEvaluator:
    """Tests for batch LLM evaluator."""

    def test_batch_progress(self):
        """Test batch progress tracking."""
        progress = BatchProgress(total=10, completed=5, failed=1)

        assert progress.percentage == 50.0
        assert progress.elapsed_seconds >= 0

    @patch.object(LLMEvaluator, "evaluate_ticket")
    def test_evaluate_batch(self, mock_evaluate, sample_ticket):
        """Test batch evaluation."""
        mock_evaluate.return_value = [
            MagicMock(criterion_id="test", score=10, passed=True)
        ]

        client = OpenAIClient(api_key="test-key")
        batch_evaluator = BatchLLMEvaluator(client, concurrency=2)

        tickets = [sample_ticket, sample_ticket]
        result = batch_evaluator.evaluate_batch(tickets, TemplateType.INCIDENT_LOGGING)

        assert result.total_tickets == 2
        assert result.successful == 2
        assert result.failed == 0
        assert result.success_rate == 100.0

    @patch.object(LLMEvaluator, "evaluate_ticket")
    def test_evaluate_batch_with_failures(self, mock_evaluate, sample_ticket):
        """Test batch evaluation with some failures."""
        mock_evaluate.side_effect = [
            [MagicMock(criterion_id="test", score=10, passed=True)],
            LLMAPIError("API Error"),
        ]

        client = OpenAIClient(api_key="test-key")
        batch_evaluator = BatchLLMEvaluator(client)

        tickets = [sample_ticket, sample_ticket]
        result = batch_evaluator.evaluate_batch(tickets, TemplateType.INCIDENT_LOGGING)

        assert result.total_tickets == 2
        assert result.successful == 1
        assert result.failed == 1
        assert result.success_rate == 50.0

    @patch.object(LLMEvaluator, "evaluate_ticket")
    def test_evaluate_batch_with_progress_callback(self, mock_evaluate, sample_ticket):
        """Test batch evaluation with progress callback."""
        mock_evaluate.return_value = [MagicMock()]

        client = OpenAIClient(api_key="test-key")
        batch_evaluator = BatchLLMEvaluator(client)

        progress_updates = []

        def callback(progress: BatchProgress):
            progress_updates.append(progress.percentage)

        tickets = [sample_ticket, sample_ticket, sample_ticket]
        batch_evaluator.evaluate_batch(
            tickets,
            TemplateType.INCIDENT_LOGGING,
            progress_callback=callback,
        )

        # Should have received progress updates
        assert len(progress_updates) > 0

    @patch.object(LLMEvaluator, "evaluate_ticket")
    @patch.object(LLMEvaluator, "get_full_evaluation")
    def test_evaluate_single(self, mock_full, mock_evaluate, sample_ticket):
        """Test single ticket evaluation."""
        mock_evaluate.return_value = [MagicMock()]
        mock_full.return_value = MagicMock()

        client = OpenAIClient(api_key="test-key")
        batch_evaluator = BatchLLMEvaluator(client)

        result = batch_evaluator.evaluate_single(sample_ticket, TemplateType.INCIDENT_LOGGING)

        assert result.success is True
        assert result.ticket_number == "INC1234567"


# ============================================================================
# Integration-style Tests (with full mock chain)
# ============================================================================


class TestIntegration:
    """Integration-style tests with full mock chain."""

    @patch("tqrs.llm.client.OpenAI")
    def test_full_evaluation_flow(
        self,
        mock_openai_class,
        sample_ticket,
        mock_description_response,
        mock_spelling_response,
    ):
        """Test complete evaluation flow."""
        # Set up mock responses
        responses = [
            json.dumps(mock_description_response),
            json.dumps(mock_spelling_response),
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

        # Run evaluation
        client = OpenAIClient(api_key="test-key")
        evaluator = LLMEvaluator(client)
        results = evaluator.evaluate_ticket(sample_ticket, TemplateType.INCIDENT_LOGGING)

        # Verify results
        assert len(results) == 2
        assert results[0].criterion_id == "accurate_description"
        assert results[0].score == 20
        assert results[1].criterion_id == "spelling_grammar"
        assert results[1].score == 2

        # Verify token tracking
        assert client.token_usage.total_tokens == 300  # 2 calls * 150
