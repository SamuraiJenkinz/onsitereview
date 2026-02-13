"""ServiceNow ticket data model."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ServiceNowTicket(BaseModel):
    """Parsed ServiceNow incident ticket with relevant fields for evaluation."""

    # Identifiers
    number: str = Field(..., description="Ticket number (e.g., INC8924218)")
    sys_id: str = Field(..., description="Unique ServiceNow identifier")

    # Timestamps
    opened_at: datetime = Field(..., description="When ticket was opened")
    resolved_at: datetime | None = Field(None, description="When ticket was resolved")
    closed_at: datetime | None = Field(None, description="When ticket was closed")

    # People (sys_id references)
    caller_id: str = Field(..., description="Sys_id of the caller")
    opened_by: str = Field(..., description="Sys_id of who opened the ticket")
    opened_for: str = Field("", description="Sys_id of person ticket was opened for")
    assigned_to: str = Field(..., description="Sys_id of assignee")
    resolved_by: str | None = Field(None, description="Sys_id of resolver")
    closed_by: str | None = Field(None, description="Sys_id of who closed")

    # Classification
    category: str = Field(..., description="Primary category")
    subcategory: str = Field(..., description="Subcategory")
    contact_type: str = Field(..., description="Contact method (phone, chat, email, self-service)")
    priority: str = Field(..., description="Priority level (1-5)")
    impact: str = Field(..., description="Impact level (1-3)")
    urgency: str = Field(..., description="Urgency level (1-3)")

    # Content - evaluation targets
    short_description: str = Field(..., description="Brief issue summary")
    description: str = Field(..., description="Full issue description")
    work_notes: str = Field("", description="Internal work notes")
    close_notes: str = Field("", description="Resolution notes")
    close_code: str = Field("", description="Closure reason code")

    # Status
    state: str = Field(..., description="Current state (1-7, 7=closed)")
    incident_state: str = Field(..., description="Incident-specific state")

    # Business context (sys_id references)
    company: str = Field(..., description="Company sys_id")
    location: str = Field(..., description="Location sys_id")
    assignment_group: str = Field(..., description="Assignment group sys_id")
    business_service: str | None = Field(None, description="Business service sys_id")
    cmdb_ci: str | None = Field(None, description="Configuration item sys_id")

    # Line of Business boolean flags (stored as "true"/"false" strings in ServiceNow)
    u_marsh: bool = Field(False, description="Marsh LoB flag")
    u_mercer: bool = Field(False, description="Mercer LoB flag")
    u_guy_carpenter: bool = Field(False, description="Guy Carpenter LoB flag")
    u_oliver_wyman_group: bool = Field(False, description="Oliver Wyman LoB flag")
    u_mmc_corporate: bool = Field(False, description="MMC Corporate LoB flag")

    # Metadata
    reassignment_count: int = Field(0, description="Number of reassignments")
    reopen_count: int = Field(0, description="Number of reopens")

    # Computed fields (populated by parser)
    line_of_business: str | None = Field(None, description="Determined LoB")
    resolution_time_minutes: int | None = Field(None, description="Time to resolution")

    @field_validator("work_notes", "close_notes", "close_code", mode="before")
    @classmethod
    def empty_string_to_default(cls, v: str | None) -> str:
        """Convert None to empty string for optional text fields."""
        return v if v else ""

    @field_validator("business_service", "cmdb_ci", "resolved_by", "closed_by", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: str | None) -> str | None:
        """Convert empty strings to None for optional reference fields."""
        return v if v else None

    @field_validator("reassignment_count", "reopen_count", mode="before")
    @classmethod
    def string_to_int(cls, v: str | int) -> int:
        """Convert string numbers to int."""
        if isinstance(v, str):
            return int(v) if v else 0
        return v

    def get_line_of_business(self) -> str:
        """Get line of business from flags or computed field."""
        if self.line_of_business:
            return self.line_of_business

        # Check LoB flags
        if self.u_marsh:
            return "Marsh"
        if self.u_mercer:
            return "Mercer"
        if self.u_guy_carpenter:
            return "Guy Carpenter"
        if self.u_oliver_wyman_group:
            return "Oliver Wyman"
        if self.u_mmc_corporate:
            return "MMC Corporate"

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
        if " - " in self.short_description:
            prefix = self.short_description.split(" - ")[0].strip().upper()
            if prefix in lob_map:
                return lob_map[prefix]

        # Try "-" separator (alternative format like "Marsh-Mumbai-LAN-...")
        if "-" in self.short_description:
            prefix = self.short_description.split("-")[0].strip().upper()
            if prefix in lob_map:
                return lob_map[prefix]
            # Also check first two parts for "MMC-NCL" style
            parts = self.short_description.split("-")
            if len(parts) >= 2:
                compound = f"{parts[0].strip()}-{parts[1].strip()}".upper()
                if compound in lob_map:
                    return lob_map[compound]

        return "Unknown"

    @property
    def is_closed(self) -> bool:
        """Check if ticket is in closed state."""
        return self.state == "7" or self.incident_state == "7"

    @property
    def is_resolved(self) -> bool:
        """Check if ticket has been resolved."""
        return self.resolved_at is not None

