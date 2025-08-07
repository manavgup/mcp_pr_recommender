# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup
- AI-powered MCP server for generating intelligent PR grouping recommendations
- Semantic analysis using OpenAI GPT-4 for code relationship understanding
- Multiple PR recommendation strategies (semantic, directory-based, size-based)
- Feasibility analysis for PR recommendations and conflict detection
- Strategy management for different grouping approaches
- Validation and refinement of PR recommendations
- Multiple transport support (stdio, HTTP, WebSocket, SSE)
- CLI interface with environment variable validation
- Integration with mcp_shared_lib for common functionality

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.1.0] - 2025-08-07

### Added
- Initial release of MCP PR Recommender
- MCP Server for recommending PR structures and groupings
- AI-powered semantic analysis for intelligent code change grouping
- MCP tools for PR generation, feasibility analysis, and validation
- Services for grouping engine, semantic analyzer, and atomicity validator
- CLI with OpenAI API key validation and configuration options
- Integration with OpenAI GPT-4 for advanced code understanding
- Comprehensive test suite with unit and integration tests
- Documentation and setup instructions
