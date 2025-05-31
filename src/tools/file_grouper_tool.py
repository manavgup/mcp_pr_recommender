import json
import re
from typing import Type, List, Dict, Any, Set, Optional

from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from mcp_shared_lib.src.tools.base_tool import BaseRepoTool
from mcp_pr_recommender.src.lib.models.agent_models import (
    PRGroupingStrategy, PRGroup, GroupingStrategyType, PatternAnalysisResult
)
from mcp_shared_lib.src.models.analysis_models import RepositoryAnalysis, DirectorySummary, FileChange
from mcp_shared_lib.src.models.git_models import FileStatusType
from shared.utils.logging_utils import get_logger
from mcp_shared_lib.src.models.analysis_models import RepositoryAnalysis, DirectorySummary, FileChange
from mcp_shared_lib.src.models.git_models import FileStatusType

logger = get_logger(__name__)

class FileGrouperToolSchemaMinimalPrimitives(BaseModel):
    batch_file_paths: List[str] = Field(..., description="List of file paths for the current batch.")
    strategy_type_value: str = Field(..., description="The chosen grouping strategy type value (e.g., 'mixed', 'directory_based').")
    repository_analysis_json: str = Field(..., description="REQUIRED: The full JSON string serialization of the RepositoryAnalysis object for context.")
    pattern_analysis_json: Optional[str] = Field(None, description="Optional JSON string serialization of the PatternAnalysisResult object.")

