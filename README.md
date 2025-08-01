# MCP PR Recommender

## Overview
The MCP PR Recommender is an intelligent PR boundary detection and recommendation system designed to analyze git changes and generate atomic, logically-grouped pull request (PR) recommendations. It aims to optimize code review efficiency and deployment safety by providing structured PR suggestions with titles, descriptions, and rationale.

## Features
- Generate PR recommendations from git analysis data.
- Analyze feasibility and risks of specific PR recommendations.
- Retrieve available PR grouping strategies and settings.
- Validate generated PR recommendations for quality, completeness, and atomicity.
- Supports both STDIO and HTTP transport protocols for flexible integration.

## Usage
The server can be run in different modes:
- **STDIO mode**: For direct MCP client connections.
- **HTTP mode**: For integration with MCP Gateway or other HTTP clients.

### Running the server
```bash
# Run in STDIO mode (default)
python -m mcp_pr_recommender.main --transport stdio

# Run in HTTP mode
python -m mcp_pr_recommender.main --transport streamable-http --host 127.0.0.1 --port 9071
```

## Input and Output
- **Input**: Expects git analysis data from the `mcp_local_repo_analyzer` project.
- **Output**: Structured PR recommendations including grouping, titles, descriptions, and rationale.

## Tools Provided
- `generate_pr_recommendations`: Generate PR recommendations from git analysis.
- `analyze_pr_feasibility`: Analyze feasibility and risks of PR recommendations.
- `get_strategy_options`: Get available grouping strategies.
- `validate_pr_recommendations`: Validate PR recommendations for quality.

## License
Apache-2.0 License

## Author
Manav Gupta &lt;manavg@gmail.com&gt;
