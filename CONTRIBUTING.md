# Contributing to MCP PR Recommender

Thank you for your interest in contributing to MCP PR Recommender! This guide outlines the development workflow and standards for this project.

## Development Environment Setup

### Prerequisites
- Python 3.10 or higher
- Poetry for dependency management
- Git for version control
- Pre-commit for code quality checks
- **OpenAI API Key** for LLM functionality

### Initial Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/manavgup/mcp_pr_recommender.git
   cd mcp_pr_recommender
   ```

2. **Install dependencies:**
   ```bash
   poetry install --with test,dev
   ```

3. **Set up environment variables:**
   ```bash
   export OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **Install pre-commit hooks:**
   ```bash
   poetry run pre-commit install
   ```

5. **Verify installation:**
   ```bash
   poetry run pytest tests/ -v
   ```

## Code Standards

### Code Style
This project uses automated code formatting and linting:

- **Black**: Code formatting with 88-character line length
- **Ruff**: Fast Python linter for code quality
- **mypy**: Static type checking
- **pre-commit**: Automated checks before commits

### Running Code Quality Checks
```bash
# Run all pre-commit checks
poetry run pre-commit run --all-files

# Individual tools
poetry run black src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/
```

### Type Annotations
- All functions must include type annotations for parameters and return values
- Use modern union syntax (`X | Y` instead of `Union[X, Y]`)
- Import types from `typing` when needed

### Documentation Standards
- All public functions and classes must have docstrings
- Use Google-style docstrings
- Include type information in docstrings where helpful
- Update README.md for significant feature changes

## Testing Requirements

### Test Structure
- Tests are located in the `tests/` directory
- Use pytest for all testing
- Organize tests to mirror the `src/` directory structure
- Use descriptive test function names

### Test Types
- **Unit tests**: Fast, isolated tests (marked with `@pytest.mark.unit`)
- **Integration tests**: Cross-component tests (marked with `@pytest.mark.integration`)
- **Slow tests**: Tests taking >5 seconds (marked with `@pytest.mark.slow`)
- **External tests**: Tests requiring OpenAI API (marked with `@pytest.mark.external`)

### Running Tests
```bash
# Run all tests (excluding external by default)
poetry run pytest tests/

# Run specific test types
poetry run pytest -m "unit and not slow"
poetry run pytest -m integration

# Run tests requiring OpenAI API
poetry run pytest -m external

# Run with coverage
poetry run pytest --cov=src --cov-report=html
```

### Test Coverage
- Maintain minimum 80% test coverage
- All new features must include comprehensive tests
- Mock OpenAI API calls in unit tests
- Use real API calls sparingly in integration tests

## Development Workflow

### Branch Strategy
1. Create feature branches from `main`: `git checkout -b feature/your-feature-name`
2. Make commits with descriptive messages
3. Push branch and create pull request
4. Address review feedback
5. Merge after approval

### Commit Message Format
```
type(scope): short description

Longer description if needed explaining the changes
and their rationale.

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

### Pull Request Process
1. **Before creating PR:**
   - Ensure all tests pass locally
   - Run pre-commit checks
   - Update documentation if needed
   - Add changelog entry if applicable

2. **PR Requirements:**
   - Clear title and description
   - Link to related issues
   - Include testing instructions
   - Request appropriate reviewers

3. **Review Process:**
   - Address all reviewer feedback
   - Ensure CI checks pass
   - Squash commits if requested
   - Await approval before merging

## Project-Specific Guidelines

### MCP PR Recommender Architecture
This service generates intelligent PR grouping recommendations using LLM analysis:

- **Core Engine**: SemanticAnalyzer using OpenAI GPT-4 for code relationship understanding
- **MCP Tools**: PR generation, feasibility analysis, strategy management, validation
- **Configuration**: Requires OPENAI_API_KEY environment variable
- **Default Port**: 9071 (HTTP mode)

### Key Components
- **SemanticAnalyzer**: LLM-powered code analysis and relationship detection
- **PRGenerator**: Creates intelligent PR groupings with dependency ordering
- **FeasibilityAnalyzer**: Assesses PR conflicts and implementation risks
- **StrategyManager**: Manages different grouping strategies (semantic, size-based, etc.)

### Running the Service
```bash
# Development mode (stdio)
export OPENAI_API_KEY=your_key_here
poetry run python -m mcp_pr_recommender.main --transport stdio

# HTTP server mode
poetry run python -m mcp_pr_recommender.main --transport http --port 9071

# Using make commands from workspace root
make serve-recommender
```

### Available MCP Tools
- `generate_pr_recommendations`: Generate intelligent PR groupings with dependency ordering
- `analyze_pr_feasibility`: Analyze PR feasibility and potential conflicts
- `get_strategy_options`: Available grouping strategies (semantic, size-based, etc.)
- `validate_pr_recommendations`: Validate and refine recommendations

### Working with OpenAI API
- **Rate Limiting**: Implement exponential backoff for API calls
- **Error Handling**: Gracefully handle API failures and network issues
- **Cost Management**: Monitor token usage and optimize prompt efficiency
- **Testing**: Mock API responses for deterministic testing

### LLM Best Practices
- **Prompt Engineering**: Use clear, structured prompts for consistent results
- **Context Management**: Optimize context window usage for large codebases
- **Response Validation**: Validate LLM responses before processing
- **Fallback Strategies**: Implement rule-based fallbacks when LLM fails

## Issue Reporting

### Bug Reports
When reporting bugs, please include:
- Python version and operating system
- OpenAI API key status (without revealing the key)
- Complete error messages and stack traces
- Input data that caused the issue
- Expected vs. actual behavior

### Feature Requests
For new features, please provide:
- Clear use case and motivation
- Detailed description of proposed functionality
- Consider impact on LLM token usage and costs
- Suggest implementation approach if possible

## Getting Help

- **Documentation**: Check the README.md and inline documentation
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Code Review**: Don't hesitate to ask for clarification during reviews

## Recognition

Contributors are recognized in:
- Git commit history
- Release notes for significant contributions
- Contributors section in README.md

Thank you for contributing to MCP PR Recommender!
