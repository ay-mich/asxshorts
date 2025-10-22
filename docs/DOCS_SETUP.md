# Documentation Setup

This project uses automatic documentation generation with `pdoc` and GitHub Pages.

## How it works

1. **Automatic Generation**: Documentation is automatically generated from docstrings in your Python code
2. **GitHub Pages**: Deployed automatically when you push to the `main` branch
3. **Zero Configuration**: No manual setup required - just push your code

## Local Development

To generate and preview documentation locally:

```bash
# Install pdoc
pip install pdoc

# Generate documentation
pdoc asxshorts -o docs

# Preview locally
cd docs && python -m http.server 8000
```

Then open http://localhost:8000 in your browser.

## GitHub Pages Setup

1. Go to your repository settings
2. Navigate to "Pages" section
3. Set source to "GitHub Actions"
4. The workflow will automatically deploy docs on every push to main

## Documentation URL

Once set up, your documentation will be available at:
`https://ay-mich.github.io/asxshorts/asxshorts.html`

## Adding Documentation

Simply add docstrings to your Python classes and functions:

```python
def my_function(param: str) -> str:
    """
    Brief description of the function.

    Args:
        param: Description of the parameter

    Returns:
        Description of the return value

    Example:
        >>> result = my_function("test")
        >>> print(result)
    """
    return param
```

The documentation will automatically update when you push changes.
