"""
Group validator tool for validating PR groups against best practices.
"""
from typing import List, Dict, Any, Set, Type
from pathlib import Path
import re
import json

from pydantic import BaseModel, Field, ValidationError
from mcp_shared_lib.src.utils import get_logger
from mcp_shared_lib.src.tools.base_tool import BaseRepoTool
from mcp_pr_recommender.src.lib.models.agent_models import PRGroupingStrategy, PRValidationResult, GroupValidationIssue, GroupingStrategyType

logger = get_logger(__name__)

class GroupValidatorToolSchema(BaseModel):
    """Input schema for GroupValidatorTool using primitive types."""
    pr_grouping_strategy_json: str = Field(..., description="JSON string of the PRGroupingStrategy object to validate.")
    is_final_validation: bool = Field(default=False, description="Set to true if this is the final validation after merging batches.")

class GroupValidatorTool(BaseRepoTool):
    name: str = "Group Validator Tool"
    description: str = "Validates a set of proposed PR groups against predefined rules and best practices."
    args_schema: Type[BaseModel] = GroupValidatorToolSchema

    def _run(self, pr_grouping_strategy_json: str, is_final_validation: bool = False) -> str:
        logger.info(f"GroupValidatorTool received pr_grouping_strategy_json: {pr_grouping_strategy_json[:100]}...")
        logger.info(f"GroupValidatorTool received is_final_validation: {is_final_validation}")
        
        try:
            pr_grouping_strategy_json = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', pr_grouping_strategy_json)

            if not self._validate_json_string(pr_grouping_strategy_json):
                raise ValueError("Invalid pr_grouping_strategy_json provided")
            
            try:
                json.loads(pr_grouping_strategy_json)
            except json.JSONDecodeError as je:
                logger.error(f"JSON parsing error: {je}")
                raise ValueError(f"Cannot parse pr_grouping_strategy_json: {je}")
                
            grouping_strategy = PRGroupingStrategy.model_validate_json(pr_grouping_strategy_json)
            logger.info(f"Validating {len(grouping_strategy.groups)} groups. Final validation: {is_final_validation}")

            issues: List[GroupValidationIssue] = []

            empty_groups = [g.title for g in grouping_strategy.groups if not g.files]
            if empty_groups:
                issues.append(GroupValidationIssue(
                    severity="high", issue_type="Empty Group",
                    description="Groups should not be empty.",
                    affected_groups=empty_groups,
                    recommendation="Remove or merge these groups."
                ))

            files_in_groups: Dict[str, List[str]] = {}
            all_files_set: List[str] = []
            for group in grouping_strategy.groups:
                for file_path in group.files:
                    if file_path not in files_in_groups:
                        files_in_groups[file_path] = []
                    files_in_groups[file_path].append(group.title)
                all_files_set.extend(group.files)

            duplicates = {fp: titles for fp, titles in files_in_groups.items() if len(titles) > 1}
            if duplicates:
                affected_titles = list(set(t for titles in duplicates.values() for t in titles))
                issues.append(GroupValidationIssue(
                    severity="high", issue_type="Duplicate Files",
                    description=f"Files found in multiple groups: {list(duplicates.keys())[:5]}...",
                    affected_groups=affected_titles,
                    recommendation="Ensure each file belongs to only one PR group. Refine merging logic or group definitions."
                ))

            if is_final_validation and grouping_strategy.ungrouped_files:
                issues.append(GroupValidationIssue(
                    severity="medium", issue_type="Ungrouped Files",
                    description=f"{len(grouping_strategy.ungrouped_files)} files remain ungrouped.",
                    affected_groups=[],
                    recommendation="Assign ungrouped files to existing groups or create a 'miscellaneous' group."
                ))

            is_valid = not issues
            validation_notes = f"Validation complete. Found {len(issues)} issues."
            if not is_valid:
                validation_notes += " Issues detected, refinement may be required."
            logger.info(validation_notes)

            result = PRValidationResult(
                is_valid=is_valid,
                issues=issues,
                validation_notes=validation_notes,
                strategy_type=grouping_strategy.strategy_type
            )
            return result.model_dump_json(indent=2)

        except Exception as e:
            logger.error(f"Error in GroupValidatorTool: {e}", exc_info=True)
            error_result = PRValidationResult(
                is_valid=False,
                issues=[GroupValidationIssue(severity="critical", issue_type="Tool Error", description=f"Validation failed: {e}", affected_groups=[], recommendation="Debug tool.")],
                validation_notes=f"Validation process failed: {e}",
                strategy_type=GroupingStrategyType.MIXED
            )
            return error_result.model_dump_json(indent=2)
