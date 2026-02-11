echo "Step 1: Cleaning up old distribution files..."
rm -rf dist/ build/ *.egg-info/

echo "Step 2: Building distribution packages..."
python3 -m build

echo "Step 3: Checking the packages for issues..."
python3 -m twine check dist/*

echo "Step 4: Upload to Test PyPI..."
python3 -m twine upload --repository testpypi dist/*

echo "Step 5: Test installing from Test PyPI..."
pip3 install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ crawlit

echo "Step 6: Upload to PyPI..."
python3 -m twine upload dist/*
