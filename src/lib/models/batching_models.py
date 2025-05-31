from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from mcp_shared_lib.src.models.git_models import FileChange
from .agent_models import PatternAnalysisResult, PRGroupingStrategy, GroupingStrategyDecision
from mcp_shared_lib.src.models.analysis_models import RepositoryAnalysis

class BatchSplitterInput(BaseModel):
    """Input for the BatchSplitterTool."""
    repository_analysis: RepositoryAnalysis = Field(..., description="The overall analysis of the repository.")
    pattern_analysis: Optional[PatternAnalysisResult] = Field(None, description="Global pattern analysis results.")
    target_batch_size: int = Field(default=50, description="Desired number of files per batch.")

class BatchSplitterOutput(BaseModel):
    """Output of the BatchSplitterTool."""
    batches: List[List[str]] = Field(..., description="List of batches, where each inner list contains file paths (or file_ids).")
    strategy_used: str = Field(..., description="Description of the splitting strategy applied.")
    notes: Optional[str] = Field(None, description="Any relevant notes about the splitting.")

class GroupMergingInput(BaseModel):
    """Input for the GroupMergingTool."""
    batch_grouping_results: List[PRGroupingStrategy] = Field(..., description="List of PRGroupingStrategy results, one from each processed batch.")
    original_repository_analysis: RepositoryAnalysis = Field(..., description="The original, full repository analysis for context and ensuring all files are covered.")
    pattern_analysis: Optional[PatternAnalysisResult] = Field(None, description="Global pattern analysis results.")

class GroupMergingOutput(BaseModel):
    """Output of the GroupMergingTool."""
    merged_grouping_strategy: PRGroupingStrategy = Field(..., description="The final PRGroupingStrategy containing merged and potentially refined groups.")
    unmerged_files: List[str] = Field(default_factory=list, description="List of file paths that couldn't be merged or assigned to a group.")
    notes: Optional[str] = Field(None, description="Any relevant notes about the merging process.")

class WorkerBatchContext(BaseModel):
    """Context provided to the worker crew for processing a single batch."""
    batch_file_paths: List[str] = Field(..., description="List of file paths (or file_ids) to process in this batch.")
    repository_analysis: RepositoryAnalysis = Field(..., description="The full repository analysis (or a relevant subset/summary).")
    pattern_analysis: Optional[PatternAnalysisResult] = Field(None, description="Global pattern analysis results.")
    grouping_strategy_decision: GroupingStrategyDecision = Field(...,
        description="The full GroupingStrategyDecision object containing the chosen strategy type and supporting info."
    )
    repo_path: str = Field(..., description="Path to the repository.")
