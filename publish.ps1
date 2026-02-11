# PowerShell script to publish crawlit 0.2.0 to PyPI

Write-Host "Step 1: Cleaning up old distribution files..." -ForegroundColor Green
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist/, build/, *.egg-info/

Write-Host "Step 2: Building distribution packages..." -ForegroundColor Green
python -m build

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Step 3: Checking the packages for issues..." -ForegroundColor Green
python -m twine check dist/*

if ($LASTEXITCODE -ne 0) {
    Write-Host "Package check failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Step 4: Upload to Test PyPI..." -ForegroundColor Yellow
Write-Host "Note: You will need to enter your Test PyPI credentials" -ForegroundColor Yellow
python -m twine upload --repository testpypi dist/*

if ($LASTEXITCODE -ne 0) {
    Write-Host "Test PyPI upload failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Step 5: Test installing from Test PyPI..." -ForegroundColor Green
Write-Host "You can test install with: pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ crawlit" -ForegroundColor Yellow

$response = Read-Host "Did the Test PyPI upload succeed? Continue to PyPI? (y/n)"
if ($response -ne "y") {
    Write-Host "Publishing cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host "Step 6: Upload to PyPI..." -ForegroundColor Green
Write-Host "Note: You will need to enter your PyPI credentials" -ForegroundColor Yellow
python -m twine upload dist/*

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyPI upload failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Successfully published crawlit 0.2.0 to PyPI!" -ForegroundColor Green

