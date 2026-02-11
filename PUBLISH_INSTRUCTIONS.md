# Publishing crawlit 0.2.0 to PyPI

## Pre-Publication Checklist

✅ Version updated to 0.2.0 in:
- `crawlit/__init__.py`
- `pyproject.toml`
- `RELEASE_NOTES.md`

✅ Documentation updated:
- README.md includes all new features
- RELEASE_NOTES.md comprehensive
- All examples and usage documented

✅ Packages built:
- `crawlit-0.2.0-py3-none-any.whl` (84.97 KB)
- `crawlit-0.2.0.tar.gz` (138.82 KB)

## Publishing Steps

### Option 1: Upload to Test PyPI First (Recommended)

1. **Upload to Test PyPI:**
   ```powershell
   python -m twine upload --repository testpypi dist/*
   ```
   - You'll be prompted for your Test PyPI credentials
   - Test PyPI username/password (different from PyPI)

2. **Test Installation:**
   ```powershell
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ crawlit
   ```

3. **Verify Installation:**
   ```powershell
   python -c "import crawlit; print(crawlit.__version__)"
   # Should output: 0.2.0
   ```

4. **If test successful, upload to PyPI:**
   ```powershell
   python -m twine upload dist/*
   ```
   - You'll be prompted for your PyPI credentials
   - Use your PyPI username and password (or API token)

### Option 2: Direct Upload to PyPI

If you're confident and want to skip Test PyPI:

```powershell
python -m twine upload dist/*
```

## Note on Twine Check Warning

The `twine check` command may show a warning about `license-file` field. This is a known compatibility issue between setuptools and twine, but **it does not prevent upload to PyPI**. PyPI accepts packages with this field, so you can proceed with the upload.

## After Publishing

1. **Verify on PyPI:**
   - Visit: https://pypi.org/project/crawlit/
   - Check that version 0.2.0 is listed
   - Verify all metadata is correct

2. **Test Installation:**
   ```powershell
   pip install --upgrade crawlit
   python -c "import crawlit; print(crawlit.__version__)"
   ```

3. **Create GitHub Release (Optional):**
   - Tag the release: `git tag -a v0.2.0 -m "Release version 0.2.0"`
   - Push tag: `git push origin v0.2.0`
   - Create release on GitHub with release notes from RELEASE_NOTES.md

## Troubleshooting

- **Authentication Issues**: Use API tokens instead of passwords for better security
  - Generate token at: https://pypi.org/manage/account/token/
  - Use `__token__` as username and the token as password

- **Version Already Exists**: If 0.2.0 already exists on PyPI, you'll need to bump to 0.2.1

- **Upload Errors**: Check your internet connection and PyPI status

