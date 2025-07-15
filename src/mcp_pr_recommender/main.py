#!/usr/bin/env python3
"""FastMCP server for PR recommendations."""

import logging
from typing import Any

from fastmcp import Context, FastMCP
from pydantic import Field

from mcp_pr_recommender.config import settings
from mcp_pr_recommender.tools import FeasibilityAnalyzerTool, PRRecommenderTool, StrategyManagerTool, ValidatorTool


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def create_server() -> FastMCP:
    """Create and configure the FastMCP server."""

    mcp = FastMCP(
        name="PR Recommender",
        instructions="""
        Intelligent PR boundary detection and recommendation system.

        This server analyzes git changes and generates atomic, logically-grouped
        PR recommendations optimized for code review efficiency and deployment safety.

        Available tools:
        - generate_pr_recommendations: Main tool to generate PR recommendations from git analysis
        - analyze_pr_feasibility: Analyze feasibility and risks of specific recommendations
        - get_strategy_options: Get available grouping strategies and settings
        - validate_pr_recommendations: Validate generated recommendations for quality

        Input: Expects git analysis data from mcp_local_repo_analyzer
        Output: Structured PR recommendations with titles, descriptions, and rationale
        """,
    )

    # Initialize tools
    mcp.pr_generator = PRRecommenderTool()
    mcp.feasibility_analyzer = FeasibilityAnalyzerTool()
    mcp.strategy_manager = StrategyManagerTool()
    mcp.validator = ValidatorTool()

    @mcp.tool()
    async def generate_pr_recommendations(
        ctx: Context,
        analysis_data: dict[str, Any] = Field(..., description="Git analysis data from mcp_local_repo_analyzer"),
        strategy: str = Field(default="semantic", description="Grouping strategy to use"),
        max_files_per_pr: int = Field(default=8, description="Maximum files per PR"),
    ) -> dict[str, Any]:
        """Generate PR recommendations from git analysis data."""
        await ctx.info(f"Generating PR recommendations using {strategy} strategy")
        return await mcp.pr_generator.generate_recommendations(analysis_data, strategy, max_files_per_pr)

    @mcp.tool()
    async def analyze_pr_feasibility(
        ctx: Context,
        pr_recommendation: dict[str, Any] = Field(..., description="PR recommendation to analyze"),
    ) -> dict[str, Any]:
        """Analyze the feasibility and risks of a specific PR recommendation."""
        await ctx.info("Analyzing PR feasibility")
        return await mcp.feasibility_analyzer.analyze_feasibility(pr_recommendation)

    @mcp.tool()
    async def get_strategy_options(
        ctx: Context,
    ) -> dict[str, Any]:
        """Get available PR grouping strategies and their descriptions."""
        await ctx.info("Retrieving available strategies")
        return await mcp.strategy_manager.get_strategies()

    @mcp.tool()
    async def validate_pr_recommendations(
        ctx: Context,
        recommendations: list[dict[str, Any]] = Field(..., description="List of PR recommendations to validate"),
    ) -> dict[str, Any]:
        """Validate a set of PR recommendations for completeness and atomicity."""
        await ctx.info(f"Validating {len(recommendations)} PR recommendations")
        return await mcp.validator.validate_recommendations(recommendations)

    return mcp


def main():
    """Main entry point."""
    setup_logging()

    try:
        mcp = create_server()

        logging.info(f"Starting PR Recommender server on {settings.server_host}:{settings.server_port}")
        mcp.run()

    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")


if __name__ == "__main__":
    main()
