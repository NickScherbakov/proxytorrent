# Contributing to ProxyTorrent

Thank you for considering contributing to ProxyTorrent! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and Clone**
```bash
git clone https://github.com/yourusername/proxytorrent.git
cd proxytorrent
```

2. **Set Up Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. **Install libtorrent**
For development, you'll need libtorrent installed:
```bash
# Ubuntu/Debian
sudo apt-get install python3-libtorrent

# macOS (via Homebrew)
brew install libtorrent-rasterbar
```

## Running the Service

### Local Development
```bash
# Using the run script
./run.py

# Or directly with uvicorn
cd src
uvicorn app.main:app --reload --port 8000
```

### Docker
```bash
docker-compose up --build
```

## Testing

### Run All Tests
```bash
pytest src/app/tests/ -v
```

### Run Unit Tests Only (Skip Integration)
```bash
pytest src/app/tests/ -v -m "not integration"
```

### Run with Coverage
```bash
pytest src/app/tests/ -v --cov=app --cov-report=html
```

### Run Specific Test
```bash
pytest src/app/tests/test_api.py::test_root_endpoint -v
```

## Code Quality

### Linting
```bash
# Run ruff
ruff check src/

# Auto-fix issues
ruff check src/ --fix
```

### Type Checking
```bash
mypy src/
```

### Formatting
```bash
# Format with black
black src/

# Sort imports
isort src/
```

### Run All Checks
```bash
ruff check src/ --fix && black src/ && isort src/ && mypy src/
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Maximum line length: 100 characters
- Use modern Python 3.11+ features (e.g., `str | None` instead of `Optional[str]`)

## Commit Messages

Use clear, descriptive commit messages:
```
feat: Add support for custom tracker URLs
fix: Handle timeout errors in fetcher
docs: Update API examples in README
test: Add integration test for E2E flow
refactor: Simplify rate limiting logic
```

Prefixes:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build/tooling changes

## Pull Request Process

1. **Create a Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make Your Changes**
   - Write code
   - Add tests
   - Update documentation

3. **Ensure Quality**
```bash
# Run tests
pytest src/app/tests/ -v

# Run linting
ruff check src/ --fix
mypy src/
```

4. **Commit Your Changes**
```bash
git add .
git commit -m "feat: your feature description"
```

5. **Push and Create PR**
```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## PR Requirements

Before submitting a PR, ensure:

- [ ] All tests pass
- [ ] Code is linted (ruff, mypy)
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No security vulnerabilities introduced

## Adding New Features

### API Endpoints
1. Add endpoint in `src/app/api/`
2. Add schema models in `src/app/models/schemas.py`
3. Add tests in `src/app/tests/`
4. Update API documentation in README

### Services
1. Add service in `src/app/services/`
2. Add error classes if needed
3. Add unit tests
4. Document public methods

### Configuration
1. Add settings in `src/app/core/config.py`
2. Update `.env.example`
3. Document in README

## Reporting Issues

When reporting issues, include:

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Relevant logs or error messages

## Security Issues

**Do not** report security issues publicly. Instead:
1. Email the maintainers directly
2. Provide details of the vulnerability
3. Allow time for a fix before disclosure

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the project's guidelines

## Questions?

- Check existing issues and discussions
- Read the documentation
- Ask in GitHub Discussions
- Join our community chat (if available)

Thank you for contributing to ProxyTorrent! 🎉
