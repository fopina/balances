link-check:
	ruff check
	ruff format --check

lint:
	ruff check --fix
	ruff format