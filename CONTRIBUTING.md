# Contributing to JobSync

Thank you for your interest in contributing to JobSync! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

### Suggesting Features

We love new ideas! Open an issue with:
- A clear description of the feature
- Why it would be useful
- Any implementation ideas you have

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test your changes**: Ensure all tests pass
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to your fork**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Write tests for new features

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/jobsync.git
cd jobsync

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate    # Linux/Mac

# Install dependencies
pip install -r backend/requirements-dev.txt

# Run tests
pytest

# Format code
black backend/

# Lint code
flake8 backend/
```

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove, etc.)
- Keep the first line under 50 characters
- Add details in the body if needed

Examples:
- `Add resume parsing feature`
- `Fix job search API timeout issue`
- `Update documentation for cover letter generation`

### Testing

- Write tests for new features
- Ensure existing tests pass
- Aim for good test coverage

### Documentation

- Update README.md if you change functionality
- Add docstrings to new functions
- Update API documentation if you add/change endpoints

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help others learn and grow

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.

Thank you for contributing to JobSync!
