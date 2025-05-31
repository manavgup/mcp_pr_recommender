"""
Grouping Service - Provides functionality for suggesting PR boundaries
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class GroupingService:
    """Service for suggesting PR boundaries"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Grouping service with configuration"""
        self.config = config
        self.strategies_config = config.get('strategies', {})
        logger.info("Grouping service initialized")
    
    async def suggest_pr_boundaries(
        self, 
        analysis: Dict[str, Any], 
        strategy: str = "hybrid", 
        max_files_per_pr: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Suggest logical PR boundaries using LLM and other strategies.
        
        Args:
            analysis: Repository analysis data
            strategy: Grouping strategy to use (semantic, directory, dependency, hybrid)
            max_files_per_pr: Maximum number of files to include in a single PR
            
        Returns:
            List of suggested PR groups
        """
        logger.info(f"Suggesting PR boundaries with strategy: {strategy}")
        
        # Implement different grouping strategies here
        if strategy == "semantic":
            return await self._semantic_grouping(analysis, max_files_per_pr)
        elif strategy == "directory":
            return await self._directory_grouping(analysis, max_files_per_pr)
        elif strategy == "dependency":
            return await self._dependency_grouping(analysis, max_files_per_pr)
        elif strategy == "hybrid":
            return await self._hybrid_grouping(analysis, max_files_per_pr)
        else:
            logger.warning(f"Unknown grouping strategy: {strategy}. Falling back to hybrid.")
            return await self._hybrid_grouping(analysis, max_files_per_pr)
    
    async def _semantic_grouping(self, analysis: Dict[str, Any], max_files_per_pr: int) -> List[Dict[str, Any]]:
        """Group files based on semantic similarity using patterns and file relationships"""
        logger.info("Performing semantic grouping")
        
        # Extract files from analysis
        files_to_group = []
        if "file_changes" in analysis:
            files_to_group = [
                {"path": fc.get("path"), "directory": fc.get("directory", ""), "extension": fc.get("extension", "")}
                for fc in analysis.get("file_changes", [])
            ]
        
        # If no files found, return empty result
        if not files_to_group:
            logger.warning("No files found in analysis for semantic grouping")
            return []
            
        # Extract pattern analysis if available
        pattern_analysis = analysis.get("patterns", {})
        naming_patterns = pattern_analysis.get("naming_patterns", [])
        similar_names = pattern_analysis.get("similar_names", [])
        common_patterns = pattern_analysis.get("common_patterns", {})
        related_files = pattern_analysis.get("related_files", [])
        
        groups = []
        assigned_files = set()
        
        # 1. Group by related files (tests, schemas, etc.)
        for relation_group in related_files:
            group_type = relation_group.get("type", "unknown")
            file_pairs = relation_group.get("pairs", [])
            
            if file_pairs:
                group_files = []
                for pair in file_pairs:
                    file1 = pair.get("file1")
                    file2 = pair.get("file2")
                    
                    if file1 and file1 not in assigned_files:
                        group_files.append(file1)
                        assigned_files.add(file1)
                    
                    if file2 and file2 not in assigned_files:
                        group_files.append(file2)
                        assigned_files.add(file2)
                
                if group_files:
                    groups.append({
                        "name": f"Feature: {group_type.replace('_', ' ').title()} Changes",
                        "files": group_files,
                        "rationale": f"Files grouped by {group_type} relationship patterns.",
                        "feature_focus": group_type
                    })
        
        # 2. Group by similar names
        for similar_group in similar_names:
            base_pattern = similar_group.get("base_pattern", "")
            files = [f for f in similar_group.get("files", []) if f not in assigned_files]
            
            if files:
                groups.append({
                    "name": f"Feature: {base_pattern} Components",
                    "files": files,
                    "rationale": f"Files sharing naming pattern '{base_pattern}'.",
                    "feature_focus": base_pattern
                })
                assigned_files.update(files)
        
        # 3. Group by common prefixes/suffixes
        if common_patterns:
            for prefix_group in common_patterns.get("common_prefixes", []):
                prefix = prefix_group.get("pattern_value", "")
                files = [f for f in prefix_group.get("files", []) if f not in assigned_files]
                
                if files and len(files) <= max_files_per_pr:
                    groups.append({
                        "name": f"Feature: {prefix} Module",
                        "files": files,
                        "rationale": f"Files sharing common prefix '{prefix}'.",
                        "feature_focus": f"prefix-{prefix}"
                    })
                    assigned_files.update(files)
            
            for suffix_group in common_patterns.get("common_suffixes", []):
                suffix = suffix_group.get("pattern_value", "")
                files = [f for f in suffix_group.get("files", []) if f not in assigned_files]
                
                if files and len(files) <= max_files_per_pr:
                    groups.append({
                        "name": f"Feature: {suffix} Components",
                        "files": files,
                        "rationale": f"Files sharing common suffix '{suffix}'.",
                        "feature_focus": f"suffix-{suffix}"
                    })
                    assigned_files.update(files)
        
        # 4. Group remaining files by extension
        extension_groups = {}
        for file_info in files_to_group:
            file_path = file_info.get("path")
            if file_path and file_path not in assigned_files:
                extension = file_info.get("extension", "")
                if not extension in extension_groups:
                    extension_groups[extension] = []
                extension_groups[extension].append(file_path)
                assigned_files.add(file_path)
        
        for ext, files in extension_groups.items():
            if files:
                ext_display = ext.replace(".", "") if ext else "Misc"
                groups.append({
                    "name": f"Chore: {ext_display} File Updates",
                    "files": files,
                    "rationale": f"Files grouped by common file type '{ext}'.",
                    "feature_focus": f"filetype-{ext}"
                })
        
        # Limit the size of groups according to max_files_per_pr
        result_groups = []
        for group in groups:
            files = group.get("files", [])
            
            # If group is too large, split it into smaller groups
            if len(files) > max_files_per_pr:
                chunks = [files[i:i + max_files_per_pr] for i in range(0, len(files), max_files_per_pr)]
                for i, chunk in enumerate(chunks):
                    new_group = dict(group)
                    new_group["name"] = f"{group['name']} (Part {i+1}/{len(chunks)})"
                    new_group["files"] = chunk
                    result_groups.append(new_group)
            else:
                result_groups.append(group)
        
        logger.info(f"Semantic grouping created {len(result_groups)} groups")
        return result_groups
    
    async def _directory_grouping(self, analysis: Dict[str, Any], max_files_per_pr: int) -> List[Dict[str, Any]]:
        """Group files based on directory structure"""
        logger.info("Performing directory grouping")
        
        # Extract files from analysis
        files_to_group = []
        if "file_changes" in analysis:
            files_to_group = [
                {"path": fc.get("path"), "directory": fc.get("directory", "")}
                for fc in analysis.get("file_changes", [])
            ]
        
        # If no files found, return empty result
        if not files_to_group:
            logger.warning("No files found in analysis for directory grouping")
            return []
        
        # Extract directory summaries if available
        directory_summaries = analysis.get("directory_summaries", [])
        directory_complexities = {}
        
        # Build a complexity map for directories
        for dir_summary in directory_summaries:
            path = dir_summary.get("path", "")
            if path:
                complexity = dir_summary.get("estimated_complexity", 1.0)
                file_count = dir_summary.get("file_count", 0)
                directory_complexities[path] = (complexity, file_count)
        
        # Group files by directory
        dir_to_files = {}
        for file_info in files_to_group:
            directory = file_info.get("directory", "")
            if not directory:
                directory = "(root)"
            
            if directory not in dir_to_files:
                dir_to_files[directory] = []
            
            dir_to_files[directory].append(file_info.get("path"))
        
        # Generate groups, considering complexity and size
        groups = []
        for directory, files in dir_to_files.items():
            if not files:
                continue
                
            # Get complexity info
            complexity, _ = directory_complexities.get(directory, (1.0, 0))
            
            # Handle large directories - split into smaller groups if needed
            if len(files) > max_files_per_pr:
                # Calculate number of groups needed
                num_groups = (len(files) + max_files_per_pr - 1) // max_files_per_pr
                
                # Split files into roughly equal groups
                for i in range(num_groups):
                    start_idx = i * max_files_per_pr
                    end_idx = min((i + 1) * max_files_per_pr, len(files))
                    group_files = files[start_idx:end_idx]
                    
                    groups.append({
                        "name": f"Refactor: Directory {directory} Changes (Part {i+1}/{num_groups})",
                        "files": group_files,
                        "rationale": f"Changes focused in the '{directory}' directory (split due to size).",
                        "directory_focus": directory,
                        "estimated_size": len(group_files)
                    })
            else:
                # Simple case - all files in one group
                groups.append({
                    "name": f"Refactor: Changes in {directory}",
                    "files": files,
                    "rationale": f"Changes focused in the '{directory}' directory.",
                    "directory_focus": directory,
                    "estimated_size": len(files)
                })
        
        logger.info(f"Directory grouping created {len(groups)} groups")
        return groups
    
    async def _dependency_grouping(self, analysis: Dict[str, Any], max_files_per_pr: int) -> List[Dict[str, Any]]:
        """Group files based on code dependencies"""
        logger.info("Performing dependency grouping")
        
        # Extract dependency information from analysis if available
        dependency_graph = analysis.get("dependency_graph", {})
        
        if not dependency_graph:
            logger.warning("No dependency information found in analysis")
            return []
        
        # Extract files from analysis
        files_to_group = []
        if "file_changes" in analysis:
            files_to_group = [
                fc.get("path") for fc in analysis.get("file_changes", []) if fc.get("path")
            ]
        
        # If no files found, return empty result
        if not files_to_group:
            logger.warning("No files found in analysis for dependency grouping")
            return []
        
        # Convert to set for faster lookups
        files_set = set(files_to_group)
        
        # Build the dependency map
        dependency_map = {}
        
        for file_path, dependencies in dependency_graph.items():
            if file_path in files_set:
                # Filter to only include dependencies that are also in our changed files
                relevant_deps = [dep for dep in dependencies if dep in files_set]
                if relevant_deps:
                    dependency_map[file_path] = relevant_deps
        
        # If no dependencies found among changed files, fall back to directory grouping
        if not dependency_map:
            logger.warning("No dependencies found among changed files, falling back to directory grouping")
            return await self._directory_grouping(analysis, max_files_per_pr)
        
        # Build connected components (dependency clusters)
        visited = set()
        components = []
        
        def dfs(node, component):
            """Depth-first search to find connected components"""
            visited.add(node)
            component.append(node)
            
            # Check dependencies (outgoing edges)
            for dep in dependency_map.get(node, []):
                if dep not in visited:
                    dfs(dep, component)
            
            # Check reverse dependencies (incoming edges)
            for file, deps in dependency_map.items():
                if node in deps and file not in visited:
                    dfs(file, component)
        
        # Find all connected components
        for file in dependency_map:
            if file not in visited:
                component = []
                dfs(file, component)
                components.append(component)
        
        # Add isolated files (no dependencies) to components
        isolated_files = [f for f in files_set if f not in visited]
        if isolated_files:
            # Group isolated files by extension
            ext_to_files = {}
            for file in isolated_files:
                ext = file.split(".")[-1] if "." in file else "unknown"
                if ext not in ext_to_files:
                    ext_to_files[ext] = []
                ext_to_files[ext].append(file)
            
            # Add each extension group as a component
            for ext, files in ext_to_files.items():
                components.append(files)
        
        # Generate groups from components, splitting if too large
        groups = []
        for i, component in enumerate(components):
            # Skip empty components
            if not component:
                continue
                
            # Determine component type by examining files
            file_exts = [f.split(".")[-1] if "." in f else "" for f in component]
            common_ext = max(set(file_exts), key=file_exts.count) if file_exts else "unknown"
            
            # If component is too large, split it
            if len(component) > max_files_per_pr:
                # Calculate number of groups needed
                num_groups = (len(component) + max_files_per_pr - 1) // max_files_per_pr
                
                # Split component into roughly equal groups
                for j in range(num_groups):
                    start_idx = j * max_files_per_pr
                    end_idx = min((j + 1) * max_files_per_pr, len(component))
                    group_files = component[start_idx:end_idx]
                    
                    groups.append({
                        "name": f"Feature: {common_ext.title()} Module Dependencies (Part {j+1}/{num_groups})",
                        "files": group_files,
                        "rationale": f"Files grouped by code dependencies (split due to size).",
                        "feature_focus": f"dependency-{common_ext}",
                        "estimated_size": len(group_files)
                    })
            else:
                # Add component as a single group
                groups.append({
                    "name": f"Feature: {common_ext.title()} Module Dependencies",
                    "files": component,
                    "rationale": "Files grouped by code dependencies.",
                    "feature_focus": f"dependency-{common_ext}",
                    "estimated_size": len(component)
                })
        
        logger.info(f"Dependency grouping created {len(groups)} groups")
        return groups
    
    async def _hybrid_grouping(self, analysis: Dict[str, Any], max_files_per_pr: int) -> List[Dict[str, Any]]:
        """Combine multiple grouping strategies with intelligent conflict resolution"""
        logger.info("Performing hybrid grouping")
        
        # Execute all grouping strategies
        semantic_groups = await self._semantic_grouping(analysis, max_files_per_pr)
        directory_groups = await self._directory_grouping(analysis, max_files_per_pr)
        dependency_groups = await self._dependency_grouping(analysis, max_files_per_pr)
        
        logger.info(f"Hybrid grouping received: {len(semantic_groups)} semantic groups, " 
                   f"{len(directory_groups)} directory groups, {len(dependency_groups)} dependency groups")
        
        # Track all files to avoid duplicates
        assigned_files = set()
        result_groups = []
        
        # Order of precedence: dependency > semantic > directory
        # Process dependency groups first (highest priority)
        for group in dependency_groups:
            files = group.get("files", [])
            # Only keep files that haven't been assigned yet
            unassigned_files = [f for f in files if f not in assigned_files]
            
            if unassigned_files:
                # Create a new group with only unassigned files
                new_group = dict(group)
                new_group["files"] = unassigned_files
                new_group["rationale"] = group.get("rationale", "") + " (Prioritized by dependency analysis.)"
                result_groups.append(new_group)
                assigned_files.update(unassigned_files)
        
        # Process semantic groups second
        for group in semantic_groups:
            files = group.get("files", [])
            unassigned_files = [f for f in files if f not in assigned_files]
            
            if unassigned_files:
                new_group = dict(group)
                new_group["files"] = unassigned_files
                new_group["rationale"] = group.get("rationale", "") + " (Prioritized by semantic analysis.)"
                result_groups.append(new_group)
                assigned_files.update(unassigned_files)
        
        # Process directory groups last
        for group in directory_groups:
            files = group.get("files", [])
            unassigned_files = [f for f in files if f not in assigned_files]
            
            if unassigned_files:
                new_group = dict(group)
                new_group["files"] = unassigned_files
                new_group["rationale"] = group.get("rationale", "") + " (Applied directory-based grouping.)"
                result_groups.append(new_group)
                assigned_files.update(unassigned_files)
        
        # Extract list of all files from the analysis
        all_files = []
        if "file_changes" in analysis:
            all_files = [
                fc.get("path") for fc in analysis.get("file_changes", []) 
                if fc.get("path")
            ]
            
        # Check for any ungrouped files
        ungrouped_files = [f for f in all_files if f not in assigned_files]
        
        # Handle any remaining files
        if ungrouped_files:
            logger.info(f"Found {len(ungrouped_files)} ungrouped files after hybrid strategy")
            
            # Group remaining files by extension
            ext_to_files = {}
            for file in ungrouped_files:
                ext = file.split(".")[-1] if "." in file else "unknown"
                if ext not in ext_to_files:
                    ext_to_files[ext] = []
                ext_to_files[ext].append(file)
            
            # Create miscellaneous groups for each extension
            for ext, files in ext_to_files.items():
                if files:
                    ext_display = ext.capitalize()
                    
                    # Split into multiple groups if too large
                    if len(files) > max_files_per_pr:
                        chunks = [files[i:i + max_files_per_pr] for i in range(0, len(files), max_files_per_pr)]
                        for i, chunk in enumerate(chunks):
                            result_groups.append({
                                "name": f"Chore: Miscellaneous {ext_display} Files (Part {i+1}/{len(chunks)})",
                                "files": chunk,
                                "rationale": f"Remaining {ext} files not covered by other grouping strategies.",
                                "feature_focus": f"misc-{ext}",
                                "estimated_size": len(chunk)
                            })
                    else:
                        result_groups.append({
                            "name": f"Chore: Miscellaneous {ext_display} Files",
                            "files": files,
                            "rationale": f"Remaining {ext} files not covered by other grouping strategies.",
                            "feature_focus": f"misc-{ext}",
                            "estimated_size": len(files)
                        })
        
        # Filter out any empty groups
        result_groups = [group for group in result_groups if group.get("files", [])]
        
        logger.info(f"Hybrid grouping created {len(result_groups)} final groups")
        return result_groups
