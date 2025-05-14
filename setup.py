#!/usr/bin/env python3
"""
Setup file for the crawlit package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="crawlit",
    version="0.1.0",
    author="Swayam Dani",
    author_email="swayamdani@swayamdani.com",  
    description="Modular, Ethical Python Web Crawler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SwayamDani/crawlit",  
    project_urls={
        "Bug Tracker": "https://github.com/SwayamDani/crawlit/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
        "lxml>=4.6.0",
    ],
    extras_require={
        'cli': [],  # No extra dependencies needed for CLI, but keeps it optional
    },
    entry_points={
        "console_scripts": [
            "crawlit=crawlit:cli_main [cli]",  # Only installed when the 'cli' extra is requested
        ],
    },
)