class FileGrouperTool(BaseRepoTool):
    name: str = "File Grouper Tool"
    description: str = "Groups a specific batch of files (provided as a list of paths) using a designated strategy type, referencing full repository and pattern analysis context provided as JSON strings."
    args_schema: Type[BaseModel] = FileGrouperToolSchemaMinimalPrimitives

    def _run(
        self,
        batch_file_paths: List[str],
        strategy_type_value: str,
        repository_analysis_json: str,
        pattern_analysis_json: Optional[str] = None
    ) -> str:
        logger.info(f"FileGrouperTool received batch_file_paths: {batch_file_paths[:5]}... ({len(batch_file_paths)} total)")
        logger.info(f"FileGrouperTool received strategy_type_value: {strategy_type_value}")
        logger.info(f"FileGrouperTool received repository_analysis_json: {repository_analysis_json[:100]}...")
        logger.info(f"FileGrouperTool received pattern_analysis_json (exists): {pattern_analysis_json is not None}")

        groups: List[PRGroup] = []
        strategy_type: GroupingStrategyType = GroupingStrategyType.MIXED

        try:
            try:
                strategy_type = GroupingStrategyType(strategy_type_value)
            except ValueError:
                logger.warning(f"Invalid strategy_type_value '{strategy_type_value}' received. Defaulting to MIXED.")
                strategy_type = GroupingStrategyType.MIXED

            repository_analysis_json = self._clean_json_string(repository_analysis_json)
            if pattern_analysis_json:
                pattern_analysis_json = self._clean_json_string(pattern_analysis_json)

            if not repository_analysis_json or not repository_analysis_json.strip().startswith('{'):
                raise ValueError("Received empty or invalid repository_analysis_json string.")

            repo_analysis_dict = json.loads(repository_analysis_json)
            if "repo_path" not in repo_analysis_dict:
                repo_analysis_dict["repo_path"] = self._repo_path
                repository_analysis_json = json.dumps(repo_analysis_dict)

            repository_analysis = RepositoryAnalysis.model_validate_json(repository_analysis_json)
            directory_summaries = repository_analysis.directory_summaries or []
            all_file_changes = repository_analysis.file_changes or []

            pattern_analysis = PatternAnalysisResult()
            if pattern_analysis_json and pattern_analysis_json.strip().startswith('{'):
                try:
                    pattern_analysis = PatternAnalysisResult.model_validate_json(pattern_analysis_json)
                except (ValidationError, json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Could not parse/validate optional pattern_analysis_json: {e}. Proceeding without pattern analysis.")

            batch_file_paths_set = set(batch_file_paths)
            logger.info(f"FileGrouperTool processing batch of {len(batch_file_paths_set)} files.")
            logger.info(f"Using strategy: {strategy_type.value}")

            batch_files_objects = [
                fc for fc in all_file_changes
                if hasattr(fc, 'path') and fc.path in batch_file_paths_set
            ]

            if not batch_files_objects:
                logger.warning("No FileChange objects found matching the provided batch file paths in the loaded context.")
                strategy_result = PRGroupingStrategy(
                    strategy_type=strategy_type, groups=[],
                    explanation="No files matching the batch paths found in repository analysis context.",
                    ungrouped_files=list(batch_file_paths_set)
                )
                return strategy_result.model_dump_json(indent=2)

            if strategy_type == GroupingStrategyType.DIRECTORY_BASED:
                groups = self._group_by_directory(batch_files_objects, directory_summaries)
            elif strategy_type == GroupingStrategyType.FEATURE_BASED:
                groups = self._group_by_feature(batch_files_objects, pattern_analysis)
            elif strategy_type == GroupingStrategyType.MODULE_BASED:
                groups = self._group_by_module(batch_files_objects)
            elif strategy_type == GroupingStrategyType.SIZE_BALANCED:
                groups = self._group_by_size(batch_files_objects)
            elif strategy_type == GroupingStrategyType.MIXED:
                groups = self._group_mixed(batch_files_objects, pattern_analysis, directory_summaries)
            else:
                logger.error(f"FATAL: Reached unexpected else block for strategy_type '{strategy_type}'. Defaulting.")
                groups = self._group_by_directory(batch_files_objects, directory_summaries)

            populated_groups: List[PRGroup] = []
            for group in groups:
                group.files = [str(f) for f in group.files]
                if not group.files:
                    continue
                if not group.title:
                    group.title = "Chore: Grouped changes"
                if not group.rationale:
                    group.rationale = f"Group created by {strategy_type.value} strategy for this batch."
                group.suggested_branch_name = self._generate_branch_name(group.title)
                group.suggested_pr_description = self._generate_pr_description(group, batch_files_objects)
                populated_groups.append(group)

            all_grouped_files_in_batch = set().union(*(set(g.files) for g in populated_groups if g.files))
            ungrouped_in_batch = list(batch_file_paths_set - all_grouped_files_in_batch)
            if ungrouped_in_batch:
                logger.warning(f"{len(ungrouped_in_batch)} files remain ungrouped.")

            strategy_explanation = self._generate_strategy_explanation(strategy_type.value, populated_groups, len(batch_files_objects))
            estimated_complexity = self._estimate_review_complexity(populated_groups)
            strategy_result = PRGroupingStrategy(
                strategy_type=strategy_type, groups=populated_groups, explanation=strategy_explanation,
                estimated_review_complexity=estimated_complexity, ungrouped_files=ungrouped_in_batch
            )
            return strategy_result.model_dump_json(indent=2)

        except (ValidationError, json.JSONDecodeError, TypeError, ValueError) as e:
            error_msg = f"Error during FileGrouperTool execution: {e}"
            logger.error(error_msg, exc_info=True)
            error_result = PRGroupingStrategy(
                strategy_type=strategy_type, groups=[],
                explanation=f"Error during file grouping for batch: {e}",
                estimated_review_complexity=1.0,
                ungrouped_files=batch_file_paths if batch_file_paths else []
            )
            return error_result.model_dump_json(indent=2)
        except Exception as e:
            final_strategy_type = strategy_type if strategy_type else GroupingStrategyType.MIXED
            logger.error(f"Unexpected error grouping files with strategy {final_strategy_type.value}: {e}", exc_info=True)
            error_result = PRGroupingStrategy(
                strategy_type=final_strategy_type, groups=[],
                explanation=f"Unexpected error during file grouping for batch: {e}",
                estimated_review_complexity=1.0,
                ungrouped_files=batch_file_paths if batch_file_paths else []
            )
            return error_result.model_dump_json(indent=2)

    def _group_by_directory(self, batch_files_objects: List[FileChange], directory_summaries: List[DirectorySummary]) -> List[PRGroup]:
        groups: List[PRGroup] = []
        dir_to_files = defaultdict(list)
        for file_ctx in batch_files_objects:
            directory = file_ctx.directory or "(root)"
            if directory and file_ctx.path:
                dir_to_files[directory].append(file_ctx.path)
        for directory, files in dir_to_files.items():
            if files:
                groups.append(PRGroup(title=f"Refactor: Changes in directory '{directory}'", files=files, rationale=f"Batch changes focused within the '{directory}' directory.", directory_focus=directory, estimated_size=len(files)))
        return groups

    def _group_by_feature(self, batch_files_objects: List[FileChange], pattern_analysis: PatternAnalysisResult) -> List[PRGroup]:
        groups: List[PRGroup] = []
        assigned_files: Set[str] = set()
        current_batch_paths: Set[str] = {fc.path for fc in batch_files_objects if fc.path}
        if not current_batch_paths:
            return []
        def add_group_if_valid(title, files_from_pattern, rationale, feature_focus):
            if not isinstance(files_from_pattern, list):
                return
            valid_files = [f for f in files_from_pattern if isinstance(f, str) and f in current_batch_paths and f not in assigned_files]
            if valid_files:
                groups.append(PRGroup(title=title, files=valid_files, rationale=rationale, feature_focus=feature_focus, estimated_size=len(valid_files)))
                assigned_files.update(valid_files)
        if pattern_analysis.naming_patterns:
            for pattern in pattern_analysis.naming_patterns:
                pattern_type = getattr(pattern, 'type', None)
                pattern_matches = getattr(pattern, 'matches', None)
                if pattern_type and pattern_matches:
                    add_group_if_valid(f"Feature: Relates to {pattern_type}", pattern_matches, f"Batch changes related to {pattern_type} based on file naming patterns.", pattern_type)
        if pattern_analysis.similar_names:
            for similar_group in pattern_analysis.similar_names:
                base_pattern = getattr(similar_group, 'base_pattern', None)
                similar_files = getattr(similar_group, 'files', None)
                if base_pattern and similar_files:
                    add_group_if_valid(f"Feature: Files related to '{base_pattern}'", similar_files, f"Batch files sharing the common base pattern '{base_pattern}'.", base_pattern)
        if hasattr(pattern_analysis, 'common_patterns') and pattern_analysis.common_patterns:
            common_patterns_obj = pattern_analysis.common_patterns
            if hasattr(common_patterns_obj, 'common_prefixes'):
                for prefix_group in common_patterns_obj.common_prefixes:
                    prefix = getattr(prefix_group, 'pattern_value', None)
                    prefix_files = getattr(prefix_group, 'files', None)
                    if prefix and prefix_files:
                        add_group_if_valid(f"Feature: Files with prefix '{prefix}'", prefix_files, f"Batch files sharing the common prefix '{prefix}'.", f"prefix-{prefix}")
            if hasattr(common_patterns_obj, 'common_suffixes'):
                for suffix_group in common_patterns_obj.common_suffixes:
                    suffix = getattr(suffix_group, 'pattern_value', None)
                    suffix_files = getattr(suffix_group, 'files', None)
                    if suffix and suffix_files:
                        add_group_if_valid(f"Feature: Files with suffix '{suffix}'", suffix_files, f"Batch files sharing the common suffix '{suffix}'.", f"suffix-{suffix}")
        remaining_files_paths = [fc.path for fc in batch_files_objects if fc.path and fc.path not in assigned_files]
        if remaining_files_paths:
            groups.append(PRGroup(title="Feature: Other Related Changes", files=remaining_files_paths, rationale="Remaining files in the batch, potentially related by feature context.", feature_focus="misc-feature", estimated_size=len(remaining_files_paths)))
        return groups

    def _group_by_module(self, batch_files_objects: List[FileChange]) -> List[PRGroup]:
        logger.info(f"Starting module-based grouping for {len(batch_files_objects)} files")
        module_groups = defaultdict(list)
        for file_ctx in batch_files_objects:
            extension = file_ctx.extension or "(noext)"
            if file_ctx.path:
                module_groups[extension].append(file_ctx.path)
        logger.info(f"Created {len(module_groups)} potential module groups")
        groups = []
        for module, files in module_groups.items():
            if files:
                module_display = module.replace(".", "") if module != "(noext)" else "NoExtension"
                module_display = module_display or "NoExtension"
                groups.append(PRGroup(title=f"Chore: {module_display} module changes", files=files, rationale=f"Batch changes grouped by file type '{module}'.", feature_focus=f"module-{module_display}", estimated_size=len(files)))
        logger.debug(f"Created {len(groups)} module groups with {sum(len(g.files) for g in groups)} total files")
        return groups

    def _group_by_size(self, batch_files_objects: List[FileChange]) -> List[PRGroup]:
        groups: List[PRGroup] = []
        file_paths_in_batch = [fc.path for fc in batch_files_objects if fc.path]
        num_files = len(file_paths_in_batch)
        if num_files == 0:
            return []
        num_groups = 1 if num_files <= 5 else 2
        batch_size = (num_files + num_groups - 1) // num_groups
        for i in range(num_groups):
            start_index = i * batch_size
            end_index = min((i + 1) * batch_size, num_files)
            group_files = file_paths_in_batch[start_index:end_index]
            if group_files:
                part_num = i + 1
                groups.append(PRGroup(title=f"Chore: Batch Changes (Part {part_num}/{num_groups})", files=group_files, rationale=f"Part {part_num} of the batch, grouped for balanced size.", feature_focus=f"size-balanced-{part_num}", estimated_size=len(group_files)))
        return groups

    def _group_mixed(self, batch_files_objects: List[FileChange], pattern_analysis: PatternAnalysisResult, directory_summaries: List[DirectorySummary]) -> List[PRGroup]:
        feature_groups = self._group_by_feature(batch_files_objects, pattern_analysis)
        assigned_files: Set[str] = set()
        filtered_feature_groups: List[PRGroup] = []
        for group in feature_groups:
            if group.files and isinstance(group.files, list):
                unique_files = [f for f in group.files if isinstance(f, str) and f not in assigned_files]
                if unique_files:
                    group.files = unique_files
                    filtered_feature_groups.append(group)
                    assigned_files.update(unique_files)
        remaining_files_objs = [fc for fc in batch_files_objects if fc.path and fc.path not in assigned_files]
        if remaining_files_objs:
            directory_groups_for_remaining = self._group_by_directory(remaining_files_objs, directory_summaries)
            combined_groups = filtered_feature_groups + [g for g in directory_groups_for_remaining if g.files]
        else:
            combined_groups = filtered_feature_groups
        return combined_groups
