"""
Validation Service - Provides functionality for validating PR groups
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ValidationService:
    """Service for validating PR groups"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Validation service with configuration"""
        self.config = config
        self.rules_config = config.get('validation_rules', {})
        logger.info("Validation service initialized")
    
    async def validate_pr_groups(
        self, 
        groups: List[Dict[str, Any]], 
        validation_rules: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Validate suggested PR groupings against a set of rules.
        
        Args:
            groups: List of suggested PR groups
            validation_rules: List of validation rule names to apply. If None, apply all configured rules.
            
        Returns:
            Validation results for each group
        """
        logger.info(f"Validating {len(groups)} PR groups with rules: {validation_rules or 'all'}")
        
        results = []
        
        # Determine which rules to apply
        rules_to_apply = validation_rules if validation_rules is not None else list(self.rules_config.keys())
        
        for group in groups:
            group_results = {
                "group": group.get("name", "Untitled Group"),
                "is_valid": True,
                "errors": [],
                "warnings": []
            }
            
            for rule_name in rules_to_apply:
                rule_config = self.rules_config.get(rule_name)
                if not rule_config:
                    group_results["warnings"].append(f"Unknown validation rule: {rule_name}")
                    continue
                
                # Apply the validation rule
                is_valid, messages = await self._apply_rule(rule_name, rule_config, group)
                
                if not is_valid:
                    group_results["is_valid"] = False
                    group_results["errors"].extend(messages)
                elif messages:
                    group_results["warnings"].extend(messages)
            
            results.append(group_results)
            
        return results
    
    async def _apply_rule(self, rule_name: str, rule_config: Dict[str, Any], group: Dict[str, Any]) -> (bool, List[str]):
        """Apply a specific validation rule to a PR group"""
        logger.debug(f"Applying rule '{rule_name}' to group '{group.get('name', 'Untitled')}'")
        
        messages = []
        is_valid = True
        
        if rule_name == "size_check":
            # Check if the group is too large
            max_files = rule_config.get("max_files")
            max_total_changes = rule_config.get("max_total_changes")
            
            files = group.get("files", [])
            file_count = len(files)
            
            # File count check
            if max_files is not None and file_count > max_files:
                is_valid = False
                messages.append(f"Group exceeds maximum file count ({file_count}/{max_files})")
                
            # Total changes check (if data available)
            if max_total_changes is not None and "estimated_size" in group:
                estimated_size = group.get("estimated_size", 0)
                if estimated_size > max_total_changes:
                    is_valid = False
                    messages.append(f"Group exceeds maximum change size ({estimated_size}/{max_total_changes})")
            
        elif rule_name == "cohesion_check":
            # Verify files in the group are related
            min_cohesion_score = rule_config.get("min_cohesion_score", 0.5)
            
            # Factors that improve cohesion
            has_feature_focus = "feature_focus" in group and group["feature_focus"]
            has_directory_focus = "directory_focus" in group and group["directory_focus"]
            
            files = group.get("files", [])
            
            # If group has a clear focus and reasonable size, consider it cohesive
            if (has_feature_focus or has_directory_focus) and len(files) <= 20:
                pass # Cohesion is good
            elif len(files) > 5 and not (has_feature_focus or has_directory_focus):
                # Large group with no clear focus might not be cohesive
                is_valid = False
                messages.append("Group lacks cohesion - files may not be logically related")
            
            # Check extensions - highly diverse extensions may indicate low cohesion
            extensions = set()
            for file in files:
                ext = file.split(".")[-1] if "." in file else ""
                if ext:
                    extensions.add(ext)
            
            if len(extensions) > 5 and len(files) > 10:
                messages.append(f"Group contains many different file types ({len(extensions)}), which may indicate low cohesion")
        
        elif rule_name == "dependency_check":
            # Check for dependency completeness - all required dependencies should be in the same group
            check_completeness = rule_config.get("check_completeness", True)
            
            if check_completeness and "dependency_graph" in rule_config:
                dependency_graph = rule_config["dependency_graph"]
                files = group.get("files", [])
                
                # Check if any dependencies are missing from the group
                missing_deps = []
                for file in files:
                    if file in dependency_graph:
                        deps = dependency_graph[file]
                        for dep in deps:
                            if dep not in files:
                                missing_deps.append((file, dep))
                
                if missing_deps:
                    # Only show up to 3 examples to avoid overly long messages
                    examples = missing_deps[:3]
                    is_valid = False
                    messages.append(f"Group is missing dependencies: {examples} " + 
                                  f"(and {len(missing_deps) - 3} more)" if len(missing_deps) > 3 else "")
        
        elif rule_name == "test_coverage":
            # Check if implementation files have corresponding test files
            require_tests = rule_config.get("require_tests", False)
            test_patterns = rule_config.get("test_patterns", ["test_*.py", "*_test.py", "*.spec.ts", "*.test.js"])
            
            if require_tests:
                files = group.get("files", [])
                
                # Identify implementation and test files
                impl_files = []
                test_files = []
                
                for file in files:
                    # Check if file matches any test pattern
                    is_test = False
                    for pattern in test_patterns:
                        # Convert glob pattern to regex
                        pattern_regex = pattern.replace(".", "\\.").replace("*", ".*")
                        if re.search(pattern_regex, file):
                            is_test = True
                            break
                    
                    if is_test:
                        test_files.append(file)
                    else:
                        impl_files.append(file)
                
                # Check if implementation files have corresponding test files
                if impl_files and not test_files:
                    messages.append("Group contains implementation files but no test files")
        
        elif rule_name == "balanced_changes":
            # Check if the group has a balanced mix of additions and deletions
            max_imbalance_ratio = rule_config.get("max_imbalance_ratio", 10.0)
            
            if "additions" in group and "deletions" in group:
                additions = group.get("additions", 0)
                deletions = group.get("deletions", 0)
                
                # Skip check if changes are minimal
                if additions + deletions > 100:
                    # Calculate imbalance ratio
                    ratio = (additions / max(1, deletions)) if additions > deletions else (deletions / max(1, additions))
                    
                    if ratio > max_imbalance_ratio:
                        messages.append(f"Group has highly imbalanced changes (ratio: {ratio:.1f}). " +
                                       f"Additions: {additions}, Deletions: {deletions}")
        
        elif rule_name == "cross_module_check":
            # Check if the group spans too many different modules/components
            max_modules = rule_config.get("max_modules", 3)
            
            # Extract top-level directories from files
            top_dirs = set()
            for file in group.get("files", []):
                parts = file.split("/")
                if len(parts) > 1:
                    top_dirs.add(parts[0])
            
            if len(top_dirs) > max_modules:
                is_valid = False
                messages.append(f"Group spans too many modules/components ({len(top_dirs)}): {', '.join(top_dirs)}")
        
        else:
            # Rule not recognized
            messages.append(f"Rule '{rule_name}' not implemented.")
            # We don't fail validation for unimplemented rules
            
        return is_valid, messages
