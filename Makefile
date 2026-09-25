.PHONY: check render goldens test lint-fixtures clean

UV := uv run --with pytest --with pyyaml

check: ## render in memory and diff against tests/golden/ (what CI runs)
	python3 src/render.py --check

render: ## write all three renders to dist/ for eyeballing
	python3 src/render.py --out dist

goldens: ## adopt the current renders as the golden oracle — then read `git diff tests/golden/`
	python3 src/render.py --update-goldens

test: ## full suite (no model, no network, writes only to tmp)
	$(UV) pytest tests/ -q

lint-fixtures: ## run the linter over every fixture, printing exit codes
	@for v in tests/fixtures/*/; do \
		python3 -I skill/scripts/zettel_lint.py "$$v" --quiet >/dev/null 2>&1; \
		printf '%-40s exit=%s\n' "$$v" "$$?"; \
	done

clean:
	rm -rf dist .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
