# Chequeos locales: reemplazan al CI mientras GitHub Actions no esté disponible en la cuenta
DBT = dbt --no-use-colors
DBT_ARGS = --project-dir transform --profiles-dir transform
EXPERIMENT ?= piloto
N ?= 2000

.PHONY: install demo simulate transform transform-breaks orchestrate dashboard lint test check

install:
	pip install -e ".[dev]"

# Partida simulada como video, y su análisis tiro a tiro
SEED ?= 1
demo:
	pool-synthetic --seed $(SEED)
	pool-analyze data/videos/sintetica_$(SEED).mp4

simulate:
	pool-break --experiment $(EXPERIMENT) --n $(N)

# Modelos de tiros (requiere videos analizados en data/shots)
transform:
	$(DBT) build $(DBT_ARGS) --select tag:tiros

# Modelos del laboratorio de quiebres (requiere make simulate)
transform-breaks:
	$(DBT) build $(DBT_ARGS) --select tag:quiebres

orchestrate:
	dagster dev -m pool_match_lab.defs

dashboard:
	streamlit run dashboard/app.py

lint:
	ruff check .

test:
	pytest -v

check: lint test demo transform
