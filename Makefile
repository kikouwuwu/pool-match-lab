# Chequeos locales: reemplazan al CI mientras GitHub Actions no esté disponible en la cuenta
DBT = dbt --no-use-colors
DBT_ARGS = --project-dir transform --profiles-dir transform
EXPERIMENT ?= piloto
N ?= 2000

.PHONY: install simulate transform orchestrate lint test check

install:
	pip install -e ".[dev]"

simulate:
	pool-break --experiment $(EXPERIMENT) --n $(N)

transform:
	$(DBT) build $(DBT_ARGS)

orchestrate:
	dagster dev -m pool_break_lab.defs

lint:
	ruff check .

test:
	pytest -v

check: lint test transform
