.PHONY: check render goldens test lint-fixtures eval-lint eval-claude clean

UV := uv run --with pytest --with pyyaml

#: The eval target is the repo's `skill/` directory, so it needs a render in place first.
#: `skill/SKILL.md` is gitignored precisely because it is a build artifact.
SKILL_MD := skill/SKILL.md

# `claude plugin eval` needs a resolvable skill, and `skill/` has no SKILL.md until rendered.
$(SKILL_MD): src/SKILL.template.md src/fragments/frontmatter.claude.yaml src/fragments/environment.claude.md
	python3 src/render.py --platform claude --out dist
	cp dist/claude/SKILL.md $(SKILL_MD)

eval-lint: $(SKILL_MD) ## validate every eval case and run none — no model, no cost
	claude plugin eval skill --trust-plugin --case __lint__

eval-claude: $(SKILL_MD) ## Claude acceptance: the with/without ablation (calls a model, costs money)
	claude plugin eval skill --trust-plugin \
		--allow-tools Write Edit \
		--scaffold --ablation with-without \
		--json skill/evals/results/ablation.json

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
