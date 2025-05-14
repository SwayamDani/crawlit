# crawlit Documentation

This directory contains the API documentation for the `crawlit` package.

## Building the Documentation

To build the documentation:

1. Install the required packages:
   ```
   pip install sphinx sphinx_rtd_theme sphinxcontrib-napoleon
   ```

2. Build the HTML documentation:
   ```
   cd docs
   make html  # On Windows: make.bat html
   ```

3. The documentation will be available in the `_build/html` directory. Open `_build/html/index.html` in your browser to view it.

## Documentation Structure

- `index.rst`: The main documentation homepage
- `api/`: API reference documentation
  - `index.rst`: API documentation overview
  - `crawler.rst`: Crawler module documentation
  - `output.rst`: Output module documentation
  - `cli.rst`: Command line interface documentation
- `installation.rst`: Installation instructions
- `quickstart.rst`: Getting started guide
- `usage.rst`: Detailed usage examples
- `examples.rst`: Example code
- `contributing.rst`: Contribution guidelines
- `changelog.rst`: Version history

## Updating Documentation

When adding new features or changing existing ones, please update the corresponding documentation:

1. Update docstrings in the Python code using Google style format
2. Update the relevant RST files if necessary
3. Rebuild the documentation to ensure it renders correctly
