#!/bin/bash
# Development setup script for MCP PR Recommender
# This script sets up the development environment and validates the installation

set -e

PROJECT_NAME="MCP PR Recommender"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 Setting up development environment for $PROJECT_NAME"
echo "📁 Project directory: $PROJECT_DIR"

cd "$PROJECT_DIR"

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry first: https://python-poetry.org/docs/#installation"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Please install Git first"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "🐍 Found Python $PYTHON_VERSION"

# Check OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY environment variable not set"
    echo "   Some functionality will be limited without API access"
    echo "   Set your API key: export OPENAI_API_KEY=your_key_here"
else
    echo "🔑 OpenAI API key configured"
fi

# Install dependencies
echo "📦 Installing dependencies..."
poetry install --with test,dev

# Install pre-commit hooks
echo "🔒 Setting up pre-commit hooks..."
poetry run pre-commit install

# Run initial validation
echo "🧪 Running initial validation..."

# Check code style
echo "  - Running code style checks..."
poetry run black --check src/ tests/ || {
    echo "⚠️  Code style issues found. Running black to fix..."
    poetry run black src/ tests/
}

# Check linting
echo "  - Running linter..."
poetry run ruff check src/ tests/

# Check type annotations
echo "  - Running type checker..."
poetry run mypy src/

# Run fast tests (excluding external API tests)
echo "  - Running unit tests..."
poetry run pytest tests/ -m "unit and not slow and not external" -v

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "📚 Common development commands:"
echo "  poetry run pytest tests/                              # Run all tests (excluding external)"
echo "  poetry run pytest -m 'unit and not slow'             # Run fast unit tests"
echo "  poetry run pytest -m external                        # Run tests requiring OpenAI API"
echo "  poetry run pre-commit run --all-files                # Run all code quality checks"
echo "  poetry run python -m mcp_pr_recommender.main         # Start MCP server (stdio)"
echo "  poetry run python -m mcp_pr_recommender.main --transport http --port 9071  # HTTP server"
echo ""
echo "🔑 For full functionality, ensure OPENAI_API_KEY is set"
echo "🎯 Ready for development! Check CONTRIBUTING.md for detailed guidelines."
