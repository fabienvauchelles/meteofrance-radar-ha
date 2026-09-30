# Quality gates for meteofrance-radar-ha. Two areas, each with its own tools:
#
#   integration  .venv   Home Assistant 2026.8 + test harness, provisioned by uv (Python 3.14)
#   card         card/   npm: biome check, tsc --noEmit, vitest, rollup bundle
#
#   make build       provision both areas
#   make check       every gate of both areas, fail on any
#   make lint / typecheck / test   one step of the integration area
#   make card        every gate of the card, then rebuild the committed bundle

PY   := .venv/bin/python
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy

SRC := custom_components/meteofrance_radar tests

.PHONY: build build-integration build-card check lint typecheck test card clean

build: build-integration build-card

build-integration:
	uv sync --frozen

build-card:
	cd card && npm ci --no-audit --no-fund

lint:
	$(RUFF) check $(SRC)
	$(RUFF) format --check $(SRC)

typecheck:
	$(MYPY)

test:
	$(PY) -m pytest

card:
	cd card && npm run lint
	cd card && npm run typecheck
	cd card && npm test
	cd card && npm run build

check: lint typecheck test card

clean:
	rm -rf .venv .mypy_cache .ruff_cache .pytest_cache card/node_modules
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
