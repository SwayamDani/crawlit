#!/usr/bin/env python3
"""
Minimal setup.py for backwards compatibility.
Configuration is now in pyproject.toml.
"""

from setuptools import setup
import os

# Read the long description from README.md
current_dir = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(current_dir, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    python_requires=">=3.8",
    long_description=long_description,
    long_description_content_type='text/markdown',
    entry_points={
        'console_scripts': [
            'crawlit=crawlit.crawlit:main',
        ],
    },
    include_package_data=True,  # Tells setuptools to include files from MANIFEST.in
)