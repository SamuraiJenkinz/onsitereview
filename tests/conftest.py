"""Pytest fixtures for TQRS tests."""

from pathlib import Path

import pytest

from tqrs.models import ServiceNowTicket
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
def parser() -> ServiceNowParser:
    """ServiceNow parser instance."""
    return ServiceNowParser()


@pytest.fixture
def sample_tickets(parser: ServiceNowParser, sample_tickets_path: Path) -> list[ServiceNowTicket]:
    """Parse and return sample tickets."""
    return parser.parse_file(sample_tickets_path)
