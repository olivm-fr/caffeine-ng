check:
	ruff format .
	ruff check --fix --exit-non-zero-on-fix .
	vermin --target=3.8- --violations  .
	mypy .
