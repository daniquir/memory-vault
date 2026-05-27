# Contributing to The Memory Vault

Thank you for your interest in contributing to The Memory Vault! This document provides guidelines and information for contributors.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- A descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:

- Use a clear and descriptive title
- Provide a detailed description of the enhancement
- Explain why this enhancement would be useful
- Provide examples of how the enhancement would be used

### Pull Requests

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write tests for your changes (if applicable)
5. Ensure all tests pass
6. Commit your changes with a clear message
7. Push to your branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Daniquir/memory-vault.git
cd memory-vault

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest tests/
```

## Coding Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Add comments for complex logic

## Project Structure

```
memory-vault/
├── src/
│   ├── cli/          # Command-line interface
│   ├── core/         # Core logic (rclone, restic, mount management)
│   ├── gui/          # Graphical interface
│   └── utils/        # Utilities (config, i18n, shield)
├── tests/            # Test files
├── docs/             # Documentation
└── scripts/          # Installation/uninstallation scripts
```

## Testing

- Write tests for new features
- Ensure existing tests pass before submitting
- Test on multiple Python versions when possible (3.7+)

## Documentation

- Update README.md if you change user-facing functionality
- Add docstrings to new functions
- Update relevant documentation files in docs/

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue for any questions about contributing.
