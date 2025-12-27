"""Pytest fixtures for TQRS tests."""

from pathlib import Path

import pytest

from tqrs.models import ServiceNowTicket, TemplateType, load_rubrics
from tqrs.parser import ServiceNowParser


@pytest.fixture
def project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_tickets_path(project_root: Path) -> Path:
    """Path to prototype sample tickets JSON."""
    return project_root / "prototype_samples.json"


@pytest.fixture
def rubrics_path(project_root: Path) -> Path:
    """Path to scoring rubrics JSON."""
    return project_root / "scoring_rubrics.json"


@pytest.fixture
def parser() -> ServiceNowParser:
    """ServiceNow parser instance."""
    return ServiceNowParser()


@pytest.fixture
def sample_tickets(parser: ServiceNowParser, sample_tickets_path: Path) -> list[ServiceNowTicket]:
    """Parse and return sample tickets."""
    return parser.parse_file(sample_tickets_path)


@pytest.fixture
def rubrics(rubrics_path: Path):
    """Load all scoring rubrics."""
    return load_rubrics(rubrics_path)


@pytest.fixture
def incident_logging_rubric(rubrics):
    """Get the Incident Logging rubric."""
    return rubrics[TemplateType.INCIDENT_LOGGING]


@pytest.fixture
def incident_handling_rubric(rubrics):
    """Get the Incident Handling rubric."""
    return rubrics[TemplateType.INCIDENT_HANDLING]


@pytest.fixture
def customer_service_rubric(rubrics):
    """Get the Customer Service rubric."""
    return rubrics[TemplateType.CUSTOMER_SERVICE]
