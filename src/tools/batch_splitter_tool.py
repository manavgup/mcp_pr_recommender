"""
Batch splitter tool for splitting files into manageable batches.
"""
from collections import defaultdict
import math
from pathlib import Path
import re
from typing import Type, List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json

from mcp_shared_lib.src.tools.base_tool import BaseRepoTool
from mcp_pr_recommender.src.lib.models.batching_models import BatchSplitterOutput
from mcp_shared_lib.src.utils import get_logger
from mcp_shared_lib.src.models.analysis_models import RepositoryAnalysis

logger = get_logger(__name__)

class BatchSplitterToolSchema(BaseModel):
    repository_analysis_json: str = Field(..., description="JSON string of the RepositoryAnalysis object.")
    pattern_analysis_json: Optional[str] = Field(None, description="JSON string of the PatternAnalysisResult object (optional).")
    target_batch_size: int = Field(default=50, description="Desired number of files per batch.")

class BatchSplitterTool(BaseRepoTool):
    name: str = "Batch Splitter Tool"
    description: str = "Splits a list of changed files into manageable batches based on size or other criteria."
    args_schema: Type[BaseModel] = BatchSplitterToolSchema

    def _run(
        self,
        repository_analysis_json: str,
        pattern_analysis_json: Optional[str] = None,
        target_batch_size: int = 50
    ) -> str:
        logger.info(f"BatchSplitterTool received repository_analysis_json: {repository_analysis_json[:100]}...")
        if pattern_analysis_json:
            logger.info(f"BatchSplitterTool received pattern_analysis_json: {pattern_analysis_json[:100]}...")
        logger.info(f"BatchSplitterTool received target_batch_size: {target_batch_size}")
        
        try:
            if not self._validate_json_string(repository_analysis_json):
                raise ValueError("Invalid repository_analysis_json provided")
            
            file_paths = self._extract_file_paths(repository_analysis_json)
            if not file_paths:
                logger.warning("No file paths found in repository_analysis_json")
                return BatchSplitterOutput(
                    batches=[], 
                    strategy_used="Empty",
                    notes="No files found to split into batches"
                ).model_dump_json(indent=2)
            
            file_metadata = self._extract_file_metadata(repository_analysis_json)
            
            target_complexity = target_batch_size * 1.5
            
            pattern_data = None
            if pattern_analysis_json and self._validate_json_string(pattern_analysis_json):
                pattern_data = self._safe_deserialize(pattern_analysis_json)
            
            if file_metadata:
                batches = self._create_adaptive_batches(file_metadata, target_complexity)
                strategy_used = f"Adaptive complexity-based splitting into {len(batches)} batches"
            elif pattern_data:
                batches = self._create_pattern_batches(file_paths, pattern_data, target_batch_size)
                strategy_used = f"Pattern-based splitting into {len(batches)} batches"
            else:
                batches = self._create_simple_batches(file_paths, target_batch_size)
                strategy_used = f"Simple count-based splitting into {len(batches)} batches"
            
            logger.info(f"Split into {len(batches)} batches using strategy: {strategy_used}")
            
            output = BatchSplitterOutput(
                batches=batches,
                strategy_used=strategy_used,
                notes=f"Target batch size was {target_batch_size}, target complexity was {target_complexity}"
            )
            return output.model_dump_json(indent=2)
            
        except Exception as e:
            logger.error(f"Error in BatchSplitterTool: {e}", exc_info=True)
            error_output = BatchSplitterOutput(
                batches=[], 
                strategy_used="Error", 
                notes=f"Failed to split batches: {e}"
            )
            return error_output.model_dump_json(indent=2)

    def _create_simple_batches(self, files: List[str], target_size: int) -> List[List[str]]:
        batches = []
        for i in range(0, len(files), target_size):
            batches.append(files[i:i + target_size])
        return batches

    def _create_pattern_batches(self, files: List[str], pattern_data: Dict[str, Any], target_size: int) -> List[List[str]]:
        batches = []
        
        if "naming_patterns" in pattern_data and pattern_data["naming_patterns"]:
            pattern_groups = defaultdict(list)
            matched_files = set()
            
            for pattern in pattern_data["naming_patterns"]:
                pattern_type = pattern.get("type", "")
                pattern_matches = pattern.get("matches", [])
                
                for file in files:
                    file_name = Path(file).name
                    if file_name in pattern_matches:
                        pattern_groups[pattern_type].append(file)
                        matched_files.add(file)
            
            for pattern_type, pattern_files in pattern_groups.items():
                if len(pattern_files) > target_size * 1.5:
                    for i in range(0, len(pattern_files), target_size):
                        batches.append(pattern_files[i:i + target_size])
                else:
                    batches.append(pattern_files)
            
            unmatched = [f for f in files if f not in matched_files]
            if unmatched:
                for i in range(0, len(unmatched), target_size):
                    batches.append(unmatched[i:i + target_size])
        
        if not batches:
            batches = self._create_simple_batches(files, target_size)
            
        return batches

    def _calculate_file_complexity(self, file_info: Dict[str, Any]) -> float:
        complexity = 1.0
        
        total_changes = file_info.get("total_changes", 0)
        if not total_changes:
            added_lines = file_info.get("added_lines", 0)
            deleted_lines = file_info.get("deleted_lines", 0)
            total_changes = added_lines + deleted_lines
            
        if total_changes > 500:
            complexity *= 3.0
        elif total_changes > 200:
            complexity *= 2.0
        elif total_changes > 50:
            complexity *= 1.5
        
        extension = file_info.get("extension", "")
        if extension in ['.py', '.java', '.cpp']:
            complexity *= 1.5
        elif extension in ['.yml', '.json', '.toml']:
            complexity *= 1.2
        
        return complexity

    def _create_adaptive_batches(self, file_metadata: List[Dict[str, Any]], target_complexity: float) -> List[List[str]]:
        batches = []
        current_batch = []
        current_complexity = 0.0
        
        sorted_files = sorted(file_metadata, 
                            key=lambda file_info: self._calculate_file_complexity(file_info),
                            reverse=True)
        
        for file_info in sorted_files:
            file_complexity = self._calculate_file_complexity(file_info)
            
            if current_complexity + file_complexity > target_complexity and current_batch:
                batches.append([file_path for file_path in current_batch])
                current_batch = []
                current_complexity = 0.0
            
            current_batch.append(file_info.get("path", ""))
            current_complexity += file_complexity
        
        if current_batch:
            batches.append([file_path for file_path in current_batch])
        
        return batches
