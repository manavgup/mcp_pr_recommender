"""Git models copied from mcp_local_repo_analyzer for independence."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class FileStatus(BaseModel):
    """Represents the status of a single file."""

    path: str = Field(..., description="File path relative to repository root")
    status_code: str = Field(..., description="Git status code (M, A, D, R, etc.)")
    staged: bool = Field(False, description="File is staged for commit")
    lines_added: int = Field(0, ge=0, description="Lines added")
    lines_deleted: int = Field(0, ge=0, description="Lines deleted")
    is_binary: bool = Field(False, description="File is binary")

    @property
    def total_changes(self) -> int:
        """Total number of line changes."""
        return self.lines_added + self.lines_deleted

    @property
    def file_type(self) -> str:
        """Determine file type based on status_code and staged flag."""
        if self.staged:
            return "staged"
        elif self.status_code == "?":
            return "untracked"
        elif self.status_code in ["M", "A", "D", "R", "C", "U"]:
            return "tracked"
        else:
            return "unknown"

    @property
    def is_untracked(self) -> bool:
        """Check if file is untracked."""
        return self.status_code == "?"

    @property
    def is_staged(self) -> bool:
        """Check if file is staged."""
        return self.staged

    @property
    def is_tracked_change(self) -> bool:
        """Check if file is a tracked change."""
        return self.status_code in ["M", "A", "D", "R", "C", "U"] and not self.staged


class ChangeCategorization(BaseModel):
    """Categorization of changed files by type."""

    critical_files: list[str] = Field(default_factory=list)
    source_code: list[str] = Field(default_factory=list)
    documentation: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    configuration: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Assessment of risk level for changes."""

    risk_level: Literal["low", "medium", "high"] = Field(...)
    risk_factors: list[str] = Field(default_factory=list)
    large_changes: list[str] = Field(default_factory=list)
    potential_conflicts: list[str] = Field(default_factory=list)


class OutstandingChangesAnalysis(BaseModel):
    """Analysis input from mcp_local_repo_analyzer."""

    repository_path: Path = Field(...)
    analysis_timestamp: datetime = Field(...)
    total_outstanding_files: int = Field(0, ge=0)
    categories: ChangeCategorization = Field(default_factory=ChangeCategorization)
    risk_assessment: RiskAssessment = Field(...)
    summary: str = Field(...)

    # File lists
    working_directory_files: list[FileStatus] = Field(default_factory=list)
    staged_files: list[FileStatus] = Field(default_factory=list)

    @property
    def all_changed_files(self) -> list[FileStatus]:
        """Get all changed files across categories."""
        return self.working_directory_files + self.staged_files
