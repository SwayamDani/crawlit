# Crawlit Test Suite

Comprehensive test suite with 500+ tests covering unit, integration, performance, and edge cases.

## Quick Start

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage (requires pytest-cov)
pip install pytest-cov
pytest --cov=crawlit --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
start htmlcov\index.html  # Windows
```

## Test Organization

```
tests/
├── test_budget_tracker.py          # Budget tracking tests
├── test_priority_queue.py          # URL prioritization tests
├── test_cookie_persistence.py      # Cookie management tests
├── test_captcha_detector.py        # CAPTCHA detection tests
├── test_pdf_extractor.py           # PDF extraction tests
├── test_download_manager.py        # Download manager tests
├── test_incremental_crawling.py    # Incremental crawl tests
├── test_scheduler.py               # Crawl scheduler tests
├── integration/
│   ├── test_end_to_end.py         # End-to-end workflows
│   ├── test_javascript_rendering.py # JS rendering tests
│   └── test_distributed_crawling.py # Distributed system tests
└── performance/
    └── test_benchmarks.py          # Performance benchmarks
```

## Running Specific Tests

### By Category

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# Performance tests
pytest -m performance

# Exclude slow tests
pytest -m "not slow"
```

### By Feature

```bash
# Budget tracker
pytest -m budget_tracker

# Priority queue
pytest -m priority_queue

# Cookie persistence
pytest -m cookie_persistence

# CAPTCHA detection
pytest -m captcha_detection
```

### By File

```bash
# Single file
pytest tests/test_budget_tracker.py

# Specific test
pytest tests/test_budget_tracker.py::TestBudgetTracker::test_page_limit
```

## Optional Dependencies

Some tests require optional dependencies:

```bash
# For JavaScript rendering tests
pip install -e ".[playwright]"
playwright install chromium

# For PDF extraction tests
pip install -e ".[pdf]"

# For distributed crawling tests
pip install -e ".[distributed]"

# Install all optional dependencies
pip install -e ".[all]"
```

## Test Markers

- `unit` - Fast unit tests (no external dependencies)
- `integration` - Integration tests (may require services)
- `performance` - Performance and benchmark tests
- `slow` - Slow-running tests
- `playwright` - Requires Playwright browser
- `distributed` - Requires RabbitMQ or Kafka
- `database` - Requires database connection
- `asyncio` - Asynchronous tests

## Coverage Reports

```bash
# HTML report (interactive)
pytest --cov=crawlit --cov-report=html

# Terminal report
pytest --cov=crawlit --cov-report=term-missing

# XML report (for CI)
pytest --cov=crawlit --cov-report=xml

# Multiple formats
pytest --cov=crawlit --cov-report=html --cov-report=term
```

## Parallel Execution

```bash
# Install parallel plugin
pip install pytest-xdist

# Run in parallel (auto-detect CPUs)
pytest -n auto

# Specify worker count
pytest -n 4
```

## Debugging

```bash
# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s

# Very verbose output
pytest -vv

# Show local variables in tracebacks
pytest -l
```

## Common Issues

### ImportError

```bash
# Make sure package is installed
pip install -e .
```

### Playwright tests skipped

```bash
# Install Playwright browsers
playwright install
```

### RabbitMQ/Kafka tests skipped

```bash
# Start RabbitMQ
docker run -d -p 5672:5672 rabbitmq

# Or install locally
sudo apt-get install rabbitmq-server
```

### PDF tests failing

```bash
# Install PDF dependencies
pip install pypdf reportlab
```

## CI/CD

Tests are automatically run on:
- Pull requests
- Pushes to main
- Scheduled nightly builds

**Test Matrix:**
- Python: 3.8, 3.9, 3.10, 3.11, 3.12
- OS: Ubuntu, Windows, macOS

## Documentation

For detailed information, see:
- [TESTING.md](../TESTING.md) - Complete testing guide
- [TEST_COVERAGE_SUMMARY.md](../TEST_COVERAGE_SUMMARY.md) - Coverage summary
- [pytest.ini](../pytest.ini) - Test configuration

## Contributing

When adding tests:

1. Follow naming convention: `test_*.py`
2. Use descriptive test names
3. Add appropriate markers
4. Maintain >80% coverage
5. Include edge cases
6. Document complex tests

## Questions?

- Open an issue on GitHub
- Check [TESTING.md](../TESTING.md) for details
- Review existing tests for examples

