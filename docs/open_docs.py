#!/usr/bin/env python3
"""
Helper script to open the documentation in the default web browser
"""

import os
import sys
import webbrowser
from pathlib import Path

def main():
    """Open the documentation in the default web browser"""
    # Get the docs directory
    docs_dir = Path(__file__).parent
    
    # Check if the documentation has been built
    html_index = docs_dir / '_build' / 'html' / 'index.html'
    
    if not html_index.exists():
        print("Documentation hasn't been built yet. Building now...")
        
        # Try to build the documentation
        try:
            if sys.platform.startswith('win'):
                os.system(f'cd {docs_dir} && make.bat html')
            else:
                os.system(f'cd {docs_dir} && make html')
        except Exception as e:
            print(f"Error building documentation: {e}")
            print("\nPlease build the documentation manually:")
            print("  cd docs")
            print("  make html  # On Windows: make.bat html")
            return 1
    
    # Open the documentation in the default browser
    url = html_index.as_uri()
    print(f"Opening documentation: {url}")
    webbrowser.open(url)
    return 0

if __name__ == "__main__":
    sys.exit(main())
