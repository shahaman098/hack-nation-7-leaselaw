.PHONY: help install install-all lint fmt typecheck test test-fast doctor demo release-check clean

help:
	@echo "HackForge dev targets:"
	@echo "  make install      Install core + dev deps (editable)"
	@echo "  make install-all  Install with collision + LLM extras"
	@echo "  make lint         Run ruff"
	@echo "  make fmt          Auto-fix lint + format"
	@echo "  make typecheck    Run mypy"
	@echo "  make test         Run full test suite"
	@echo "  make test-fast    Run tests excluding slow (model/network) tests"
	@echo "  make doctor       Verify environment"
	@echo "  make demo         Run the live pipeline on the sample brief"
	@echo "  make release-check Build and validate release artifacts"

install:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all,dev]"

lint:
	ruff check src/ tests/

fmt:
	ruff check --fix src/ tests/
	ruff format src/ tests/

typecheck:
	mypy

test:
	pytest

test-fast:
	HACKFORGE_USE_SENTENCE_TRANSFORMERS=0 HACKFORGE_REQUIRE_SEMANTIC_COLLISION=0 pytest -m "not slow"

doctor:
	hackforge doctor

demo:
	hackforge doctor --strict --live
	hackforge analyse --url https://openai.devpost.com/ --provider deepseek --search-profile fast

release-check: lint typecheck test-fast
	python -m build
	twine check dist/*

clean:
	rm -rf runs/* corpora/indexes/* corpora/cache/* .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
