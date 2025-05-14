#!/usr/bin/env bash
# This script shows the steps to publish crawlit to PyPI

# Step 1: Clean up old distribution files
echo "Step 1: Cleaning up old distribution files..."
rm -rf dist/ build/ *.egg-info/

# Step 2: Build the distribution packages
echo "Step 2: Building distribution packages..."
python3 -m build

# Step 3: Check the packages for issues
echo "Step 3: Checking the packages for issues..."
python3 -m twine check dist/*

# Step 4: Upload to Test PyPI first
echo "Step 4: Upload to Test PyPI..."
python3 -m twine upload --repository testpypi dist/*

# Step 5: Test the package from Test PyPI
echo "Step 5: Test installing from Test PyPI..."
pip3 install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ crawlit

# Step 6: Upload to real PyPI
echo "Step 6: Upload to PyPI..."
python3 -m twine upload dist/*

echo ""
echo "==============================================" 
echo "To actually publish to PyPI, you will need to:"
echo "1. Create an account on https://pypi.org/"
echo "2. Uncomment the upload commands in this script"
echo "3. Run this script and enter your credentials when prompted"
echo "==============================================" 
echo ""
echo "Alternatively, you can set up API tokens:"
echo "1. Create a token on PyPI: https://pypi.org/manage/account/token/"
echo "2. Save it to your ~/.pypirc file or use environment variables"
echo ""
