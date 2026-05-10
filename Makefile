lint:
	ruff check --fix
	ruff format

lint-check:
	ruff check
	ruff format --check
