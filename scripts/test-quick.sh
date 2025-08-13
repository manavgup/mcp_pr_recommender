#!/bin/bash
# Quick test script for MCP PR Recommender
# Runs fast tests for development cycle (excluding external API calls)

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "⚡ Running quick tests for MCP PR Recommender..."

# Run pre-commit checks
echo "🔒 Running pre-commit checks..."
poetry run pre-commit run --all-files

# Run fast unit tests (excluding external API tests)
echo "🧪 Running fast unit tests..."
poetry run pytest tests/ -m "unit and not slow and not external" -v --tb=short

# Check test coverage for core modules
echo "📊 Checking test coverage..."
poetry run pytest tests/ -m "unit and not slow and not external" --cov=src/mcp_pr_recommender --cov-report=term-missing --cov-fail-under=70

echo ""
echo "✅ Quick tests passed! Ready for development."
echo ""
echo "💡 To run full test suite: poetry run pytest tests/"
echo "💡 To run external API tests: poetry run pytest tests/ -m external"
echo "💡 To run integration tests: poetry run pytest tests/ -m integration"
echo ""
echo "🔑 Note: External tests require OPENAI_API_KEY to be set"
