.PHONY: help install dev test lint format build publish publish-test clean bump-patch bump-minor bump-major

PYTHON ?= python3
VERSION := $(shell $(PYTHON) -c "import re; print(re.search(r'version\s*=\s*\"(.+?)\"', open('pyproject.toml').read()).group(1))")

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	$(PYTHON) -m pip install -e .

dev: ## Install with dev dependencies
	$(PYTHON) -m pip install -e ".[dev]"

test: ## Run tests
	$(PYTHON) -m pytest tests/ -v --tb=short

lint: ## Run ruff linter
	$(PYTHON) -m ruff check src/ tests/

format: ## Format code with ruff
	$(PYTHON) -m ruff format src/ tests/

build: clean ## Build distribution packages
	$(PYTHON) -m pip install --upgrade build
	$(PYTHON) -m build

publish-test: build ## Publish to TestPyPI
	$(PYTHON) -m pip install --upgrade twine
	$(PYTHON) -m twine upload --repository testpypi dist/*

publish: build ## Publish to PyPI (uses PYPI_TOKEN env var or ~/.pypirc)
	$(PYTHON) -m pip install --upgrade twine
	$(PYTHON) -m twine upload dist/* --username __token__ --password $(PYPI_TOKEN)

clean: ## Clean build artifacts
	rm -rf dist/ build/ src/*.egg-info *.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ── Versioning (semver) ─────────────────────────────────────────────────

bump-patch: ## Bump patch version (0.1.0 → 0.1.1)
	@$(PYTHON) scripts/bump_version.py patch
	@echo "Version bumped to $$($(PYTHON) -c "import re; print(re.search(r'version\s*=\s*\"(.+?)\"', open('pyproject.toml').read()).group(1))")"

bump-minor: ## Bump minor version (0.1.0 → 0.2.0)
	@$(PYTHON) scripts/bump_version.py minor
	@echo "Version bumped to $$($(PYTHON) -c "import re; print(re.search(r'version\s*=\s*\"(.+?)\"', open('pyproject.toml').read()).group(1))")"

bump-major: ## Bump major version (0.1.0 → 1.0.0)
	@$(PYTHON) scripts/bump_version.py major
	@echo "Version bumped to $$($(PYTHON) -c "import re; print(re.search(r'version\s*=\s*\"(.+?)\"', open('pyproject.toml').read()).group(1))")"

release-patch: bump-patch build publish ## Bump patch + build + publish
release-minor: bump-minor build publish ## Bump minor + build + publish
release-major: bump-major build publish ## Bump major + build + publish

tag: ## Create a git tag for the current version
	git tag -a "v$(VERSION)" -m "Release v$(VERSION)"
	git push origin "v$(VERSION)"
