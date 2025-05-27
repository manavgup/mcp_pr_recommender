#!/usr/bin/env python3
"""
PR Recommender MCP Server - Main Entry Point
"""
import sys
import logging
from pathlib import Path
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import FastMCP
from fastmcp import FastMCP

# Import local modules
from services.grouping_service import GroupingService
from services.validation_service import ValidationService

class PRRecommenderServer:
    """PR Recommender MCP Server implementation"""
    
    def __init__(self, config_path="config/server.yaml"):
        """Initialize the server with configuration"""
        self.config = self._load_config(config_path)
        self.server_config = self.config.get('server', {})
        
        # Create FastMCP instance
        logger.info(f"Creating FastMCP server with name: {self.server_config.get('name', 'PR Recommender')}")
        self.mcp = FastMCP(
            name=self.server_config.get('name', 'PR Recommender'),
            instructions=self.server_config.get('instructions', 'This server provides tools for PR recommendation and generation.')
        )
        
        # Initialize services
        self.grouping_service = GroupingService(self.config)
        self.validation_service = ValidationService(self.config)
        
        # Register tools
        self._register_tools()
        
        logger.info("PR Recommender MCP Server initialized")
    
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def _register_tools(self):
        """Register all tools with the MCP server"""
        logger.info("Registering tools...")
        
        # Tool 1: suggest_pr_boundaries
        @self.mcp.tool(name="suggest_pr_boundaries")
        async def suggest_pr_boundaries(
            analysis: Dict[str, Any],
            strategy: str = "hybrid",
            max_files_per_pr: int = 30
        ):
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
            try:
                result = await self.grouping_service.suggest_pr_boundaries(
                    analysis=analysis,
                    strategy=strategy,
                    max_files_per_pr=max_files_per_pr
                )
                return result
            except Exception as e:
                logger.error(f"Error suggesting PR boundaries: {e}")
                return {"error": str(e)}
        
        # Tool 2: validate_pr_groups
        @self.mcp.tool(name="validate_pr_groups")
        async def validate_pr_groups(
            groups: List[Dict[str, Any]],
            validation_rules: Optional[List[str]] = None
        ):
            """
            Validate suggested PR groupings against a set of rules.
            
            Args:
                groups: List of suggested PR groups
                validation_rules: List of validation rule names to apply
                
            Returns:
                Validation results for each group
            """
            logger.info("Validating PR groups")
            try:
                result = await self.validation_service.validate_pr_groups(
                    groups=groups,
                    validation_rules=validation_rules
                )
                return result
            except Exception as e:
                logger.error(f"Error validating PR groups: {e}")
                return {"error": str(e)}
        
        # Tool 3: generate_pr_metadata
        @self.mcp.tool(name="generate_pr_metadata")
        async def generate_pr_metadata(
            pr_group: Dict[str, Any],
            template: str = "standard"
        ):
            """
            Generate PR titles, descriptions, and labels.
            
            Args:
                pr_group: A single PR group with associated files and analysis data
                template: Template to use for generating metadata
                
            Returns:
                Generated PR metadata
            """
            logger.info(f"Generating PR metadata using template: {template}")
            # This tool would typically interact with an LLM or use templates
            # For now, return a placeholder
            return {
                "title": f"Draft PR: {pr_group.get('name', 'Untitled')}",
                "body": f"Proposed changes for: {', '.join(pr_group.get('files', []))}",
                "labels": ["draft"]
            }
        
        logger.info("Tools registered successfully")
    
    def run(self):
        """Run the MCP server"""
        logger.info("Starting PR Recommender MCP Server...")
        self.mcp.run()


if __name__ == "__main__":
    # Create and run the server
    server = PRRecommenderServer()
    server.run()
