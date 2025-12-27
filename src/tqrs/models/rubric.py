"""Scoring rubric models for TQRS."""

import json
from pathlib import Path

from pydantic import BaseModel, Field

from tqrs.models.evaluation import TemplateType


class ScoringOption(BaseModel):
    """One scoring choice for a criterion."""

    score: int | str = Field(..., description="Score value or special code (PASS/FAIL/N/A)")
    description: str = Field(..., description="Description of this scoring level")
    notes: str = Field("", description="Additional guidance notes")

    @property
    def is_special(self) -> bool:
        """Check if this is a special score (PASS/FAIL/N/A)."""
        return isinstance(self.score, str)

    @property
    def is_pass(self) -> bool:
        """Check if this represents a PASS."""
        return self.score == "PASS"

    @property
    def is_fail(self) -> bool:
        """Check if this represents a FAIL."""
        return self.score == "FAIL"

    @property
    def is_na(self) -> bool:
        """Check if this represents N/A."""
        return self.score == "N/A"

    @property
    def numeric_score(self) -> int:
        """Get numeric score value (0 for special codes)."""
        if isinstance(self.score, int):
            return self.score
        return 0


class Criterion(BaseModel):
    """Single evaluation criterion from a rubric."""

    id: str = Field(..., description="Unique criterion identifier")
    name: str = Field(..., description="Human-readable criterion name")
    max_points: int = Field(..., description="Maximum points for this criterion")
    options: list[ScoringOption] = Field(..., description="Available scoring options")
    notes: str = Field("", description="Additional guidance notes")
    category: str = Field("general", description="Criterion category")
    evaluation_type: str = Field("llm", description="How to evaluate: 'rules' or 'llm'")

    @property
    def is_deduction(self) -> bool:
        """Check if this criterion is a deduction (like validation or critical process)."""
        return any(
            isinstance(opt.score, int) and opt.score < 0 for opt in self.options
        ) or any(opt.is_fail for opt in self.options)

    @property
    def is_validation(self) -> bool:
        """Check if this is the validation criterion."""
        return "validation" in self.name.lower()

    @property
    def is_critical_process(self) -> bool:
        """Check if this is the critical process criterion."""
        return "critical process" in self.name.lower()

    def get_option_by_score(self, score: int | str) -> ScoringOption | None:
        """Get scoring option by score value."""
        return next((opt for opt in self.options if opt.score == score), None)


class ScoringRubric(BaseModel):
    """Complete rubric for one evaluation template."""

    template: TemplateType = Field(..., description="Template type")
    template_name: str = Field(..., description="Display name for template")
    total_points: int = Field(70, description="Maximum possible score")
    criteria: list[Criterion] = Field(..., description="All criteria for this template")

    def get_criterion(self, criterion_id: str) -> Criterion | None:
        """Get a specific criterion by ID."""
        return next((c for c in self.criteria if c.id == criterion_id), None)

    def get_criterion_by_name(self, name: str) -> Criterion | None:
        """Get a specific criterion by name (case-insensitive partial match)."""
        name_lower = name.lower()
        return next(
            (c for c in self.criteria if name_lower in c.name.lower()),
            None,
        )

    @property
    def scoring_criteria(self) -> list[Criterion]:
        """Get criteria that contribute to base score (excludes deductions)."""
        return [c for c in self.criteria if not c.is_deduction]

    @property
    def deduction_criteria(self) -> list[Criterion]:
        """Get criteria that are deductions."""
        return [c for c in self.criteria if c.is_deduction]

    @property
    def calculated_max_points(self) -> int:
        """Sum of max points from scoring criteria."""
        return sum(c.max_points for c in self.scoring_criteria)


def _generate_criterion_id(name: str) -> str:
    """Generate a criterion ID from the name."""
    # Convert to lowercase, replace spaces/special chars with underscores
    cleaned = name.lower().strip()
    cleaned = cleaned.replace(" / ", "_").replace("/", "_")
    cleaned = cleaned.replace(" ", "_").replace("(", "").replace(")", "")
    cleaned = cleaned.replace(",", "").replace(".", "")
    # Remove consecutive underscores
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")


def _determine_evaluation_type(criterion_name: str) -> str:
    """Determine if criterion should be evaluated by rules or LLM."""
    rules_keywords = [
        "category",
        "subcategory",
        "service",
        "configuration item",
        "short description",
        "validation",
        "critical process",
    ]
    name_lower = criterion_name.lower()
    for keyword in rules_keywords:
        if keyword in name_lower:
            return "rules"
    return "llm"


def _determine_category(criterion_name: str) -> str:
    """Determine the category for a criterion."""
    name_lower = criterion_name.lower()
    if any(kw in name_lower for kw in ["category", "subcategory", "service", "configuration"]):
        return "classification"
    if "description" in name_lower:
        return "documentation"
    if "validation" in name_lower:
        return "validation"
    if "critical" in name_lower:
        return "critical_process"
    if "spelling" in name_lower or "grammar" in name_lower:
        return "quality"
    if any(kw in name_lower for kw in ["troubleshoot", "resolution", "close notes"]):
        return "troubleshooting"
    if any(kw in name_lower for kw in ["customer", "professional", "empathy"]):
        return "customer_service"
    return "general"


def _calculate_max_points(options: list[ScoringOption]) -> int:
    """Calculate max points from scoring options."""
    numeric_scores = [
        opt.score for opt in options if isinstance(opt.score, int) and opt.score > 0
    ]
    return max(numeric_scores) if numeric_scores else 0


def load_rubrics(path: Path) -> dict[TemplateType, ScoringRubric]:
    """Load all scoring rubrics from JSON file.

    Args:
        path: Path to scoring_rubrics.json

    Returns:
        Dictionary mapping TemplateType to ScoringRubric

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is invalid JSON
        ValueError: If rubric structure is invalid
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rubrics: dict[TemplateType, ScoringRubric] = {}

    # Map JSON keys to TemplateType
    template_map = {
        "Incident Logging": TemplateType.INCIDENT_LOGGING,
        "Incident Handling": TemplateType.INCIDENT_HANDLING,
        "Customer Service": TemplateType.CUSTOMER_SERVICE,
    }

    for json_key, template_type in template_map.items():
        if json_key not in data:
            continue

        template_data = data[json_key]
        criteria = []

        for crit_data in template_data.get("criteria", []):
            criterion_name = crit_data["criterion"]
            options = [
                ScoringOption(
                    score=opt["score"],
                    description=opt.get("description", ""),
                    notes=opt.get("notes", ""),
                )
                for opt in crit_data.get("scoring_options", [])
            ]

            criterion = Criterion(
                id=_generate_criterion_id(criterion_name),
                name=criterion_name,
                max_points=_calculate_max_points(options),
                options=options,
                notes=crit_data.get("notes", ""),
                category=_determine_category(criterion_name),
                evaluation_type=_determine_evaluation_type(criterion_name),
            )
            criteria.append(criterion)

        rubric = ScoringRubric(
            template=template_type,
            template_name=template_data.get("template_name", json_key),
            criteria=criteria,
        )
        rubrics[template_type] = rubric

    return rubrics


def load_rubric(path: Path, template: TemplateType) -> ScoringRubric:
    """Load a specific rubric by template type.

    Args:
        path: Path to scoring_rubrics.json
        template: Which template to load

    Returns:
        The requested ScoringRubric

    Raises:
        KeyError: If template not found in rubrics
    """
    rubrics = load_rubrics(path)
    if template not in rubrics:
        raise KeyError(f"Template {template.value} not found in rubrics")
    return rubrics[template]
