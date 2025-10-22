# Contributing to asxshorts

Thank you for your interest in contributing to asxshorts! This guide will help you get started.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git

### Development Setup

1. **Fork and Clone**

   ```bash
   git clone https://github.com/YOUR_USERNAME/asxshorts.git
   cd asxshorts
   ```

2. **Create Development Environment**

   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install in development mode
   pip install -e ".[dev]"
   ```

3. **Verify Setup**
   ```bash
   # Run tests
   pytest
   ```

## How to Contribute

### Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Include Python version, OS, and steps to reproduce
- Provide minimal code examples when possible

### Making Changes

1. **Create a branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**

   - Write tests for new functionality
   - Follow existing code style
   - Add type hints where appropriate

3. **Test your changes**

   ```bash
   pytest
   ```

4. **Submit a Pull Request**
   - Describe what your changes do
   - Reference any related issues
   - Ensure tests pass

## Code Style

- Follow PEP 8
- Use type hints for function signatures
- Write docstrings for public functions
- Keep line length under 88 characters

## Testing

Run the test suite with:

```bash
pytest
```

Add tests for any new functionality in the `tests/` directory.

## Questions?

Feel free to open an issue for any questions about contributing!
