# Mixtura Test Suite

This directory contains comprehensive tests for all Mixtura functionality.

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=mixtura --cov-report=html
```

## Test Structure

- `test_cli.py` - Tests for CLI commands
- `test_orchestrator.py` - Tests for service layer logic
- `test_providers.py` - Tests for provider implementations
- `test_ui.py` - Tests for UI components
- `conftest.py` - Shared fixtures
