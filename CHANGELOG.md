# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-08-07

### Added
- Initial release of MCP PR Recommender
- AI-powered MCP server for intelligent PR grouping recommendations
- Semantic analysis using OpenAI GPT-4 for code relationship understanding
- Multiple PR recommendation strategies (semantic, directory-based, size-based)
- Feasibility analysis for PR recommendations and conflict detection
- Strategy management for different grouping approaches
- Validation and refinement of PR recommendations
- Multiple transport support (stdio, HTTP, WebSocket, SSE)
- CLI interface with environment variable validation
- Bundled mcp_shared_lib for seamless installation
- Self-contained package requiring no external dependencies
- Services for grouping engine, semantic analyzer, and atomicity validator
- Integration with OpenAI GPT-4 for advanced code understanding
- Comprehensive test suite with unit and integration tests
- Production-ready PyPI package configuration
