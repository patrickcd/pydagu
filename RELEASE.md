# Release Checklist for pydagu

## Pre-release

- [ ] Update version in `pyproject.toml`
- [ ] Update your name/email in `pyproject.toml` authors
- [ ] Update GitHub URLs in `pyproject.toml` and `README.md`
- [ ] Update copyright year in `LICENSE`
- [ ] Run all tests locally: `pytest tests/ -v`
- [ ] Check test coverage: `pytest tests/ --cov=pydagu --cov-report=html`
- [ ] Update CHANGELOG.md with release notes
- [ ] Review and update README.md examples

## GitHub Setup

1. **Create GitHub repository** (if not already done)
   ```bash
   gh repo create yourusername/pydagu --public
   git remote add origin https://github.com/yourusername/pydagu.git
   git push -u origin main
   ```

2. **Set up PyPI trusted publishing** (recommended over API tokens)
   - Go to https://pypi.org/manage/account/publishing/
   - Add a new pending publisher:
     - PyPI Project Name: `pydagu`
     - Owner: `yourusername`
     - Repository name: `pydagu`
     - Workflow name: `publish.yml`
     - Environment name: (leave empty)

3. **Enable GitHub Actions**
   - Push code to GitHub
   - Check Actions tab to ensure workflows are enabled

## Testing GitHub Actions

1. **Test the test workflow**
   ```bash
   git commit --allow-empty -m "Test GitHub Actions"
   git push
   ```
   - Go to Actions tab and verify tests run successfully
   - Check all Python versions (3.11, 3.12, 3.13)

## Release Process

1. **Create a git tag**
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

2. **Create GitHub Release**
   - Go to https://github.com/yourusername/pydagu/releases/new
   - Select the tag `v0.1.0`
   - Title: `v0.1.0`
   - Description: Copy from CHANGELOG.md
   - Click "Publish release"

3. **Verify PyPI publication**
   - The publish workflow should trigger automatically
   - Check https://pypi.org/project/pydagu/
   - Verify package can be installed:
     ```bash
     pip install pydagu
     ```

## Post-release

- [ ] Test installation in a fresh environment: `pip install pydagu`
- [ ] Update version to next development version (e.g., `0.2.0-dev`)
- [ ] Announce on relevant channels (Twitter, Reddit, etc.)
- [ ] Update documentation site (if applicable)

## Manual PyPI Upload (Alternative)

If you prefer using API tokens instead of trusted publishing:

1. Create a PyPI API token at https://pypi.org/manage/account/token/
2. Add it as GitHub secret: `PYPI_API_TOKEN`
3. Modify `.github/workflows/publish.yml` to use token authentication

Or build and upload manually:

```bash
# Build
python -m build

# Upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Upload to PyPI
python -m twine upload dist/*
```

## Troubleshooting

### Tests fail in GitHub Actions
- Ensure Dagu server starts correctly
- Check Dagu version compatibility
- Review logs in Actions tab

### PyPI upload fails
- Verify trusted publishing configuration
- Check package name is not taken
- Ensure version number is incremented

### Package installation issues
- Verify dependencies are correctly specified
- Check Python version requirements
- Test in fresh virtual environment
