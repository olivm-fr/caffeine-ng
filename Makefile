check:
	ruff format .
	ruff check --fix --exit-non-zero-on-fix .
	mypy .
